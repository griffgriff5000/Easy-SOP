"""Training video recording and basic voiceover editing, independent of SOP projects."""
from pathlib import Path
from PySide6.QtCore import Qt,QUrl,QTimer,QStandardPaths
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,
    QCheckBox,QDoubleSpinBox,QSlider,QProgressBar,QSplitter,QFormLayout,QFileDialog,QInputDialog,QDialog,QMessageBox)
from .components import page_header,scroll_panel
from ..training_video import VideoSession
from ..media_export import VideoExport


class TrainingVideoPage(QWidget):
    def __init__(self,can_record,parent=None):
        super().__init__(parent);self.can_record=can_record;self.video=None;self.engine=None;self.player=None;self.loading=False
        self._media_ready=False;self._narration_failure=None
        self.exporter=VideoExport(self);self.exporter.finished.connect(self._exported);self.exporter.progress.connect(self._progress)
        box=QVBoxLayout(self);page_header(box,'Training video','Record a screen or window, add your narration and export an MP4. Everything stays on this PC.')
        tools=QHBoxLayout()
        self.new_button=self._button('New video',self.new_session,tools)
        self.open_button=self._button('Open video session',self.open_session,tools)
        self.folder_button=self._button('Open folder',self.open_folder,tools);tools.addStretch();box.addLayout(tools)
        split=QSplitter();self.controls=QWidget();self.controls.setObjectName('scrollPage');controls=QVBoxLayout(self.controls)
        self.identity=QLabel('Create or open a video session. Each video has its own folder.');self.identity.setWordWrap(True);controls.addWidget(self.identity)
        form=QFormLayout();self.source=QComboBox();self.source.setAccessibleName('Video source');form.addRow('Screen / window',self.source)
        self.mic=QComboBox();self.mic.addItem('No microphone',None);self.mic.setAccessibleName('Recording microphone');form.addRow('Microphone',self.mic)
        for picker in (self.source,self.mic):picker.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);picker.setMinimumContentsLength(14)
        self.refresh_button=QPushButton('Refresh screens and microphones');self.refresh_button.clicked.connect(self.refresh_sources);form.addRow(self.refresh_button)
        self.test_button=QPushButton('Test microphone (record 3 seconds)');self.test_button.clicked.connect(self.test_microphone);form.addRow(self.test_button)
        self.minimize=QCheckBox('Minimize app while recording video');self.minimize.setChecked(True);form.addRow(self.minimize);controls.addLayout(form)
        row=QHBoxLayout();self.record_button=self._button('Record video',self.record_video,row)
        self.pause_button=self._button('Pause',self.pause_recording,row);self.stop_button=self._button('Stop',self.stop_recording,row);controls.addLayout(row)
        self.narrate_button=QPushButton('Record voiceover while watching');self.narrate_button.clicked.connect(self.record_narration);controls.addWidget(self.narrate_button)
        note=QLabel('Voiceover starts at the beginning of the recording. Original footage and earlier takes are retained. Trimming is applied on export.');note.setWordWrap(True);note.setObjectName('caption');controls.addWidget(note)
        edits=QFormLayout();self.start=QDoubleSpinBox();self.end=QDoubleSpinBox()
        for field in (self.start,self.end):field.setRange(0,360000);field.setDecimals(3);field.setSuffix(' s');field.valueChanged.connect(self._edited)
        self.end.setSpecialValueText('End of recording');edits.addRow('Trim start',self.start);edits.addRow('Trim end',self.end)
        self.volume=QDoubleSpinBox();self.volume.setRange(0,100);self.volume.setValue(100);self.volume.setSuffix(' %');self.volume.valueChanged.connect(self._edited);edits.addRow('Audio volume',self.volume)
        self.use_voice=QCheckBox('Use recorded voiceover instead of original audio');self.use_voice.toggled.connect(self._edited);edits.addRow(self.use_voice);controls.addLayout(edits)
        self.export_button=QPushButton('Export MP4...');self.export_button.setObjectName('primary');self.export_button.clicked.connect(self.export);controls.addWidget(self.export_button)
        self.cancel_button=QPushButton('Cancel export');self.cancel_button.clicked.connect(self.exporter.cancel);controls.addWidget(self.cancel_button)
        self.progress=QProgressBar();controls.addWidget(self.progress);controls.addStretch()
        self.controls_scroll=scroll_panel(self.controls);split.addWidget(self.controls_scroll)
        preview=QWidget();preview_box=QVBoxLayout(preview);self.preview_box=preview_box
        self.placeholder=QLabel('Your recording will appear here. Select a source and press Record video.');self.placeholder.setWordWrap(True);self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter);preview_box.addWidget(self.placeholder,1)
        playback=QHBoxLayout();self.play_button=self._button('Play / pause',self.play_pause,playback)
        self.position=QSlider(Qt.Orientation.Horizontal);self.position.sliderReleased.connect(self._seek);playback.addWidget(self.position,1)
        self.time=QLabel('00:00 / 00:00');playback.addWidget(self.time);preview_box.addLayout(playback)
        split.addWidget(preview);split.setStretchFactor(1,1);split.setSizes([320,800]);box.addWidget(split,1)
        self.status=QLabel('Ready. Choose a session to keep your recording and voiceover together.');self.status.setWordWrap(True);box.addWidget(self.status)
        self.floating=QDialog(None,Qt.WindowType.Tool|Qt.WindowType.WindowStaysOnTopHint);self.floating.setWindowTitle('Training video recording')
        floating_box=QHBoxLayout(self.floating);self.floating_time=QLabel('Recording');floating_box.addWidget(self.floating_time)
        self._button('Pause / resume',self.pause_recording,floating_box);self._button('Stop recording',self.stop_recording,floating_box)
        self.floating.rejected.connect(self.stop_recording)
        self.mic_timer=QTimer(self);self.mic_timer.setSingleShot(True);self.mic_timer.timeout.connect(self.stop_recording)
        self._refresh()

    @staticmethod
    def _button(text,callback,layout):
        button=QPushButton(text);button.clicked.connect(callback);layout.addWidget(button);return button

    @property
    def busy(self):return bool((self.engine and self.engine.busy) or self.exporter.busy)

    def activate(self):
        try:
            self._ensure_media()
            if self.video and self.video.original and self.player.source().isEmpty():self._load_media()
            if not self.busy:self.refresh_sources()
        except Exception as exc:self.status.setText('Video tools unavailable: '+str(exc))

    def _ensure_media(self):
        if self.engine:return
        from ..video_recorder import VideoRecorder
        self.engine=VideoRecorder(self)
        from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
        from PySide6.QtMultimediaWidgets import QVideoWidget
        self.player=QMediaPlayer(self);self.audio=QAudioOutput(self);self.player.setAudioOutput(self.audio)
        self.view=QVideoWidget();self.view.hide();self.preview_box.insertWidget(0,self.view,1);self.player.setVideoOutput(self.view)
        self.view.videoSink().videoFrameChanged.connect(self._preview_frame)
        self.voice_player=QMediaPlayer(self);self.voice_audio=QAudioOutput(self);self.voice_player.setAudioOutput(self.voice_audio)
        self.test_player=QMediaPlayer(self);self.test_audio=QAudioOutput(self);self.test_player.setAudioOutput(self.test_audio)
        self.engine.changed.connect(self._record_state);self.engine.duration.connect(self._record_duration);self.engine.completed.connect(self._recorded)
        self.engine.error.connect(lambda text:self.status.setText('Recording error: '+text))
        self.player.durationChanged.connect(self._duration);self.player.positionChanged.connect(self._position)
        self.player.playbackStateChanged.connect(self._play_state);self.player.mediaStatusChanged.connect(self._media_status)
        self.player.hasVideoChanged.connect(lambda _:self._update_media_ready())
        self.player.errorOccurred.connect(lambda code,text:self._playback_error(text,True))
        for player in (self.voice_player,self.test_player):player.errorOccurred.connect(lambda code,text:self._playback_error(text,False))
        if self.video:self._load_media()

    def refresh_sources(self):
        if self.busy:return
        try:
            self._ensure_media()
            from PySide6.QtGui import QGuiApplication
            from PySide6.QtMultimedia import QWindowCapture,QMediaDevices
            old_mic=self.mic.currentData();self.source.clear();self.mic.clear();self.mic.addItem('No microphone',None)
            for index,screen in enumerate(QGuiApplication.screens(),1):self.source.addItem(f'Screen {index}: {screen.name()}',('screen',screen))
            for window in QWindowCapture.capturableWindows():self.source.addItem('Window: '+window.description(),('window',window))
            for device in QMediaDevices.audioInputs():self.mic.addItem(device.description(),bytes(device.id()))
            index=self.mic.findData(old_mic)
            if index>=0:self.mic.setCurrentIndex(index)
        except Exception as exc:self.status.setText('Could not list recording devices: '+str(exc))

    def _device(self,required=False):
        from PySide6.QtMultimedia import QMediaDevices
        identity=self.mic.currentData()
        for device in QMediaDevices.audioInputs():
            if bytes(device.id())==identity:return device
        if required or identity is not None:raise ValueError('Select an available microphone first.')
        return None

    def new_session(self):
        if self.busy:return False
        title,accepted=QInputDialog.getText(self,'New training video','Video name:')
        if not accepted:return False
        parent=QFileDialog.getExistingDirectory(self,'Choose a parent folder for the new video',QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation))
        if not parent:return False
        try:self.set_session(VideoSession.create(parent,title));return True
        except Exception as exc:self.status.setText(str(exc));return False

    def open_session(self):
        if self.busy:return
        path,_=QFileDialog.getOpenFileName(self,'Open training video session','','Training video (video.json)')
        if path:
            try:self.set_session(VideoSession.load(path))
            except Exception as exc:self.status.setText('Could not open video: '+str(exc))

    def set_session(self,session):
        if self.busy:raise ValueError('Stop recording or finish the export first.')
        if self.player:
            for player in (self.player,self.voice_player,self.test_player):player.stop();player.setSource(QUrl())
        self.video=session;self.loading=True
        self.start.setValue(session.trim_start);self.end.setValue(session.trim_end);self.volume.setValue(session.volume*100);self.use_voice.setChecked(session.use_narration)
        self.loading=False;self.identity.setText(session.title+'\n'+str(session.root))
        self.status.setText('Session opened. Originals are retained in this folder.')
        if self.player:self._load_media()
        self._refresh()

    def _load_media(self):
        self._media_ready=False
        self.placeholder.setText('Press Play to preview your recording.' if self.video.original else 'Choose a source and press Record video.');self.placeholder.show();self.view.hide()
        if self.video.original:self.player.setSource(QUrl.fromLocalFile(str(self.video.asset(self.video.original))))
        else:self.player.setSource(QUrl())
        if self.video.narration:self.voice_player.setSource(QUrl.fromLocalFile(str(self.video.asset(self.video.narration))))
        else:self.voice_player.setSource(QUrl())
        self._audio_mode()

    def _prepare_recording(self):
        if self.busy:return False
        if not self.can_record():raise ValueError('Finish SOP recording, document processing or export first.')
        self._ensure_media()
        if self.video is None and not self.new_session():return False
        self.player.pause();self.voice_player.stop();self.test_player.stop();return True

    def record_video(self):
        try:
            if not self._prepare_recording():return
            if self.source.currentData() is None:self.refresh_sources()
            if self.source.currentData() is None:raise ValueError('Select a screen or window.')
            self.engine.start_video(self.source.currentData(),self._device(),self.video.new_asset('recording','.mkv'))
        except Exception as exc:self.status.setText('Could not start recording: '+str(exc));self._refresh()

    def record_narration(self):
        try:
            if not self._prepare_recording():return
            if not self.video.original:raise ValueError('Record the screen video first.')
            self._update_media_ready()
            if not self._media_ready:raise ValueError('Wait for the video to load, or open a playable recording before narrating.')
            self.player.setPosition(0);self._narration_failure=None
            self.engine.start_audio(self._device(True),self.video.new_asset('voiceover','.wav'),'narration')
        except Exception as exc:self.status.setText('Could not start voiceover: '+str(exc));self._refresh()

    def test_microphone(self):
        try:
            if not self._prepare_recording():return
            self.engine.start_audio(self._device(True),self.video.new_asset('microphone-test','.wav'),'microphone-test')
            if self.engine.busy:self.mic_timer.start(3000)
        except Exception as exc:self.status.setText('Could not test microphone: '+str(exc));self._refresh()

    def pause_recording(self):
        if self.engine and self.engine.busy:self.engine.pause()

    def stop_recording(self):
        self.mic_timer.stop()
        if self.engine:self.engine.stop()

    def _record_state(self,state):
        if state in {'starting','recording','paused','stopping'}:self.status.setText('Training video: '+state)
        if self.engine.mode=='narration':
            self.audio.setMuted(True)
            if state=='recording':self.player.play()
            else:self.player.pause()
        if self.engine.mode=='video' and state=='recording':
            self.floating.show()
            if self.minimize.isChecked():self.window().showMinimized()
        if state=='idle':self.floating.hide();self.mic_timer.stop()
        self.pause_button.setText('Resume' if state=='paused' else 'Pause');self._refresh()

    def _record_duration(self,milliseconds):
        self.floating_time.setText(f'Recording {milliseconds/1000:.1f} s')

    def _recorded(self,mode,path,duration,error):
        self.window().showNormal()
        if mode=='narration':self.player.pause()
        if mode=='narration' and self._narration_failure:error=error or self._narration_failure
        if error:
            self.status.setText('Recording stopped: '+str(error)+' Unfinished files are retained in the session folder.')
        elif mode=='video':
            self.video.original=path.name;self.video.narration=None;self.video.use_narration=False
            self.video.duration=duration/1000;self.video.trim_start=self.video.trim_end=0;self.video.save();self.set_session(self.video)
            self.status.setText('Video recorded. Preview it, trim it or record a voiceover.')
        elif mode=='narration':
            self.video.narration=path.name;self.video.use_narration=True;self.video.save();self.set_session(self.video)
            self.status.setText('Voiceover saved. Play to preview it with the video, or export MP4.')
        else:
            self.test_player.setSource(QUrl.fromLocalFile(str(path)));self.test_player.play()
            self.status.setText('Playing your microphone test. The test file is retained in the session folder.')
        self._audio_mode();self._refresh()

    def _duration(self,milliseconds):
        self.position.setRange(0,milliseconds)
        if self.video and self.video.original and milliseconds>0:
            self.video.duration=milliseconds/1000;self.video.save()
        self._position(self.player.position());self._update_media_ready()

    def _preview_frame(self,frame):
        if frame.isValid():self.placeholder.hide();self.view.show()

    def _position(self,milliseconds):
        if not self.position.isSliderDown():self.position.setValue(milliseconds)
        self.time.setText(f'{milliseconds/1000:.1f} / {self.position.maximum()/1000:.1f} s')
        if not self.video or (self.engine and self.engine.busy):return
        if self.video.use_narration and abs(self.voice_player.position()-milliseconds)>200:self.voice_player.setPosition(milliseconds)
        if self.video.trim_end and milliseconds>=self.video.trim_end*1000:self.player.pause()

    def _play_state(self,state):
        if self.engine and self.engine.busy:return
        from PySide6.QtMultimedia import QMediaPlayer
        if self.video and self.video.use_narration:
            if state==QMediaPlayer.PlaybackState.PlayingState:self.voice_player.setPosition(self.player.position());self.voice_player.play()
            else:self.voice_player.pause()

    def _media_status(self,status):
        from PySide6.QtMultimedia import QMediaPlayer
        self._update_media_ready()
        if status==QMediaPlayer.MediaStatus.EndOfMedia and self.engine.mode=='narration':self.stop_recording()
        elif status in {QMediaPlayer.MediaStatus.InvalidMedia,QMediaPlayer.MediaStatus.StalledMedia}:
            self._playback_error('Video playback stopped or became unavailable.',True)

    def _update_media_ready(self):
        if self.player:
            from PySide6.QtMultimedia import QMediaPlayer
            self._media_ready=bool(self.video and self.video.original and self.video.asset(self.video.original).is_file() and
                Path(self.player.source().toLocalFile()).resolve()==self.video.asset(self.video.original) and self.player.hasVideo() and self.player.duration()>0 and
                self.player.mediaStatus() in {QMediaPlayer.MediaStatus.LoadedMedia,QMediaPlayer.MediaStatus.BufferedMedia,QMediaPlayer.MediaStatus.EndOfMedia})
        self._refresh()

    def _playback_error(self,text,main):
        if main:
            self._media_ready=False
            if self.engine and self.engine.mode=='narration' and self.engine.busy:
                self._narration_failure='Narration stopped because the video could not play: '+text
                self.stop_recording()
        self.status.setText('Playback: '+text);self._refresh()

    def play_pause(self):
        if self.busy or not self.video or not self.video.original:return
        self._ensure_media()
        if self.player.source().isEmpty():self._load_media()
        from PySide6.QtMultimedia import QMediaPlayer
        if self.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState:self.player.pause()
        else:
            if self.player.position()<self.video.trim_start*1000 or self.player.position()>=(self.video.trim_end or self.video.duration)*1000:self.player.setPosition(round(self.video.trim_start*1000))
            self.player.play()

    def _seek(self):
        if self.player and not self.busy:self.player.setPosition(self.position.value());self.voice_player.setPosition(self.position.value())

    def _audio_mode(self):
        if not self.player:return
        voice=bool(self.video and self.video.use_narration)
        self.audio.setMuted(voice or bool(self.engine and self.engine.mode=='narration'))
        volume=self.volume.value()/100;self.audio.setVolume(volume);self.voice_audio.setVolume(volume)
        if not voice:self.voice_player.stop()
        elif not self.busy:self._play_state(self.player.playbackState())

    def _edited(self):
        if self.loading or not self.video or self.busy:return False
        try:
            from dataclasses import replace
            updated=replace(self.video,trim_start=self.start.value(),trim_end=self.end.value(),volume=self.volume.value()/100,use_narration=self.use_voice.isChecked())
            updated.save();self.video=updated;self._audio_mode();self._refresh()
            return True
        except Exception as exc:self.status.setText(str(exc));return False

    def export(self):
        if self.busy or not self.video:return
        self._ensure_media()
        if not self._edited():return
        self.player.pause();self.voice_player.pause();self.test_player.stop()
        path,_=QFileDialog.getSaveFileName(self,'Export training video',str(self.video.root/'training-video.mp4'),'MP4 video (*.mp4)')
        if not path:return
        chosen=Path(path);output=chosen.with_suffix('.mp4')
        if output!=chosen and output.exists() and QMessageBox.question(self,'Replace MP4 export?',f'{output.name} already exists. Replace it?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        try:
            self.progress.setValue(0);self.exporter.start(self.video,output);self.status.setText('Exporting MP4. Originals and existing output are retained until success.');self._refresh()
        except Exception as exc:self.status.setText('Could not export: '+str(exc));self._refresh()

    def _progress(self,value):self.progress.setValue(value)

    def _exported(self,path,error):
        self.status.setText(str(error) if error else 'MP4 saved: '+str(path));self._refresh()

    def open_folder(self):
        if self.video:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.video.root)))

    def _refresh(self):
        busy=self.busy;has_video=bool(self.video and self.video.original)
        for item in (self.new_button,self.open_button,self.source,self.mic,self.refresh_button,self.minimize,self.test_button,self.record_button):item.setEnabled(not busy)
        for item in (self.start,self.end,self.volume,self.play_button,self.position,self.narrate_button):item.setEnabled(has_video and not busy)
        self.narrate_button.setEnabled(has_video and self._media_ready and not busy)
        self.use_voice.setEnabled(bool(self.video and self.video.narration) and not busy)
        self.export_button.setEnabled(has_video and not busy and self.video.duration>0)
        self.pause_button.setEnabled(bool(self.engine and self.engine.state in {'recording','paused'}));self.stop_button.setEnabled(bool(self.engine and self.engine.busy))
        self.cancel_button.setEnabled(self.exporter.busy);self.folder_button.setEnabled(self.video is not None)

    def prepare_close(self):
        if self.busy:
            self.status.setText('Stop recording and wait for finalization, or cancel the export before closing.');return False
        if self.player:
            for player in (self.player,self.voice_player,self.test_player):player.stop();player.setSource(QUrl())
        self.floating.hide();return True
