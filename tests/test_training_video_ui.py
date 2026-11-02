from sop_capture.ui.main_window import MainWindow


def test_training_workspace_is_independent_and_does_not_open_microphone(qt_application):
    window=MainWindow()
    assert window.video_page.video is None
    assert window.video_page.engine is None
    assert not window.video_page.busy
    assert window.workspace_keys[8]=='video'
    assert 'video' in window.workspaces.hosts
    assert window.close()


def test_video_readiness_compares_windows_file_urls_as_paths(qt_application,tmp_path):
    from types import SimpleNamespace
    from PySide6.QtCore import QUrl
    from PySide6.QtMultimedia import QMediaPlayer
    from sop_capture.training_video import VideoSession
    window=MainWindow();page=window.video_page;page._ensure_media()
    video=VideoSession.create(tmp_path,'Ready');video.original='original.mkv';video.asset(video.original).write_bytes(b'fixture')
    page.video=video;real=page.player
    page.player=SimpleNamespace(source=lambda:QUrl.fromLocalFile(str(video.asset(video.original))),hasVideo=lambda:True,duration=lambda:10000,mediaStatus=lambda:QMediaPlayer.MediaStatus.LoadedMedia)
    try:
        page._update_media_ready();assert page.narrate_button.isEnabled()
    finally:page.player=real
    assert window.close()


def test_close_and_update_are_blocked_while_video_is_recording(qt_application,monkeypatch,tmp_path):
    import sys
    from types import SimpleNamespace
    import pytest
    window=MainWindow();window.video_page.engine=SimpleNamespace(busy=True,state='recording')
    assert not window.close()
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    with pytest.raises(ValueError,match='Finish recording'):window.install_update(tmp_path,'9.0.0')
    window.video_page.engine.busy=False;window.video_page.engine.state='idle'
    assert window.close()


def test_invalid_trim_is_not_exported_using_previous_values(qt_application,monkeypatch,tmp_path):
    from types import SimpleNamespace
    from PySide6.QtWidgets import QFileDialog
    from sop_capture.training_video import VideoSession
    window=MainWindow();page=window.video_page;page.set_session(VideoSession.create(tmp_path,'Trim check'))
    page.video.original='recording.mkv';page.video.duration=10
    page.engine=SimpleNamespace(busy=False,state='idle',mode=None)
    page.start.setValue(8);page.end.setValue(2)
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(_ for _ in ()).throw(AssertionError('Invalid edit must not reach output dialog')))
    page.export()
    assert 'after' in page.status.text()
    assert window.close()


def test_narration_waits_for_playable_video_and_stops_on_playback_error(qt_application,monkeypatch,tmp_path):
    from PySide6.QtMultimedia import QMediaPlayer
    from sop_capture.training_video import VideoSession
    window=MainWindow();page=window.video_page;page._ensure_media()
    video=VideoSession.create(tmp_path,'Narration readiness');page.set_session(video)
    video.original='missing.mkv';video.duration=10;video.narration='previous.wav'
    calls=[];monkeypatch.setattr(page.engine,'start_audio',lambda *args:calls.append('microphone started'))
    page._refresh()
    assert not page.narrate_button.isEnabled()
    page.record_narration();assert not calls
    page.engine.mode='narration';page.engine.state='recording'
    def stop():calls.append('stopped');page.engine.state='idle';page.engine.mode=None
    monkeypatch.setattr(page.engine,'stop',stop)
    page.player.errorOccurred.emit(QMediaPlayer.Error.ResourceError,'Video playback failed')
    assert calls==['stopped']
    page._recorded('narration',tmp_path/'unusable.wav',1000,None)
    assert page.video.narration=='previous.wav'
    assert window.close()


def test_export_suffix_change_requires_overwrite_confirmation(qt_application,monkeypatch,tmp_path):
    from PySide6.QtWidgets import QFileDialog,QMessageBox
    from sop_capture.training_video import VideoSession
    window=MainWindow();page=window.video_page;page._ensure_media()
    video=VideoSession.create(tmp_path,'Output confirmation');page.set_session(video)
    video.original='original.mkv';video.duration=10;video.asset(video.original).write_bytes(b'fixture')
    output=tmp_path/'existing.mp4';output.write_bytes(b'old export');calls=[];questions=[]
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(tmp_path/'existing.mkv'),''))
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:questions.append(True) or QMessageBox.StandardButton.No)
    monkeypatch.setattr(page.exporter,'start',lambda *a:calls.append(a))
    page.export()
    assert questions and not calls
    assert output.read_bytes()==b'old export'
    assert window.close()


def test_export_tool_download_requires_consent_and_can_be_cancelled(qt_application,monkeypatch,tmp_path):
    import time
    from PySide6.QtWidgets import QMessageBox,QApplication
    from sop_capture import media_runtime
    window=MainWindow();page=window.video_page
    calls=[]
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Cancel)
    monkeypatch.setattr(media_runtime,'install_runtime',lambda **kw:calls.append('download'))
    page._download_tool(tmp_path/'out.mp4')
    assert not calls and not page.busy
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes)
    def download(**kw):
        calls.append('download');kw['cancel'].wait(3)
        raise RuntimeError('Video tool download cancelled.')
    monkeypatch.setattr(media_runtime,'install_runtime',download)
    page._download_tool(tmp_path/'out.mp4')
    assert page.busy and page.cancel_button.isEnabled() and not window.close()
    page.cancel_export()
    deadline=time.monotonic()+5
    while page.busy and time.monotonic()<deadline:QApplication.processEvents();time.sleep(.01)
    assert calls==['download'] and not page.busy and 'cancelled' in page.status.text()
    assert window.close()
