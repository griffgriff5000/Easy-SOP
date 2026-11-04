"""Focused dialog for generating, previewing and applying local text-to-speech narration."""
from pathlib import Path
import tempfile,threading
from PySide6.QtCore import Qt,QUrl,Signal
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QPlainTextEdit,QComboBox,
    QDoubleSpinBox,QPushButton,QProgressBar,QMessageBox)
from .. import speech_runtime as speech


class SpeechDialog(QDialog):
    worker_done=Signal(int,object,object)
    progress_changed=Signal(int)

    def __init__(self,section_seconds,settings=None,apply=None,parent=None,target=None):
        super().__init__(parent);self.setWindowTitle('Text to speech');self.resize(560,560)
        self.section_seconds=section_seconds;self.apply=apply;self.target=target
        self.token=0;self.working=False;self.cancel_event=threading.Event();self.needs_download=False
        self.audio=None;self.audio_key=None;self.audio_seconds=0;self.playing=False
        self.directory=tempfile.TemporaryDirectory(prefix='sop-speech-')
        settings=settings or {}
        box=QVBoxLayout(self)
        intro=QLabel('Type the narration, choose a voice and listen to a preview. Nothing changes in the video until you choose Use voiceover. '
                     'Speech is generated on this computer; scripts and audio are never uploaded.')
        intro.setWordWrap(True);box.addWidget(intro)
        self.script=QPlainTextEdit();self.script.setPlaceholderText('Narration script for this section');self.script.setMinimumHeight(170)
        self.script.setPlainText(settings.get('script',''));box.addWidget(QLabel('Narration script'));box.addWidget(self.script,1)
        self.count=QLabel();box.addWidget(self.count)
        form=QFormLayout();self.voice=QComboBox()
        for identifier,name,sex in speech.VOICES:self.voice.addItem(f'{name} - British English, {sex.lower()}',identifier)
        self.voice.setCurrentIndex(max(0,self.voice.findData(settings.get('voice',speech.DEFAULT_VOICE))));form.addRow('Voice',self.voice)
        self.speed=QDoubleSpinBox();self.speed.setRange(.6,1.5);self.speed.setSingleStep(.05);self.speed.setDecimals(2);self.speed.setPrefix('x ')
        self.speed.setValue(min(1.5,max(.6,settings.get('speed',1.0))));form.addRow('Speaking speed',self.speed);box.addLayout(form)
        note=QLabel('Voices vary in naturalness. Generate a preview and try another if one does not sound right.');note.setWordWrap(True);box.addWidget(note)
        row=QHBoxLayout();self.generate_button=QPushButton('Generate preview');self.generate_button.clicked.connect(self.generate)
        self.play_button=QPushButton('Play preview');self.play_button.clicked.connect(self.toggle_playback)
        row.addWidget(self.generate_button);row.addWidget(self.play_button);box.addLayout(row)
        self.durations=QLabel();box.addWidget(self.durations)
        self.progress=QProgressBar();self.progress.setRange(0,100);self.progress.setValue(0);box.addWidget(self.progress)
        self.status=QLabel('');self.status.setWordWrap(True);box.addWidget(self.status)
        footer=QHBoxLayout();footer.addStretch()
        self.use_button=QPushButton('Use voiceover');self.use_button.setObjectName('primary');self.use_button.clicked.connect(self.use_voiceover)
        self.cancel_button=QPushButton('Cancel');self.cancel_button.clicked.connect(self.cancel)
        footer.addWidget(self.use_button);footer.addWidget(self.cancel_button);box.addLayout(footer)
        from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
        self.player=QMediaPlayer(self);self.output=QAudioOutput(self);self.player.setAudioOutput(self.output)
        self.player.playbackStateChanged.connect(self._playback_state)
        self.script.textChanged.connect(self._changed);self.voice.currentIndexChanged.connect(self._changed);self.speed.valueChanged.connect(self._changed)
        self.worker_done.connect(self._finished);self.progress_changed.connect(self._progress)
        if not speech.installed_runtime(target):self.status.setText(f'First use: about {speech.DOWNLOAD_MEGABYTES} MB of speech files will be downloaded once, after you agree. Afterwards speech works offline.')
        self._changed()

    def key(self):
        return (self.script.toPlainText().strip(),self.voice.currentData(),round(self.speed.value(),2))

    @property
    def matches(self):
        return self.audio is not None and self.audio_key==self.key()

    def settings(self):
        script,voice,speed=self.key();return dict(script=script,voice=voice,speed=speed)

    def _changed(self,*args):
        if self.playing:self.stop_playback()
        text=self.script.toPlainText()
        if len(text)>speech.MAX_SCRIPT:self.script.blockSignals(True);self.script.setPlainText(text[:speech.MAX_SCRIPT]);self.script.blockSignals(False)
        self.count.setText(f'{len(self.script.toPlainText()):,} / {speech.MAX_SCRIPT:,} characters')
        if self.audio is not None and not self.matches and not self.working:self.status.setText('Settings changed. Generate a new preview before using the voiceover.')
        self._refresh()

    def _refresh(self):
        busy=self.working;ready=self.matches
        for widget in (self.script,self.voice,self.speed,self.generate_button):widget.setEnabled(not busy)
        self.play_button.setEnabled(ready and not busy);self.use_button.setEnabled(ready and not busy)
        self.play_button.setText('Stop preview' if self.playing else 'Play preview')
        generated=f'{self.audio_seconds:.1f} s' if ready else 'not generated'
        self.durations.setText(f'Generated narration: {generated}    Section length: {self.section_seconds:.1f} s')
        self.cancel_button.setText('Cancel operation' if busy else 'Cancel')

    def confirm_download(self):
        return QMessageBox.question(self,'Download speech files?',
            f'Text to speech needs about {speech.DOWNLOAD_MEGABYTES} MB of speech files (sherpa-onnx engine and Kokoro voice model) downloaded once from their original GitHub release.\n\n'
            'After that, speech is generated offline on this computer. Download now?',
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes

    def generate(self):
        if self.working:return
        try:text=speech.validate_script(self.script.toPlainText(),self.voice.currentData(),self.speed.value())
        except ValueError as exc:self.status.setText(str(exc));return
        download=self.needs_download or not speech.installed_runtime(self.target)
        if download and not self.confirm_download():self.status.setText('Speech files were not downloaded.');return
        self.stop_playback();self.token+=1;token=self.token;self.cancel_event.clear();self.working=True
        key=self.key();voice,speed=key[1],key[2];output=Path(self.directory.name)/f'preview-{token}.wav'
        self.progress.setRange(0,100);self.progress.setValue(0)
        self.status.setText('Downloading speech files...' if download else 'Generating speech...')
        if not download:self.progress.setRange(0,0)
        self._refresh()
        def run():
            try:
                if download:
                    speech.install_runtime(target=self.target,cancel=self.cancel_event,progress=self.progress_changed.emit)
                    self.progress_changed.emit(-1)
                seconds=speech.synthesize(text,voice,speed,output,cancel=self.cancel_event,target=self.target)
                result,error=(output,key,seconds),None
            except Exception as exc:result,error=None,exc
            self.worker_done.emit(token,result,error)
        threading.Thread(target=run,daemon=True).start()

    def _progress(self,value):
        if value<0:self.progress.setRange(0,0);self.status.setText('Generating speech...')
        else:self.progress.setRange(0,100);self.progress.setValue(value)

    def _finished(self,token,result,error):
        if token!=self.token:return
        self.working=False;self.progress.setRange(0,100);self.progress.setValue(0)
        if error is not None:
            cancelled=self.cancel_event.is_set()
            if isinstance(error,speech.MissingSpeechRuntime):self.needs_download=True
            self.status.setText('Cancelled. Existing narration was not changed.' if cancelled else str(error) or 'Speech generation failed.')
        else:
            self.audio,self.audio_key,self.audio_seconds=result;self.needs_download=False;self.progress.setValue(100)
            self.status.setText('Preview ready. Play it, then choose Use voiceover.' if self.matches else 'Settings changed. Generate a new preview before using the voiceover.')
        self._refresh()

    def toggle_playback(self):
        if self.playing:self.stop_playback();return
        if not self.matches:return
        self.player.setSource(QUrl.fromLocalFile(str(self.audio)));self.playing=True;self.player.play();self._refresh()

    def stop_playback(self):
        self.playing=False;self.player.stop();self.player.setSource(QUrl());self._refresh()

    def _playback_state(self,state):
        from PySide6.QtMultimedia import QMediaPlayer
        if self.playing and state==QMediaPlayer.PlaybackState.StoppedState:self.playing=False;self._refresh()

    def use_voiceover(self):
        if self.working or not self.matches:return
        if self.audio_seconds>self.section_seconds+.05:
            answer=QMessageBox.warning(self,'Narration is longer than the section',
                f'The narration is {self.audio_seconds:.1f} s but the section is {self.section_seconds:.1f} s. '
                'Export may cut off the end of the narration. The video length and speech speed will not be changed.\n\nUse this voiceover anyway?',
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
            if answer!=QMessageBox.StandardButton.Yes:return
        self.stop_playback()
        try:
            if self.apply is not None:self.apply(self.audio,self.settings())
        except Exception as exc:self.status.setText('Voiceover not applied: '+str(exc));return
        self.accept()

    def cancel(self):
        if self.working:self.cancel_event.set();self.status.setText('Cancelling...');return
        self.reject()

    def done(self,result):
        if self.working:self.cancel_event.set();self.status.setText('Cancelling... close the window once it has stopped.');return
        self.stop_playback();self.audio=None
        super().done(result);self.directory.cleanup()
