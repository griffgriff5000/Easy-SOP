"""Qt screen/window and microphone capture; initialized only when requested."""
from pathlib import Path
import os,sys
from PySide6.QtCore import QObject,Signal,QUrl

_dll_handles=[]


def configure_media_runtime():
    if sys.platform=='win32' and not _dll_handles:
        import PySide6
        for path in {Path(PySide6.__file__).parent,Path(getattr(sys,'_MEIPASS',Path(PySide6.__file__).parent))}:
            if path.is_dir():_dll_handles.append(os.add_dll_directory(str(path)))
    os.environ.setdefault('QT_MEDIA_BACKEND','ffmpeg')


class VideoRecorder(QObject):
    changed=Signal(str)
    duration=Signal(int)
    error=Signal(str)
    completed=Signal(str,object,int,object)

    def __init__(self,parent=None):
        super().__init__(parent);configure_media_runtime()
        from PySide6.QtMultimedia import QMediaCaptureSession,QMediaRecorder
        self.session=QMediaCaptureSession(self);self.recorder=QMediaRecorder(self)
        self.session.setRecorder(self.recorder);self.state='idle';self.mode=None
        self.source=None;self.audio=None;self.last_duration=0;self.failure=None
        self.recorder.recorderStateChanged.connect(self._state_changed)
        self.recorder.durationChanged.connect(self._duration)
        self.recorder.errorOccurred.connect(self._error)

    @property
    def busy(self):return self.state!='idle'

    def _begin(self,output,device,mode,video):
        from PySide6.QtMultimedia import QMediaFormat,QAudioInput,QMediaRecorder
        if self.busy:raise ValueError('Stop the current recording first.')
        output=Path(output).resolve()
        if output.exists():raise ValueError('Choose a new recording file; originals are never replaced.')
        format=QMediaFormat();format.setFileFormat(QMediaFormat.FileFormat.Matroska if video else QMediaFormat.FileFormat.Wave)
        if format.fileFormat() not in format.supportedFileFormats(QMediaFormat.ConversionMode.Encode):
            raise RuntimeError('The Qt FFmpeg recording backend is unavailable. Reinstall the complete application.')
        if video:format.setVideoCodec(QMediaFormat.VideoCodec.H264)
        if device is not None:format.setAudioCodec(QMediaFormat.AudioCodec.AAC if video else QMediaFormat.AudioCodec.Wave)
        elif not video:raise ValueError('Select an available microphone.')
        self.output=output;self.mode=mode;self.failure=None;self.last_duration=0
        self.recorder.setMediaFormat(format);self.recorder.setQuality(QMediaRecorder.Quality.HighQuality)
        if video:self.recorder.setVideoFrameRate(30)
        self.recorder.setOutputLocation(QUrl.fromLocalFile(str(output)))
        if device is not None:
            self.audio=QAudioInput(device,self);self.session.setAudioInput(self.audio)
        self.state='starting';self.changed.emit(self.state)

    def start_video(self,source,device,output):
        from PySide6.QtMultimedia import QScreenCapture,QWindowCapture
        kind,target=source
        if kind not in {'screen','window'} or target is None or (kind=='window' and not target.isValid()):raise ValueError('Choose an available screen or window.')
        self._begin(output,device,'video',True)
        try:
            if kind=='screen':self.source=QScreenCapture(self);self.source.setScreen(target);self.session.setScreenCapture(self.source)
            else:self.source=QWindowCapture(self);self.source.setWindow(target);self.session.setWindowCapture(self.source)
            if hasattr(self.source,'setMaximumFrameRate'):self.source.setMaximumFrameRate(30)
            self.source.errorOccurred.connect(self._error);self.source.setActive(True)
            if self.state=='starting':self.recorder.record()
        except Exception as exc:self._error(str(exc))

    def start_audio(self,device,output,mode='narration'):
        self._begin(output,device,mode,False);self.recorder.record()

    def pause(self):
        if self.state=='recording':self.recorder.pause()
        elif self.state=='paused':self.recorder.record()

    def stop(self):
        if not self.busy:return
        from PySide6.QtMultimedia import QMediaRecorder
        self.state='stopping';self.changed.emit(self.state);self.recorder.stop()
        if self.mode and self.recorder.recorderState()==QMediaRecorder.RecorderState.StoppedState:self._finish()

    def _state_changed(self,state):
        from PySide6.QtMultimedia import QMediaRecorder
        if not self.mode:return
        if state==QMediaRecorder.RecorderState.StoppedState:self._finish()
        else:
            self.state='paused' if state==QMediaRecorder.RecorderState.PausedState else 'recording'
            self.changed.emit(self.state)

    def _duration(self,value):
        self.last_duration=max(self.last_duration,value);self.duration.emit(value)

    def _error(self,*args):
        if not self.mode:return
        self.failure=str(args[-1]);self.error.emit(self.failure);self.stop()

    def _finish(self):
        mode,path,duration,error=self.mode,self.output,self.last_duration,self.failure
        self.mode=None
        if self.source:
            self.source.setActive(False);self.session.setScreenCapture(None);self.session.setWindowCapture(None)
            self.source.deleteLater();self.source=None
        self.session.setAudioInput(None)
        if self.audio:self.audio.deleteLater();self.audio=None
        self.state='idle';self.changed.emit(self.state)
        if not path.is_file() or path.stat().st_size==0:error=error or 'No recording was created. Check the selected source and microphone.'
        self.completed.emit(mode,path,duration,error)
