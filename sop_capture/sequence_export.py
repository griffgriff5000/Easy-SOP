"""Sequential local video rendering with atomic final output and owned cancellation."""
from pathlib import Path
from copy import deepcopy
import tempfile,re
from PySide6.QtCore import QObject,QProcess,Signal,QTimer
from .video_timeline import validate_timeline,section_duration,render_card,overlay_artwork


def section_arguments(session,section,directory,output,has_audio=False):
    directory=Path(directory);duration=section_duration(section)
    args=['-hide_banner','-nostdin','-y','-progress','pipe:1','-nostats','-filter_complex_threads','1']
    if section['kind']=='card':
        image=directory/'card.png';render_card(session,section).save(image)
        args+=['-loop','1','-i',str(image)]
    else:args+=['-protocol_whitelist','file,pipe','-ss',f"{section['start']:g}",'-i',str(session.asset(section['source']))]
    args+=['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
    audio='0:a' if has_audio and section['kind']=='video' else '1:a';next_input=2;delay=0
    if section['kind']=='video' and section['use_narration']:
        offset=section['start']-section['narration_origin'];delay=max(0,-offset)
        args+=['-protocol_whitelist','file,pipe','-ss',f'{max(0,offset):g}','-i',str(session.asset(section['narration']))]
        audio='2:a';next_input=3
    filters=['[0:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,setpts=PTS-STARTPTS[v0]']
    for index,item in enumerate(section['overlays']):
        image=directory/f'overlay-{index}.png';overlay_artwork(item).save(image)
        args+=['-loop','1','-i',str(image)]
        filters.append(f"[v{index}][{next_input}:v]overlay=0:0:enable='gte(t,{item['start']:g})*lt(t,{item['end']:g})'[v{index+1}]")
        next_input+=1
    volume=section.get('volume',1)
    filters.append(f'[{audio}]asetpts=PTS-STARTPTS,adelay={round(delay*1000)}:all=1,volume={volume:g},apad,atrim=duration={duration:g},aresample=48000,aformat=channel_layouts=stereo[a]')
    args+=['-filter_complex',';'.join(filters),'-map',f"[v{len(section['overlays'])}]",'-map','[a]',
        '-t',f'{duration:g}','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',str(output)]
    return args


class SequenceExport(QObject):
    finished=Signal(object,object)
    progress=Signal(int)
    def __init__(self,parent=None):
        super().__init__(parent);self.process=QProcess(self);self.directory=None;self.cancelled=False
        self.process.readyReadStandardError.connect(self._stderr);self.process.readyReadStandardOutput.connect(self._progress)
        self.process.finished.connect(self._done);self.process.errorOccurred.connect(self._error)

    @property
    def busy(self):return self.directory is not None

    def start(self,session,output):
        from .media_export import ffmpeg_executable
        if self.busy:raise ValueError('A sequence export is already running.')
        session.validate();validate_timeline(session,session.timeline)
        if not session.timeline:raise ValueError('Add at least one section to export.')
        self.output=Path(output).resolve()
        protected={session.asset(n) for item in session.timeline for n in (item.get('source'),item.get('narration'),item.get('logo')) if n}
        protected.update(session.asset(n) for n in (session.original,session.narration) if n)
        if self.output.suffix.lower()!='.mp4' or self.output in protected:raise ValueError('Choose a separate MP4 output; originals are preserved.')
        if not self.output.parent.is_dir():raise ValueError('Choose an existing output folder.')
        for item in session.timeline:
            for name in (item.get('source'),item.get('narration') if item.get('use_narration') else None,item.get('logo')):
                if name and not session.asset(name).is_file():raise ValueError('Missing section file: '+name)
        self.executable=ffmpeg_executable();self.session=deepcopy(session);self.index=0;self.elapsed=0
        self.total=sum(section_duration(s) for s in session.timeline);self.cancelled=False
        self.directory=tempfile.TemporaryDirectory(prefix='.sop-sequence-',dir=self.output.parent);self.root=Path(self.directory.name)
        self.process.setWorkingDirectory(str(self.root));QTimer.singleShot(0,self._next)

    def _run(self,arguments,phase):
        self.phase=phase;self.errors='';self.lines='';self.process.setProgram(self.executable);self.process.setArguments(arguments);self.process.start()

    def _next(self):
        if not self.busy:return
        try:
            if self.index==len(self.session.timeline):
                (self.root/'sequence.txt').write_text(''.join(f"file section-{i}.mp4\n" for i in range(self.index)),encoding='utf-8')
                self._run(['-hide_banner','-nostdin','-y','-protocol_whitelist','file,pipe','-f','concat','-safe','1','-i','sequence.txt','-c','copy','-movflags','+faststart',str(self.root/'finished.mp4')],'join');return
            item=self.session.timeline[self.index]
            if item['kind']=='card':self._render(False)
            else:self._run(['-hide_banner','-nostdin','-protocol_whitelist','file,pipe','-i',str(self.session.asset(item['source'])),'-t','0','-f','null','-'],'probe')
        except Exception as exc:self._finish(exc)

    def _render(self,has_audio):
        self._run(section_arguments(self.session,self.session.timeline[self.index],self.root,self.root/f'section-{self.index}.mp4',has_audio),'render')

    def _stderr(self):self.errors=(self.errors+bytes(self.process.readAllStandardError()).decode('utf-8','replace'))[-32000:]

    def _progress(self):
        self.lines+=bytes(self.process.readAllStandardOutput()).decode('utf-8','replace')
        while '\n' in self.lines:
            line,self.lines=self.lines.split('\n',1)
            if self.phase=='render' and line.startswith('out_time_us='):
                try:self.progress.emit(min(98,round((self.elapsed+float(line.split('=',1)[1])/1e6)/self.total*98)))
                except ValueError:pass

    def _error(self,error):
        if error==QProcess.ProcessError.FailedToStart:self._finish(RuntimeError(self.process.errorString()))

    def _done(self,code,status):
        if not self.busy:return
        self._stderr()
        if self.cancelled:self._finish(RuntimeError('Export cancelled. Originals and existing output retained.'));return
        if code!=0:self._finish(RuntimeError(self.errors[-3000:] or 'Video export failed.'));return
        try:
            if self.phase=='probe':self._render(bool(re.search(r'Audio:',self.errors)));return
            if self.phase=='render':
                self.elapsed+=section_duration(self.session.timeline[self.index]);self.index+=1;self._next();return
            (self.root/'finished.mp4').replace(self.output);self.progress.emit(100);self._finish(None)
        except Exception as exc:self._finish(exc)

    def cancel(self):
        if self.busy:
            self.cancelled=True
            if self.process.state()==QProcess.ProcessState.NotRunning:self._finish(RuntimeError('Export cancelled. Originals and existing output retained.'))
            else:self.process.kill()

    def _finish(self,error):
        if not self.directory:return
        directory=self.directory;self.directory=None;directory.cleanup()
        self.finished.emit(self.output if error is None else None,error)
