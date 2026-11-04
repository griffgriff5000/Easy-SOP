import time,wave
from PySide6.QtWidgets import QMessageBox,QApplication
from sop_capture import speech_runtime as speech
from sop_capture.training_video import VideoSession
from sop_capture.video_timeline import split_section
from sop_capture.ui.speech_dialog import SpeechDialog
from sop_capture.ui.video_editor import VideoEditorDialog


def fake_wave(path,seconds):
    with wave.open(str(path),'wb') as out:out.setnchannels(1);out.setsampwidth(2);out.setframerate(24000);out.writeframes(b'\x01\x00'*int(24000*seconds))


def wait(dialog,condition=lambda d:not d.working):
    deadline=time.monotonic()+5
    while time.monotonic()<deadline and not condition(dialog):QApplication.processEvents();time.sleep(.01)
    QApplication.processEvents()
    assert condition(dialog)


def install_fakes(monkeypatch,seconds=2,calls=None):
    calls=calls if calls is not None else []
    monkeypatch.setattr(speech,'installed_runtime',lambda *a,**k:True)
    def synth(text,voice,speed,output,cancel=None,target=None,progress=None):
        calls.append((text,voice,speed));fake_wave(output,seconds);return seconds
    monkeypatch.setattr(speech,'synthesize',synth);return calls


def test_dialog_defaults_and_apply_requires_matching_preview(qt_application,monkeypatch):
    calls=install_fakes(monkeypatch);applied=[]
    dialog=SpeechDialog(5,apply=lambda path,settings:applied.append((path.exists(),settings)))
    assert dialog.voice.currentData()==21 and 'Emma' in dialog.voice.currentText()
    assert {dialog.voice.itemText(i).split(' - ')[1].split(', ')[1] for i in range(dialog.voice.count())}=={'female','male'}
    assert not dialog.use_button.isEnabled() and not dialog.play_button.isEnabled()
    dialog.generate();assert dialog.status.text() and not calls
    dialog.script.setPlainText('Open the permit.');dialog.speed.setValue(1.1);dialog.generate();wait(dialog)
    assert calls==[('Open the permit.',21,1.1)] and dialog.use_button.isEnabled() and '2.0 s' in dialog.durations.text()
    for change in (lambda:dialog.script.setPlainText('Open permits.'),lambda:dialog.voice.setCurrentIndex(5),lambda:dialog.speed.setValue(1.2)):
        change();assert not dialog.use_button.isEnabled() and not dialog.play_button.isEnabled()
        dialog.script.setPlainText('Open the permit.');dialog.voice.setCurrentIndex(0);dialog.speed.setValue(1.1)
        assert dialog.use_button.isEnabled()
    dialog.script.setPlainText('Something else.');dialog.use_voiceover();assert not applied
    dialog.script.setPlainText('Open the permit.');dialog.use_voiceover()
    assert applied==[(True,dict(script='Open the permit.',voice=21,speed=1.1))] and dialog.result()==1


def test_long_narration_warns_and_can_be_declined(qt_application,monkeypatch):
    install_fakes(monkeypatch,seconds=8);applied=[];asked=[]
    monkeypatch.setattr(QMessageBox,'warning',lambda *a,**k:asked.append(a[2]) or QMessageBox.StandardButton.No)
    dialog=SpeechDialog(5,apply=lambda *a:applied.append(a));dialog.script.setPlainText('Long.');dialog.generate();wait(dialog)
    dialog.use_voiceover();assert asked and 'longer' in asked[0] or 'cut off' in asked[0]
    assert not applied and dialog.result()==0
    monkeypatch.setattr(QMessageBox,'warning',lambda *a,**k:QMessageBox.StandardButton.Yes);dialog.use_voiceover();assert applied


def test_first_use_requires_consent_then_downloads(qt_application,monkeypatch):
    calls=install_fakes(monkeypatch);monkeypatch.setattr(speech,'installed_runtime',lambda *a,**k:None);installs=[]
    monkeypatch.setattr(speech,'install_runtime',lambda **k:installs.append(1) or k['progress'](50))
    dialog=SpeechDialog(5);assert '154 MB' in dialog.status.text();dialog.script.setPlainText('Hello.')
    monkeypatch.setattr(dialog,'confirm_download',lambda:False);dialog.generate()
    assert not installs and not calls and not dialog.working
    monkeypatch.setattr(dialog,'confirm_download',lambda:True);dialog.generate();wait(dialog)
    assert installs and calls and dialog.use_button.isEnabled()


def test_errors_cancel_and_close_protection(qt_application,monkeypatch):
    install_fakes(monkeypatch)
    def failing(*a,**k):raise speech.MissingSpeechRuntime('The installed speech files are damaged or incomplete. Download them again.')
    monkeypatch.setattr(speech,'synthesize',failing)
    dialog=SpeechDialog(5);dialog.script.setPlainText('Hello.');dialog.generate();wait(dialog)
    assert 'damaged' in dialog.status.text() and dialog.needs_download and not dialog.use_button.isEnabled()
    import threading;release=threading.Event()
    def slow(text,voice,speed,output,cancel=None,**k):
        release.wait(5)
        if cancel.is_set():raise RuntimeError('Speech generation cancelled.')
    monkeypatch.setattr(speech,'synthesize',slow);monkeypatch.setattr(dialog,'confirm_download',lambda:True)
    dialog.generate();assert dialog.working
    dialog.reject();assert dialog.result()==0 and dialog.working and 'Cancelling' in dialog.status.text()
    release.set();wait(dialog);assert 'Cancelled' in dialog.status.text() and dialog.audio is None
    dialog.reject()


def make_editor(tmp_path,duration=10):
    session=VideoSession.create(tmp_path,'Speech');session.original='take.mkv';session.duration=duration
    session.asset('take.mkv').write_bytes(b'fixture');session.asset('old.wav').write_bytes(b'old take')
    editor=VideoEditorDialog(session);item=editor.session.timeline[0];item.update(narration='old.wav',narration_origin=0,use_narration=True);editor.save();editor._list(0);return editor


def test_editor_applies_speech_as_new_take_with_undo_save_and_compat(qt_application,tmp_path,monkeypatch):
    install_fakes(monkeypatch,seconds=3);editor=make_editor(tmp_path)
    monkeypatch.setattr(SpeechDialog,'exec',lambda self:(self.script.setPlainText('Welcome.'),self.voice.setCurrentIndex(4),self.generate(),wait(self),self.use_voiceover()))
    editor.open_speech()
    item=editor.current();assert item['narration']!='old.wav' and item['use_narration'] and item['speech']==dict(script='Welcome.',voice=24,speed=1.0)
    assert editor.session.asset(item['narration']).is_file() and editor.session.asset('old.wav').read_bytes()==b'old take'
    reopened=VideoSession.load(editor.session.root);assert reopened.timeline[0]['speech']==item['speech'] and reopened.timeline[0]['narration']==item['narration']
    editor.undo();assert editor.current()['narration']=='old.wav' and 'speech' not in editor.current()
    editor.redo();assert editor.current()['narration']==item['narration']
    editor.close()


def test_cancelled_dialog_leaves_existing_narration_and_cards_have_no_entry(qt_application,tmp_path,monkeypatch):
    install_fakes(monkeypatch);editor=make_editor(tmp_path);before=dict(editor.current())
    monkeypatch.setattr(SpeechDialog,'exec',lambda self:(self.script.setPlainText('x'),self.generate(),wait(self),self.reject()))
    editor.open_speech();assert editor.current()==before and not list(editor.session.root.glob('section-voiceover-*'))
    editor.add_card('Title');assert editor.speech_button.isHidden() or not editor.speech_button.isEnabled()
    editor.close()


def test_failed_apply_removes_unreferenced_asset_and_metadata_survives_split_duplicate(qt_application,tmp_path,monkeypatch):
    editor=make_editor(tmp_path);path=editor.session.root/'x.wav';fake_wave(path,1)
    editor.session.timeline[0]['volume']=9
    try:editor._apply_speech(0,path,dict(script='Hi',voice=21,speed=1))
    except ValueError:pass
    else:raise AssertionError('invalid timeline must be rejected')
    assert not list(editor.session.root.glob('section-voiceover-*'))
    editor.session.timeline[0]['volume']=1
    section=editor.session.timeline[0];section['speech']=dict(script='Hi',voice=21,speed=1)
    left,right=split_section(section,4);assert left['speech']==right['speech']==section['speech']
    editor.save();editor.duplicate();assert editor.session.timeline[1]['speech']==section['speech'];editor.close()
