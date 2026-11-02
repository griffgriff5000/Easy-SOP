"""Asynchronous FFmpeg export; replace the destination only after success."""
from pathlib import Path
import os,tempfile,sys
from PySide6.QtCore import QObject,QProcess,Signal
from .training_video import export_arguments


def ffmpeg_executable():
    from .media_runtime import installed_runtime,MissingMediaRuntime
    installed=installed_runtime()
    if installed:return str(installed)
    if getattr(sys,'frozen',False):raise MissingMediaRuntime('Download the optional video export tool first.')
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


class VideoExport(QObject):
    finished=Signal(object,object)
    progress=Signal(int)
    def __init__(self,parent=None):
        super().__init__(parent);self.process=QProcess(self);self.temporary=None;self.cancelled=False
        self.process.readyReadStandardError.connect(self._stderr)
        self.process.readyReadStandardOutput.connect(self._progress)
        self.process.finished.connect(self._done);self.process.errorOccurred.connect(self._error)

    @property
    def busy(self):return self.temporary is not None

    def start(self,session,output):
        if self.busy:raise ValueError('An export is already running.')
        output=Path(output).resolve();arguments=export_arguments(session,output)
        if not output.parent.is_dir():raise ValueError('Choose an existing output folder.')
        executable=ffmpeg_executable()
        fd,path=tempfile.mkstemp(prefix='.sop-video-',suffix='.mp4',dir=output.parent);os.close(fd)
        self.temporary=Path(path);self.output=output;self.cancelled=False;self.errors='';self.lines=''
        self.duration=(session.trim_end or session.duration)-session.trim_start
        self.process.setProgram(executable);self.process.setArguments(arguments[:-1]+[str(self.temporary)]);self.process.start()

    def cancel(self):
        if self.busy:self.cancelled=True;self.process.kill() # only this owned export process, writing a disposable file

    def _stderr(self):self.errors=(self.errors+bytes(self.process.readAllStandardError()).decode('utf-8','replace'))[-16000:]

    def _progress(self):
        self.lines+=bytes(self.process.readAllStandardOutput()).decode('utf-8','replace')
        while '\n' in self.lines:
            line,self.lines=self.lines.split('\n',1)
            if line.startswith('out_time_us='):
                try:self.progress.emit(min(99,max(0,round(float(line.split('=',1)[1])/1000000/self.duration*100))))
                except ValueError:pass

    def _error(self,error):
        if error==QProcess.ProcessError.FailedToStart:self._done(-1,None)

    def _done(self,code,status):
        if self.temporary is None:return
        self._stderr();temporary=self.temporary;self.temporary=None
        error=None
        try:
            if self.cancelled:raise RuntimeError('Export cancelled. The existing output and originals were retained.')
            if code!=0 or not temporary.is_file() or temporary.stat().st_size==0:raise RuntimeError(self.errors[-3000:] or self.process.errorString())
            temporary.replace(self.output);self.progress.emit(100)
        except Exception as exc:error=exc
        finally:temporary.unlink(missing_ok=True)
        self.finished.emit(self.output if error is None else None,error)
