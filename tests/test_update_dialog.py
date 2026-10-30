import time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from sop_capture.ui.update_dialog import UpdateDialog


def wait(predicate):
    deadline=time.monotonic()+3
    while not predicate() and time.monotonic()<deadline:QApplication.processEvents();QTest.qWait(10)
    assert predicate()


def test_check_download_and_install_are_separate_confirmed_actions(tmp_path):
    release={'version':'0.3.0','notes':'New features','asset':{'size':100}}
    calls=[]
    def download(info,job,**kwargs):calls.append('download');kwargs['progress'](100,100);return tmp_path/'staged'
    dialog=UpdateDialog(None,current='0.2.0',checker=lambda:release,downloader=download,installer=lambda path,version:calls.append(('install',version)) or True,can_install=True,cache_root=tmp_path)
    wait(lambda:dialog.download_button.isEnabled());assert not calls and not dialog.install_button.isEnabled()
    dialog.download();wait(lambda:dialog.install_button.isEnabled());assert calls==['download']
    dialog.install();assert calls==['download',('install','0.3.0')]
    dialog.close();dialog.deleteLater()


def test_no_downgrade_and_source_runs_do_not_install(tmp_path):
    dialog=UpdateDialog(None,current='0.2.0',checker=lambda:{'version':'0.1.0','notes':''},cache_root=tmp_path,can_install=False)
    wait(lambda:dialog.check_button.isEnabled());assert not dialog.download_button.isEnabled() and not dialog.install_button.isEnabled()
    dialog.close();dialog.deleteLater()


def test_closed_check_can_be_reopened_without_stale_operation(tmp_path):
    import threading
    event=threading.Event()
    def check():event.wait(1);return {'version':'0.1.0','notes':''}
    dialog=UpdateDialog(checker=check,cache_root=tmp_path);QApplication.processEvents();assert dialog.operation=='check'
    dialog.close();assert dialog.operation is None
    dialog.checker=lambda:{'version':'0.1.0','notes':''};dialog.check();wait(lambda:dialog.check_button.isEnabled());event.set()
    dialog.close();dialog.deleteLater()


def test_main_save_failure_cancels_helper_before_any_install(tmp_path,monkeypatch):
    import sys,json,subprocess
    from PySide6.QtWidgets import QMessageBox
    from sop_capture.ui.main_window import MainWindow
    import sop_capture.update_install as install
    window=MainWindow();plan=tmp_path/'update-plan.json';plan.write_text('{}');runner=tmp_path/'runner.exe';calls=[]
    monkeypatch.setattr(sys,'frozen',True,raising=False);monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(install,'prepare_handoff',lambda *a:(plan,runner,'a'*32));monkeypatch.setattr(window,'close',lambda:False)
    class Helper:
        def wait(self,timeout):calls.append(json.loads((tmp_path/'cancelled.json').read_text()));return 0
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**k:Helper())
    assert window.install_update(tmp_path,'0.3.0') is False and calls==[{'token':'a'*32}]
    assert not (tmp_path/'confirmed.json').exists()
    monkeypatch.undo();window.close();window.deleteLater()
