from PySide6.QtWidgets import QMessageBox
from sop_capture.training_video import VideoSession
from sop_capture.video_timeline import legacy_section
from sop_capture.ui.video_editor import VideoEditorDialog


def test_editor_split_reorder_cards_and_undo_save(qt_application,tmp_path):
    session=VideoSession.create(tmp_path,'Editor');session.original='take.mkv';session.duration=10
    session.asset('take.mkv').write_bytes(b'fixture')
    editor=VideoEditorDialog(session)
    assert len(editor.session.timeline)==1
    editor.split_at(4)
    assert len(editor.session.timeline)==2 and editor.session.timeline[1]['start']==4
    editor.move_section(-1)
    assert editor.session.timeline[0]['start']==4
    editor.add_card('Credits')
    assert editor.current()['kind']=='card'
    editor.undo();assert len(editor.session.timeline)==2
    editor.redo();assert len(editor.session.timeline)==3
    editor.save()
    assert len(VideoSession.load(session.root).timeline)==3
    assert session.asset('take.mkv').read_bytes()==b'fixture'
    editor.close()


def test_editor_canvas_changes_persist_annotation_and_timing(qt_application,tmp_path):
    session=VideoSession.create(tmp_path,'Annotations');session.original='take.mkv';session.duration=5
    session.asset('take.mkv').write_bytes(b'fixture')
    editor=VideoEditorDialog(session)
    editor.annotation_start.setValue(1);editor.annotation_end.setValue(3)
    editor.canvas.set_tool('highlight');editor.canvas.apply_gesture((100,100),(300,250))
    item=editor.current()['overlays'][0]
    assert (item['start'],item['end'])==(1,3)
    assert item['annotation']['points']==[100,100,300,250]
    editor.save();assert VideoSession.load(session.root).timeline[0]['overlays']==[item]
    editor.close()


def test_save_and_close_applies_typed_card_properties(qt_application,tmp_path):
    session=VideoSession.create(tmp_path,'Card edits');editor=VideoEditorDialog(session)
    editor.add_card('Title');editor.name.setText('Safety training');editor.card_text.setPlainText('Read first')
    editor.accept()
    card=VideoSession.load(session.root).timeline[0]
    assert card['title']=='Safety training' and card['text']=='Read first'


def test_export_only_cards_and_busy_close_are_supported(qt_application,tmp_path):
    session=VideoSession.create(tmp_path,'Cards only');editor=VideoEditorDialog(session);editor.add_card('Title')
    editor.working=True;editor.done(1);assert editor.result()==0
    editor.working=False;editor.done(1);assert editor.result()==1


def test_full_preview_seek_uses_entire_sequence_and_no_editable_overlays(qt_application,tmp_path):
    session=VideoSession.create(tmp_path,'Preview');editor=VideoEditorDialog(session)
    editor.add_card('Title');editor.add_card('Credits');editor.sections.setCurrentRow(0)
    editor.previewing=True;editor.seek(8000)
    assert editor.relative_position==8 and not editor.canvas.step.annotations
    editor.previewing=False;editor.close()


def test_imported_clip_probes_into_sequence_without_replacing_original(qt_application,tmp_path):
    from types import SimpleNamespace
    session=VideoSession.create(tmp_path,'Import');editor=VideoEditorDialog(session);editor.add_card('Title')
    editor.import_path=session.asset('import.mp4');editor.import_title='Imported section';editor.probing=True
    real=editor.probe;editor.probe=SimpleNamespace(hasVideo=lambda:True,duration=lambda:7000,stop=lambda:None,setSource=lambda value:None)
    editor._probed();editor.probe=real
    assert editor.session.timeline[1]['source']=='import.mp4' and editor.session.timeline[1]['end']==7
    assert not editor.busy and editor.session.original is None
    editor.close()


def test_invalid_annotation_timing_does_not_leave_unsaved_shape(qt_application,tmp_path):
    session=VideoSession.create(tmp_path,'Bad times');editor=VideoEditorDialog(session);editor.add_card('Title')
    editor.annotation_start.setValue(4);editor.annotation_end.setValue(2)
    editor.canvas.set_tool('highlight');editor.canvas.apply_gesture((100,100),(300,250))
    assert not editor.current()['overlays'] and not editor.canvas.step.annotations
    editor.close()


def test_invalid_section_trim_blocks_save_and_close(qt_application,tmp_path):
    session=VideoSession.create(tmp_path,'Invalid trim');session.original='take.mp4';session.duration=5;session.asset('take.mp4').write_bytes(b'fixture')
    editor=VideoEditorDialog(session);editor.start.setValue(4);editor.end.setValue(1);editor.accept()
    assert editor.result()==0 and editor.current()['start']==0
    editor.start.setValue(0);editor.end.setValue(5);editor.close()


def test_switching_sections_and_unrelated_edits_keep_typed_properties(qt_application,tmp_path):
    session=VideoSession.create(tmp_path,'Pending');editor=VideoEditorDialog(session)
    editor.add_card('Title');editor.add_card('Credits');editor.sections.setCurrentRow(0)
    editor.card_text.setPlainText('DO NOT LOSE');editor.sections.setCurrentRow(1);editor.sections.setCurrentRow(0)
    assert editor.card_text.toPlainText()=='DO NOT LOSE'
    editor.name.setText('Edited title');editor.canvas.set_tool('highlight');editor.canvas.apply_gesture((100,100),(300,250))
    assert editor.current()['title']=='Edited title'
    assert editor.card_text.toPlainText()=='DO NOT LOSE'
    editor.close()


def test_invalid_pending_trim_prevents_switching_section(qt_application,tmp_path):
    session=VideoSession.create(tmp_path,'Pending trim');session.original='take.mp4';session.duration=5;session.asset('take.mp4').write_bytes(b'fixture')
    editor=VideoEditorDialog(session);editor.add_card('Credits');editor.sections.setCurrentRow(0)
    editor.start.setValue(4);editor.end.setValue(1);editor.sections.setCurrentRow(1)
    assert editor.sections.currentRow()==0 and editor.start.value()==4 and editor.end.value()==1
    editor.start.setValue(0);editor.end.setValue(5);editor.close()


def test_applying_voiceover_switch_synchronizes_preview_source(qt_application,tmp_path):
    from pathlib import Path
    session=VideoSession.create(tmp_path,'Audio mode');session.original='take.mp4';session.duration=5;session.narration='voice.wav'
    session.asset('take.mp4').write_bytes(b'fixture');session.asset('voice.wav').write_bytes(b'fixture')
    editor=VideoEditorDialog(session);assert editor.voice_player.source().isEmpty()
    editor.use_voice.setChecked(True);assert editor.apply_properties()
    assert Path(editor.voice_player.source().toLocalFile()).resolve()==session.asset('voice.wav')
    editor.use_voice.setChecked(False);assert editor.apply_properties()
    assert editor.voice_player.source().isEmpty()
    editor.close()


def test_unchanged_card_text_is_not_reset_during_preview_transition(qt_application,monkeypatch,tmp_path):
    session=VideoSession.create(tmp_path,'Transitions');editor=VideoEditorDialog(session);editor.add_card('Title')
    calls=[];real=editor.card_text.setPlainText
    monkeypatch.setattr(editor.card_text,'setPlainText',lambda text:calls.append(text) or real(text))
    editor._selected();assert not calls
    editor.close()


def test_adding_annotation_keeps_the_paused_preview_frame(qt_application,tmp_path):
    from PIL import Image
    session=VideoSession.create(tmp_path,'Paused frame');session.original='take.mp4';session.duration=5;session.asset('take.mp4').write_bytes(b'fixture')
    editor=VideoEditorDialog(session);editor.canvas.set_frame(Image.new('RGB',(1280,720),'blue'))
    editor.canvas.set_tool('highlight');editor.canvas.apply_gesture((100,100),(300,250))
    assert editor.canvas.frame.getpixel((10,10))==(0,0,255)
    editor.close()
