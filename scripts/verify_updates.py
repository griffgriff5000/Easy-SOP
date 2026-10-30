"""Render the updater states with fake metadata; never installs or downloads."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from sop_capture.ui.update_dialog import UpdateDialog
from sop_capture.ui.theme import stylesheet


def main():
    app=QApplication([]);out=Path('.superpowers/updates');out.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory() as temp:
        for dark in (False,True):
            theme='dark' if dark else 'light'
            dialog=UpdateDialog(current='0.2.0',checker=lambda:{'version':'0.3.0','notes':'Example release\n\nImproved document review and screenshot annotation.\nSaved projects and personal workspaces remain available.','asset':{'size':85000000}},downloader=lambda info,job,**kw:Path(temp)/'job/staged/SOPCaptureStudio',installer=lambda path,version:False,can_install=True,cache_root=temp)
            dialog.setStyleSheet(stylesheet(dark));dialog.show();deadline=time.monotonic()+3
            while not dialog.download_button.isEnabled() and time.monotonic()<deadline:app.processEvents();QTest.qWait(10)
            dialog.grab().save(str(out/f'available-{theme}.png'));dialog.download();deadline=time.monotonic()+3
            while not dialog.install_button.isEnabled() and time.monotonic()<deadline:app.processEvents();QTest.qWait(10)
            dialog.grab().save(str(out/f'ready-{theme}.png'));dialog.close()
    print(out.resolve())

if __name__=='__main__':main()
