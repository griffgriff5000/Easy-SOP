"""Section-based local training video editor."""
from pathlib import Path
from copy import deepcopy
from dataclasses import asdict
import threading,tempfile,time,shutil
from PIL import Image,ImageOps
from PySide6.QtCore import Qt,QUrl,QTimer,Signal
from PySide6.QtGui import QColor,QImage
from PySide6.QtWidgets import (QDialog,QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QSplitter,
    QListWidget,QPushButton,QLabel,QLineEdit,QPlainTextEdit,QDoubleSpinBox,QSpinBox,QComboBox,
    QTabWidget,QSlider,QCheckBox,QFileDialog,QMessageBox,QColorDialog,QProgressBar)
from .components import scroll_panel,page_header
from .video_canvas import VideoCanvas
from ..models import Annotation
from ..video_timeline import (SIZE,legacy_section,section_duration,split_section,trim_section,
    validate_timeline,render_card)
from ..media_export import VideoExport


class VideoEditorDialog(QDialog):
    worker_done=Signal(object,object)
    download_progress=Signal(int)

    def __init__(self,session,library=None,parent=None):
        super().__init__(parent);self.setWindowTitle('Training video editor');self.resize(1360,880)
        self.session=deepcopy(session);self.library=library;self.edit_index=None;self.loading=False;self.history=[];self.future=[]
        self.request_recording=False;self.working=False;self.probing=False;self.cancel_event=threading.Event()
        self.active_overlays=[];self.previewing=False;self.frame_time=0;self.relative_position=0
        self.preview_directory=None;self.narration_error=None
        if not self.session.timeline and self.session.original:self.session.timeline=[legacy_section(self.session)]
        box=QVBoxLayout(self)
        page_header(box,'Video editor','Arrange sections, trim footage and add timed annotations. Originals stay unchanged. Changes save to this session.')
        actions=QHBoxLayout();self.action_buttons=[]
        self._button('Import clip...',self.import_clip,actions)
        self._button('Record another section',self.record_section,actions)
        self._button('Title screen',lambda:self.add_card('Title'),actions)
        self._button('Credits screen',lambda:self.add_card('Credits'),actions)
        self.undo_button=self._button('Undo',self.undo,actions);self.redo_button=self._button('Redo',self.redo,actions)
        actions.addStretch();self._button('Preview full video',lambda:self.export(True),actions)
        self._button('Export MP4...',lambda:self.export(False),actions);box.addLayout(actions)
        split=QSplitter();left=QWidget();leftbox=QVBoxLayout(left);leftbox.setContentsMargins(0,0,0,0)
        leftbox.addWidget(QLabel('Sections in playback order'));self.sections=QListWidget();self.sections.currentRowChanged.connect(self._selected);leftbox.addWidget(self.sections)
        moves=QHBoxLayout();self._button('Up',lambda:self.move_section(-1),moves);self._button('Down',lambda:self.move_section(1),moves);leftbox.addLayout(moves)
        moves=QHBoxLayout();self._button('Duplicate',self.duplicate,moves);self._button('Remove',self.remove_section,moves);leftbox.addLayout(moves)
        split.addWidget(left)
        center=QWidget();centerbox=QVBoxLayout(center);centerbox.setContentsMargins(0,0,0,0)
        self.canvas=VideoCanvas();self.canvas.before_edit=self._before_draw;self.canvas.changed.connect(self._canvas_changed);self.canvas.selection_changed.connect(self._canvas_selected)
        centerbox.addWidget(self.canvas,1)
        playback=QHBoxLayout();self.play_button=self._button('Play / pause',self.play_pause,playback)
        self.position=QSlider(Qt.Orientation.Horizontal);self.position.sliderMoved.connect(self.seek);playback.addWidget(self.position,1)
        self.clock=QLabel('0.0 s');playback.addWidget(self.clock);centerbox.addLayout(playback)
        row=QHBoxLayout();self.split_button=self._button('Split at playhead',lambda:self.split_at(self.relative_position),row)
        self.trim_start_button=self._button('Trim start here',lambda:self._trim_here(True),row);self.trim_end_button=self._button('Trim end here',lambda:self._trim_here(False),row);centerbox.addLayout(row)
        split.addWidget(center)
        self.tabs=QTabWidget();properties=QWidget();properties.setObjectName("scrollPage");form=QFormLayout(properties);self.properties_form=form
        self.name=QLineEdit();form.addRow('Section name',self.name)
        self.start=self._seconds();self.end=self._seconds();form.addRow('Source start',self.start);form.addRow('Source end',self.end)
        self.volume=self._seconds(0,100);self.volume.setSuffix(' %');self.volume.setValue(100);form.addRow('Volume',self.volume)
        self.use_voice=QCheckBox('Use section voiceover');form.addRow(self.use_voice)
        self.card_duration=self._seconds(.1,120);form.addRow('Card duration',self.card_duration)
        self.card_text=QPlainTextEdit();self.card_text.setPlaceholderText('Title subtitle, training details or credits');self.card_text.setMaximumHeight(170);form.addRow('Card text',self.card_text)
        self.background='#10354b';self.foreground='#ffffff';self.logo=None
        self.background_button=QPushButton('Background colour');self.background_button.clicked.connect(lambda:self.choose_card_colour('background'));form.addRow(self.background_button)
        self.foreground_button=QPushButton('Text colour');self.foreground_button.clicked.connect(lambda:self.choose_card_colour('foreground'));form.addRow(self.foreground_button)
        self.logo_button=QPushButton('Choose logo...');self.logo_button.clicked.connect(self.choose_logo);form.addRow(self.logo_button)
        self.clear_logo=QPushButton('Remove logo');self.clear_logo.clicked.connect(lambda:self._set_logo(None));form.addRow(self.clear_logo)
        self.apply_button=QPushButton('Apply section changes');self.apply_button.setObjectName('primary');self.apply_button.clicked.connect(self.apply_properties);form.addRow(self.apply_button)
        self.mic=QComboBox();self.mic.addItem('Select microphone...',None);form.addRow('Voiceover mic',self.mic)
        self.narrate_button=QPushButton('Record section voiceover');self.narrate_button.clicked.connect(self.record_narration);form.addRow(self.narrate_button)
        self.speech_button=QPushButton('Text to speech...');self.speech_button.clicked.connect(self.open_speech);form.addRow(self.speech_button)
        self.pause_voice=QPushButton('Pause / resume voiceover');self.pause_voice.clicked.connect(lambda:self.recorder.pause());form.addRow(self.pause_voice)
        self.stop_voice=QPushButton('Stop voiceover');self.stop_voice.clicked.connect(lambda:self.recorder.stop());form.addRow(self.stop_voice)
        self.tabs.addTab(scroll_panel(properties),'Section')
        annotations=QWidget();annotations.setObjectName("scrollPage");anno=QFormLayout(annotations)
        self.tool=QComboBox()
        for label,kind in [('Select / move','edit'),('Arrow','arrow'),('Straight line','line'),('Box','highlight'),('Ellipse','circle'),('Highlight','highlighter'),('Text','text'),('Callout','callout')]:self.tool.addItem(label,kind)
        self.tool.currentIndexChanged.connect(self._tool_changed);anno.addRow('Draw tool',self.tool)
        self.designs=QComboBox();self.designs.addItem('Choose saved design...',None)
        if library:
            for identity,title in library.entries():self.designs.addItem(title,identity)
        self.designs.currentIndexChanged.connect(self._design_changed);anno.addRow('Custom designs',self.designs)
        self.annotation_text=QPlainTextEdit('Text label');self.annotation_text.setMaximumHeight(85);anno.addRow('Label',self.annotation_text)
        self.annotation_colour='#ef4444';self.colour_button=QPushButton('Annotation colour');self.colour_button.clicked.connect(self.choose_annotation_colour);anno.addRow(self.colour_button)
        self.stroke=QSpinBox();self.stroke.setRange(1,30);self.stroke.setValue(4);anno.addRow('Line width',self.stroke)
        self.font_size=QSpinBox();self.font_size.setRange(8,144);self.font_size.setValue(32);anno.addRow('Text size',self.font_size)
        self.opacity=QSpinBox();self.opacity.setRange(1,100);self.opacity.setValue(30);anno.addRow('Highlight opacity %',self.opacity)
        self.annotation_start=self._seconds();self.annotation_end=self._seconds();anno.addRow('Appears at',self.annotation_start);anno.addRow('Disappears at',self.annotation_end)
        self.overlays=QListWidget();self.overlays.setMaximumHeight(170);self.overlays.currentRowChanged.connect(self._overlay_selected);anno.addRow('Timed annotations',self.overlays)
        apply_annotation=QPushButton('Apply annotation style / timing');apply_annotation.clicked.connect(self.apply_annotation);anno.addRow(apply_annotation)
        delete_annotation=QPushButton('Remove selected annotation');delete_annotation.clicked.connect(self.delete_annotation);anno.addRow(delete_annotation)
        note=QLabel('Times are relative to this section. Pause, choose a tool and drag over the preview. Select / move also resizes shapes.');note.setWordWrap(True);anno.addRow(note)
        self.tabs.addTab(scroll_panel(annotations),'Annotations');split.addWidget(self.tabs)
        split.setSizes([210,820,310]);split.setStretchFactor(1,1);box.addWidget(split,1)
        footer=QHBoxLayout();self.status=QLabel('Ready');self.status.setWordWrap(True);footer.addWidget(self.status,1)
        self.progress=QProgressBar();self.progress.setMaximumWidth(160);footer.addWidget(self.progress)
        self.cancel_button=QPushButton('Cancel operation');self.cancel_button.clicked.connect(self.cancel_operation);footer.addWidget(self.cancel_button)
        footer.addWidget(self.pause_voice);footer.addWidget(self.stop_voice)
        self.save_button=QPushButton('Save and close');self.save_button.clicked.connect(self.accept);footer.addWidget(self.save_button);box.addLayout(footer)
        from ..video_recorder import VideoRecorder
        self.recorder=VideoRecorder(self);self.recorder.changed.connect(self._record_state);self.recorder.completed.connect(self._narrated)
        from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput,QVideoSink,QMediaDevices
        self.player=QMediaPlayer(self);self.audio=QAudioOutput(self);self.player.setAudioOutput(self.audio);self.sink=QVideoSink(self);self.player.setVideoSink(self.sink)
        self.voice_player=QMediaPlayer(self);self.voice_audio=QAudioOutput(self);self.voice_player.setAudioOutput(self.voice_audio)
        self.player.positionChanged.connect(self._position);self.player.mediaStatusChanged.connect(self._media_status)
        self.player.errorOccurred.connect(lambda code,text:self._play_error(text));self.sink.videoFrameChanged.connect(self._frame)
        self.probe=QMediaPlayer(self);self.probe.durationChanged.connect(lambda _:self._probed());self.probe.hasVideoChanged.connect(lambda _:self._probed())
        self.probe.errorOccurred.connect(lambda code,text:self._probe_failed(text))
        self.probe_timer=QTimer(self);self.probe_timer.setSingleShot(True);self.probe_timer.timeout.connect(lambda:self._probe_failed('The imported clip did not become playable.'))
        for device in QMediaDevices.audioInputs():self.mic.addItem(device.description(),bytes(device.id()))
        self.card_timer=QTimer(self);self.card_timer.setInterval(50);self.card_timer.timeout.connect(self._card_tick)
        self.exporter=VideoExport(self);self.exporter.finished.connect(self._exported);self.exporter.progress.connect(self.progress.setValue)
        self.worker_done.connect(self._worker_finished);self.download_progress.connect(self.progress.setValue)
        for field in (self.stroke,self.font_size,self.opacity):field.valueChanged.connect(self._annotation_style)
        self.annotation_text.textChanged.connect(self._annotation_style)
        self._annotation_style();self._list(0);self._refresh()

    def _button(self,text,callback,layout):
        button=QPushButton(text);button.clicked.connect(callback);layout.addWidget(button);self.action_buttons.append(button);return button

    @staticmethod
    def _seconds(low=0,high=360000):
        field=QDoubleSpinBox();field.setRange(low,high);field.setDecimals(3);field.setSuffix(' s');return field

    @property
    def busy(self):return self.working or self.probing or self.exporter.busy or self.recorder.busy

    def current(self):
        index=self.sections.currentRow()
        return self.session.timeline[index] if 0<=index<len(self.session.timeline) else None

    def _refresh(self):
        busy=self.busy
        for button in self.action_buttons:button.setEnabled(not busy)
        self.undo_button.setEnabled(not busy and bool(self.history));self.redo_button.setEnabled(not busy and bool(self.future))
        for widget in (self.sections,self.tabs,self.canvas,self.position,self.save_button):widget.setEnabled(not busy)
        for button in (self.split_button,self.trim_start_button,self.trim_end_button):button.setEnabled(not busy and not self.previewing and bool(self.current() and self.current()["kind"]=="video"))
        self.canvas.setEnabled(not busy and not self.previewing)
        self.tabs.setEnabled(not busy and not self.previewing)
        self.pause_voice.setEnabled(self.recorder.state in {'recording','paused'});self.stop_voice.setEnabled(self.recorder.busy)
        self.cancel_button.setEnabled(self.working or self.probing or self.exporter.busy)

    def _list(self,index):
        self.loading=True;self.edit_index=None;self.sections.clear()
        for i,section in enumerate(self.session.timeline,1):self.sections.addItem(f"{i:02d}  {section['title']}\n{section_duration(section):.1f} s · {section['kind']}")
        self.sections.setCurrentRow(min(index,len(self.session.timeline)-1));self.loading=False;self._selected()

    def _selected(self,*args):
        if self.loading:return
        index=self.sections.currentRow()
        if self.edit_index is not None and self.edit_index!=index and not self._flush_properties():
            self.sections.blockSignals(True);self.sections.setCurrentRow(self.edit_index);self.sections.blockSignals(False);return
        self.edit_index=index if index>=0 else None
        self.card_timer.stop();self.previewing=False;self.relative_position=0;self.canvas.select(None)
        section=self.current();self.loading=True
        if section:
            card=section['kind']=='card';self.name.setText(section['title']);self.start.setValue(section.get('start',0));self.end.setValue(section.get('end',0))
            self.volume.setValue(section.get('volume',1)*100);self.use_voice.setChecked(section.get('use_narration',False))
            if self.card_text.toPlainText()!=section.get('text',''):self.card_text.setPlainText(section.get('text',''))
            self.card_duration.setValue(section.get('duration',5));self.background=section.get('background','#10354b');self.foreground=section.get('foreground','#ffffff');self.logo=section.get('logo')
            for item in (self.start,self.end,self.volume,self.use_voice,self.mic,self.narrate_button,self.speech_button):
                item.setEnabled(not card);self.properties_form.setRowVisible(item,not card)
            for item in (self.card_duration,self.card_text,self.background_button,self.foreground_button,self.logo_button,self.clear_logo):
                item.setEnabled(card);self.properties_form.setRowVisible(item,card)
            self.position.setRange(0,round(section_duration(section)*1000));self.position.setValue(0)
            self.annotation_start.setValue(0);self.annotation_end.setValue(section_duration(section))
            try:self.canvas.set_frame(render_card(self.session,section) if card else Image.new('RGB',SIZE,'#172e42'))
            except (OSError,ValueError) as exc:self.canvas.set_frame(Image.new('RGB',SIZE,'#172e42'));self.status.setText(str(exc))
            self.player.stop();self.voice_player.stop()
            source=QUrl() if card else QUrl.fromLocalFile(str(self.session.asset(section['source'])))
            if self.player.source()!=source:self.player.setSource(source)
            if not card:self.player.setPosition(round(section['start']*1000))
            voice=QUrl.fromLocalFile(str(self.session.asset(section['narration']))) if section.get('use_narration') and section.get('narration') else QUrl()
            if self.voice_player.source()!=voice:self.voice_player.setSource(voice)
            self.audio.setVolume(section.get('volume',1));self.voice_audio.setVolume(section.get('volume',1));self.audio.setMuted(section.get('use_narration',False))
        self.loading=False;self._annotations();self._refresh()

    def _commit(self,sections,index=None,reload=True):
        if self.busy:return False
        try:
            validate_timeline(self.session,sections)
            old=self.session.timeline;self.session.timeline=sections
            try:self.session.save()
            except Exception:self.session.timeline=old;raise
            self.history.append(deepcopy(old));self.history=self.history[-20:];self.future.clear()
            if reload:self._list(self.sections.currentRow() if index is None else index)
            else:self._annotations();self._refresh()
            self.status.setText('Changes saved. Originals retained.');return True
        except Exception as exc:self.status.setText(str(exc));return False

    def save(self):
        try:self.session.save();return True
        except Exception as exc:self.status.setText(str(exc));return False

    def undo(self):
        if not self._flush_properties():return
        if self.busy or not self.history:return
        old=self.session.timeline;self.session.timeline=self.history[-1]
        if self.save():self.future.append(deepcopy(old));self.history.pop();self._list(0)
        else:self.session.timeline=old

    def redo(self):
        if not self._flush_properties():return
        if self.busy or not self.future:return
        old=self.session.timeline;self.session.timeline=self.future[-1]
        if self.save():self.history.append(deepcopy(old));self.future.pop();self._list(0)
        else:self.session.timeline=old

    def split_at(self,position):
        if not self._flush_properties():return
        section=self.current()
        if not section:return
        try:
            index=self.sections.currentRow();sections=deepcopy(self.session.timeline);sections[index:index+1]=split_section(section,position);self._commit(sections,index+1)
        except Exception as exc:self.status.setText(str(exc))

    def move_section(self,direction):
        if not self._flush_properties():return
        index=self.sections.currentRow();destination=index+direction
        if not 0<=destination<len(self.session.timeline):return
        sections=deepcopy(self.session.timeline);sections.insert(destination,sections.pop(index));self._commit(sections,destination)

    def duplicate(self):
        if not self._flush_properties():return
        index=self.sections.currentRow()
        if index<0:return
        sections=deepcopy(self.session.timeline);sections.insert(index+1,deepcopy(sections[index]));self._commit(sections,index+1)

    def remove_section(self):
        if not self._flush_properties():return
        index=self.sections.currentRow()
        if index<0:return
        if len(self.session.timeline)==1:self.status.setText('Keep at least one section; add a replacement before removing this one.');return
        sections=deepcopy(self.session.timeline);sections.pop(index);self._commit(sections,max(0,index-1))

    def add_card(self,title):
        if not self._flush_properties():return
        index=self.sections.currentRow()+1;sections=deepcopy(self.session.timeline)
        section=dict(kind='card',title=title,text='Training details' if title=='Title' else 'Created by',duration=5,background='#10354b',foreground='#ffffff',logo=None,overlays=[])
        if title=='Title':index=0
        if title=='Credits':index=len(sections)
        sections.insert(index,section);self._commit(sections,index)

    def _flush_properties(self):
        if self.loading or self.edit_index is None:return True
        if self.busy:return False
        index=self.edit_index
        if not 0<=index<len(self.session.timeline):return True
        old=self.session.timeline[index];item=deepcopy(old);item['title']=self.name.text()
        if item['kind']=='video':
            item=trim_section(item,self.start.value(),self.end.value())
            item.update(title=self.name.text(),volume=self.volume.value()/100,use_narration=self.use_voice.isChecked())
        else:
            duration=self.card_duration.value();item.update(text=self.card_text.toPlainText(),duration=duration,background=self.background,foreground=self.foreground,logo=self.logo)
            item['overlays']=[o|dict(end=min(o['end'],duration)) for o in item['overlays'] if o['start']<duration]
        if item==old:return True
        try:
            sections=deepcopy(self.session.timeline);sections[index]=item;validate_timeline(self.session,sections)
            previous=self.session.timeline;self.session.timeline=sections
            try:self.session.save()
            except Exception:self.session.timeline=previous;raise
            self.history.append(deepcopy(previous));self.history=self.history[-20:];self.future.clear()
            self.sections.item(index).setText(f"{index+1:02d}  {item['title']}\n{section_duration(item):.1f} s ? {item['kind']}")
            if self.sections.currentRow()==index:
                self.position.setRange(0,round(section_duration(item)*1000));self.relative_position=min(self.relative_position,section_duration(item))
                if item['kind']=='card':self.canvas.set_frame(render_card(self.session,item))
                self.audio.setVolume(item.get('volume',1));self.audio.setMuted(item.get('use_narration',False));self.voice_audio.setVolume(item.get('volume',1))
                voice=QUrl.fromLocalFile(str(self.session.asset(item['narration']))) if item.get('use_narration') and item.get('narration') else QUrl()
                if self.voice_player.source()!=voice:self.voice_player.stop();self.voice_player.setSource(voice)
                if not item.get('use_narration'):self.voice_player.stop()
                self._annotations()
            self.status.setText('Changes saved.');self._refresh();return True
        except Exception as exc:self.status.setText(str(exc));return False

    def apply_properties(self):return self._flush_properties()

    def _trim_here(self,start):
        section=self.current()
        if not section or section['kind']!='video':return
        (self.start if start else self.end).setValue(section['start']+self.relative_position);self.apply_properties()

    def choose_card_colour(self,key):
        colour=QColorDialog.getColor(QColor(getattr(self,key)),self,'Card '+key)
        if colour.isValid():setattr(self,key,colour.name());self.apply_properties()

    def _set_logo(self,name):self.logo=name;self.apply_properties()

    def choose_logo(self):
        if self.busy:return
        path,_=QFileDialog.getOpenFileName(self,'Card logo','','Images (*.png *.jpg *.jpeg)')
        if not path:return
        try:
            with Image.open(path) as source:
                if source.width*source.height>16_000_000:raise ValueError('Choose a logo under 16 million pixels.')
                image=source.convert('RGBA');image.thumbnail((1024,1024));target=self.session.new_asset('card-logo','.png');image.save(target)
            self._set_logo(target.name)
        except Exception as exc:self.status.setText(str(exc))

    def _before_draw(self):
        if self.previewing or self.busy:return False
        self.pause_playback();return self._flush_properties()

    def _tool_changed(self):
        self.pause_playback();self.canvas.set_tool(self.tool.currentData());self._annotation_style()

    def _design_changed(self):
        identity=self.designs.currentData()
        if identity and self.library:
            try:self.pause_playback();self.canvas.design_template=self.library.load(identity)[1];self.canvas.set_tool('design')
            except Exception as exc:self.status.setText(str(exc))

    def _annotation_style(self):
        self.canvas.draw_color=self.annotation_colour;self.canvas.draw_width=self.stroke.value();self.canvas.draw_font_size=self.font_size.value()
        self.canvas.draw_text=self.annotation_text.toPlainText();self.canvas.draw_opacity=self.opacity.value()

    def choose_annotation_colour(self):
        colour=QColorDialog.getColor(QColor(self.annotation_colour),self,'Annotation colour')
        if colour.isValid():self.annotation_colour=colour.name();self._annotation_style()

    def _annotations(self):
        section=self.current();selected=self.overlays.currentRow();self.loading=True;self.overlays.clear();self.canvas.select(None);self.active_overlays=[]
        if section:
            for i,item in enumerate(section['overlays']):
                self.overlays.addItem(f"{i+1}. {item['annotation'].get('kind','shape')}  {item['start']:.1f}–{item['end']:.1f} s")
                if item['start']<=self.relative_position<item['end']:self.active_overlays.append(i)
            self.canvas.step.annotations=[Annotation(**section['overlays'][i]['annotation']) for i in self.active_overlays]
        else:self.canvas.step.annotations=[]
        if section and 0<=selected<len(section['overlays']):
            self.overlays.setCurrentRow(selected)
            if selected in self.active_overlays:self.canvas.select(self.active_overlays.index(selected))
        self.loading=False;self.canvas.refresh()

    def _canvas_changed(self):
        if self.busy or self.previewing or not self.current():return
        section=deepcopy(self.current());annotations=self.canvas.step.annotations
        for index,annotation in zip(self.active_overlays,annotations):section['overlays'][index]['annotation']=asdict(annotation)
        for annotation in annotations[len(self.active_overlays):]:section['overlays'].append(dict(start=self.annotation_start.value(),end=self.annotation_end.value(),annotation=asdict(annotation)))
        sections=deepcopy(self.session.timeline);sections[self.sections.currentRow()]=section
        position=self.relative_position
        if self._commit(sections,reload=False):self.seek(round(position*1000))
        else:self._annotations()

    def _canvas_selected(self,selected):
        if self.loading or not selected or self.canvas.selected is None or self.canvas.selected>=len(self.active_overlays):return
        self.overlays.setCurrentRow(self.active_overlays[self.canvas.selected])

    def _overlay_selected(self,index):
        if self.loading or not self.current() or index<0:return
        item=self.current()['overlays'][index];self.annotation_start.setValue(item['start']);self.annotation_end.setValue(item['end'])
        a=Annotation(**item['annotation']);self.annotation_text.setPlainText(a.text);self.annotation_colour=a.color;self.stroke.setValue(a.width);self.font_size.setValue(a.font_size);self.opacity.setValue(a.opacity)
        self.pause_playback()
        if not item['start']<=self.relative_position<item['end']:
            self.seek(round(item['start']*1000));self.overlays.blockSignals(True);self.overlays.setCurrentRow(index);self.overlays.blockSignals(False)
        if index in self.active_overlays:
            self.canvas.set_tool('edit');self.canvas.select(self.active_overlays.index(index))

    def apply_annotation(self):
        if not self._flush_properties():return
        if self.busy:return
        self._annotation_style();index=self.overlays.currentRow();section=self.current()
        if not section:return
        if index<0:self.status.setText('Style and timing set for the next shape. Drag over the preview.');return
        sections=deepcopy(self.session.timeline);item=sections[self.sections.currentRow()]['overlays'][index]
        item.update(start=self.annotation_start.value(),end=self.annotation_end.value())
        item['annotation'].update(color=self.annotation_colour,width=self.stroke.value(),font_size=self.font_size.value(),opacity=self.opacity.value(),text=self.annotation_text.toPlainText())
        self._commit(sections,reload=False)

    def delete_annotation(self):
        if not self._flush_properties():return
        index=self.overlays.currentRow()
        if index<0 or not self.current():return
        sections=deepcopy(self.session.timeline);sections[self.sections.currentRow()]['overlays'].pop(index);self._commit(sections,reload=False)

    def pause_playback(self):self.player.pause();self.voice_player.pause();self.card_timer.stop()

    def play_pause(self):
        if self.busy or not self.current():return
        from PySide6.QtMultimedia import QMediaPlayer
        if self.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState or self.card_timer.isActive():self.pause_playback();return
        if self.previewing:self.player.play();return
        section=self.current()
        if self.relative_position>=section_duration(section)-.02:self.seek(0)
        if section['kind']=='card':self.card_tick_time=time.monotonic();self.card_timer.start()
        else:self.player.play();self._voice_sync(True)

    def seek(self,milliseconds):
        if self.busy or not self.current():return
        duration=sum(section_duration(s) for s in self.session.timeline) if self.previewing else section_duration(self.current())
        self.relative_position=max(0,min(duration,milliseconds/1000));self.position.setValue(round(self.relative_position*1000));self.clock.setText(f'{self.relative_position:.1f} s')
        if not self.previewing and self.current()['kind']=='video':self.player.setPosition(round((self.current()['start']+self.relative_position)*1000));self._voice_sync(False)
        elif self.previewing:self.player.setPosition(milliseconds)
        if not self.previewing:self._annotations()
        else:self.canvas.step.annotations=[];self.canvas.refresh()

    def _position(self,milliseconds):
        if self.loading or not self.current():return
        section=self.current();position=milliseconds/1000 if self.previewing else milliseconds/1000-section.get('start',0)
        if not self.previewing and section['kind']=='card':return
        self.relative_position=max(0,position)
        if not self.position.isSliderDown():self.position.setValue(round(self.relative_position*1000))
        self.clock.setText(f'{self.relative_position:.1f} s')
        if not self.previewing:
            if position>=section_duration(section):
                self.pause_playback()
                if self.recorder.busy:self.recorder.stop()
            self._voice_sync(False);self._annotations()

    def _voice_sync(self,playing):
        section=self.current()
        if not section or not section.get('use_narration') or self.previewing or self.recorder.busy:return
        position=(section['start']+self.relative_position-section['narration_origin'])*1000
        if position<0:self.voice_player.pause();return
        if abs(self.voice_player.position()-position)>150:self.voice_player.setPosition(round(position))
        from PySide6.QtMultimedia import QMediaPlayer
        if playing or self.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState:self.voice_player.play()

    def _frame(self,frame):
        if not frame.isValid() or time.monotonic()-self.frame_time<.066:return
        self.frame_time=time.monotonic();image=frame.toImage().convertToFormat(QImage.Format.Format_RGB888)
        raw=bytes(image.constBits());source=Image.frombytes('RGB',(image.width(),image.height()),raw,'raw','RGB',image.bytesPerLine())
        source=ImageOps.contain(source,SIZE);image=Image.new('RGB',SIZE);image.paste(source,((1280-source.width)//2,(720-source.height)//2))
        self.canvas.set_frame(image)

    def _card_tick(self):
        now=time.monotonic();position=self.relative_position+now-self.card_tick_time;self.card_tick_time=now;self.seek(round(position*1000))
        if self.relative_position>=section_duration(self.current()):self.card_timer.stop()

    def _media_status(self,status):
        from PySide6.QtMultimedia import QMediaPlayer
        if status==QMediaPlayer.MediaStatus.LoadedMedia and self.current() and not self.previewing:self.player.setPosition(round((self.current().get('start',0)+self.relative_position)*1000))
        if status==QMediaPlayer.MediaStatus.EndOfMedia and self.recorder.busy:self.recorder.stop()
        elif status in {QMediaPlayer.MediaStatus.InvalidMedia,QMediaPlayer.MediaStatus.StalledMedia} and self.recorder.busy:self._play_error('Video playback became unavailable.')

    def _play_error(self,text):
        self.status.setText('Playback: '+text)
        if self.recorder.busy:self.narration_error=text;self.recorder.stop()

    def record_section(self):
        if not self._flush_properties():return
        if not self.busy and self.save():self.request_recording=True;self.accept()

    def record_narration(self):
        if self.busy or not self.current() or self.current()['kind']!='video':return
        try:
            from PySide6.QtMultimedia import QMediaDevices
            if not self.player.hasVideo() or self.player.duration()<=0:raise ValueError('Wait for a playable video before narrating.')
            device=next((d for d in QMediaDevices.audioInputs() if bytes(d.id())==self.mic.currentData()),None)
            if device is None:raise ValueError('Select a microphone first.')
            if not self.apply_properties():return
            if not self.player.hasVideo() or self.player.duration()<=0:raise ValueError('Wait for the edited section to load, then record its voiceover.')
            self.tabs.setCurrentIndex(0);self.seek(0);self.narration_error=None;self.voice_player.stop();self.audio.setMuted(True)
            self.recorder.start_audio(device,self.session.new_asset('section-voiceover','.wav'),'narration')
        except Exception as exc:self.status.setText(str(exc));self._refresh()

    def open_speech(self):
        if self.busy or not self.current() or self.current()['kind']!='video':return
        if not self.apply_properties():return
        from .speech_dialog import SpeechDialog
        index=self.sections.currentRow();section=self.current();self.pause_playback();self.voice_player.stop()
        dialog=SpeechDialog(section_duration(section),section.get('speech'),lambda path,settings:self._apply_speech(index,path,settings),self,getattr(self,'speech_target',None))
        dialog.exec();dialog.deleteLater()

    def _apply_speech(self,index,path,settings):
        if index!=self.sections.currentRow() or not 0<=index<len(self.session.timeline):raise ValueError('The selected section changed.')
        asset=self.session.new_asset('section-voiceover','.wav');partial=asset.with_name('.'+asset.name+'.partial')
        try:
            shutil.copyfile(path,partial);partial.replace(asset)
            sections=deepcopy(self.session.timeline);item=sections[index]
            item.update(narration=asset.name,narration_origin=item['start'],use_narration=True,speech=dict(settings))
            if not self._commit(sections,index):raise ValueError(self.status.text())
        except BaseException:
            partial.unlink(missing_ok=True);asset.unlink(missing_ok=True);raise
        self.status.setText('Text-to-speech voiceover applied. Previous takes were kept in the session.')

    def _record_state(self,state):
        if state=='recording':self.player.play()
        else:self.player.pause()
        self.status.setText('Voiceover: '+state);self._refresh()

    def _narrated(self,mode,path,duration,error):
        self.pause_playback()
        if error or self.narration_error:self.status.setText('Voiceover not selected: '+str(error or self.narration_error));self._selected();return
        sections=deepcopy(self.session.timeline);item=sections[self.sections.currentRow()];item.update(narration=path.name,narration_origin=item['start'],use_narration=True)
        self._commit(sections)

    def _work(self,operation,completed):
        self.working=True;self.cancel_event.clear();self.completion=completed;self._refresh()
        def run():
            try:value,error=operation(),None
            except Exception as exc:value,error=None,exc
            self.worker_done.emit(value,error)
        self.worker=threading.Thread(target=run,daemon=True);self.worker.start()

    def _worker_finished(self,value,error):
        self.working=False
        if error:self.status.setText(str(error));self._refresh();return
        self.completion(value);self._refresh()

    def import_clip(self):
        if not self._flush_properties():return
        if self.busy:return
        path,_=QFileDialog.getOpenFileName(self,'Import video clip','','Video (*.mp4 *.mkv *.mov *.avi *.webm)')
        if not path:return
        self.pause_playback();source=Path(path);target=self.session.new_asset('import',source.suffix.lower())
        self.status.setText('Copying clip into the video session...')
        def copy():
            try:
                with source.open('rb') as inp,target.open('xb') as out:
                    while True:
                        if self.cancel_event.is_set():raise RuntimeError('Import cancelled.')
                        chunk=inp.read(1024*1024)
                        if not chunk:break
                        out.write(chunk)
                return target
            except BaseException:target.unlink(missing_ok=True);raise
        self.import_title=source.stem[:200];self._work(copy,self._probe_clip)

    def _probe_clip(self,path):
        if self.cancel_event.is_set():self.status.setText('Import cancelled. Copied file retained.');return
        self.import_path=path;self.probing=True;self.probe.setSource(QUrl.fromLocalFile(str(path)));self.probe_timer.start(15000);self.status.setText('Checking imported video...')

    def _probed(self):
        if not self.probing or not self.probe.hasVideo() or self.probe.duration()<=0:return
        duration=self.probe.duration()/1000;self.probing=False;self.probe_timer.stop();self.probe.stop();self.probe.setSource(QUrl())
        clip=dict(kind='video',title=self.import_title,source=self.import_path.name,source_duration=duration,start=0,end=duration,narration=None,narration_origin=0,use_narration=False,volume=1,overlays=[])
        sections=deepcopy(self.session.timeline);index=self.sections.currentRow()+1;sections.insert(index,clip);self._commit(sections,index)

    def _probe_failed(self,text):
        if not self.probing:return
        self.probing=False;self.probe_timer.stop();self.probe.stop();self.probe.setSource(QUrl());self.status.setText('Import not added: '+text+' Copied file retained.');self._refresh()

    def export(self,preview=False):
        if self.busy or not self.session.timeline:return
        self.pause_playback()
        if self.previewing:self._selected()
        if not self.apply_properties():return
        if preview:
            if self.preview_directory:self.preview_directory.cleanup()
            self.preview_directory=tempfile.TemporaryDirectory(prefix='.editor-preview-',dir=self.session.root)
            output=Path(self.preview_directory.name)/'preview.mp4'
        else:
            path,_=QFileDialog.getSaveFileName(self,'Export edited video',str(self.session.root/'edited-video.mp4'),'MP4 (*.mp4)')
            if not path:return
            chosen=Path(path);output=chosen.with_suffix('.mp4')
            if output!=chosen and output.exists() and QMessageBox.question(self,'Replace MP4?',f'Replace {output.name}?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self.pending_output=output;self.pending_preview=preview;self._start_export()

    def _start_export(self):
        from ..media_runtime import MissingMediaRuntime,install_runtime
        try:
            self.exporter.start(self.session,self.pending_output);self.progress.setValue(0);self.status.setText('Rendering complete video locally...');self._refresh()
        except MissingMediaRuntime:
            answer=QMessageBox.question(self,'Download video export tool?','Download FFmpeg 9.0.2 (115 MB) directly from Gyan on GitHub? The download is checksum-verified. Your video/audio stay local.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel)
            if answer==QMessageBox.StandardButton.Yes:
                self.status.setText('Downloading video exporter...');self._work(lambda:install_runtime(cancel=self.cancel_event,progress=self.download_progress.emit),lambda value:None if self.cancel_event.is_set() else self._start_export())
        except Exception as exc:self.status.setText(str(exc));self._refresh()

    def _exported(self,path,error):
        if error:self.status.setText(str(error))
        elif self.pending_preview:
            self.previewing=True;self.canvas.step.annotations=[];self.canvas.select(None)
            self.position.setRange(0,round(sum(section_duration(s) for s in self.session.timeline)*1000));self.player.setSource(QUrl.fromLocalFile(str(path)));self.audio.setMuted(False);self.audio.setVolume(1);self.player.play();self.status.setText('Full video preview. Select a section to return to editing.')
        else:self.status.setText('MP4 saved: '+str(path))
        self._refresh()

    def cancel_operation(self):
        if self.working:self.cancel_event.set();self.status.setText('Cancelling...')
        if self.probing:self._probe_failed('Cancelled.')
        if self.exporter.busy:self.exporter.cancel()

    def done(self,result):
        if self.busy:self.status.setText('Stop voiceover or cancel the operation before closing.');return
        if self.current() and not self.previewing and not self.apply_properties():return
        if not self.save():return
        self.pause_playback();self.player.setSource(QUrl());self.voice_player.setSource(QUrl());self.probe.setSource(QUrl())
        if self.preview_directory:self.preview_directory.cleanup();self.preview_directory=None
        super().done(result)
