"""User-driven, asynchronous release checks and downloads; installation is separate."""
from pathlib import Path
import sys
import threading
import uuid
from PySide6.QtCore import QObject,Signal,QTimer,QStandardPaths,QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QTextBrowser,QPushButton,QProgressBar
from .. import __version__
from ..updates import check_release,prepare_update,is_newer,Cancelled,REPO


class UpdateSignals(QObject):
    finished=Signal(int,object,object)
    progress=Signal(int,int,int)


class UpdateDialog(QDialog):
    def __init__(self,parent=None,*,current=__version__,checker=check_release,downloader=prepare_update,installer=None,can_install=None,cache_root=None):
        super().__init__(parent);self.setWindowTitle('SOP Capture Studio updates');self.resize(650,520)
        self.current=current;self.checker=checker;self.downloader=downloader;self.installer=installer;self.release=None;self.staged=None;self.operation=None;self.generation=0;self.cancel_event=threading.Event()
        installed=Path(sys.executable).resolve().parent
        self.can_install=bool(getattr(sys,'frozen',False) and (installed/'RELEASE.json').is_file() and (installed/'SOPCaptureUpdater.exe').is_file()) if can_install is None else can_install
        self.cache_root=Path(cache_root) if cache_root else Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))/'updates'
        self.signals=UpdateSignals(self);self.signals.finished.connect(self._finished);self.signals.progress.connect(self.progressed)
        box=QVBoxLayout(self);heading=QLabel('Application updates');heading.setObjectName('heading');box.addWidget(heading)
        self.versions=QLabel('Installed version: '+current);box.addWidget(self.versions)
        self.status=QLabel('Checking the public GitHub release…');self.status.setWordWrap(True);box.addWidget(self.status)
        self.notes=QTextBrowser();self.notes.setOpenExternalLinks(False);box.addWidget(self.notes,1)
        self.progress=QProgressBar();self.progress.setRange(0,100);self.progress.hide();box.addWidget(self.progress)
        hint=QLabel('Updates replace the app folder after saving and closing. Projects, templates, annotations and settings stay separate. The previous app folder is retained.');hint.setWordWrap(True);hint.setObjectName('caption');box.addWidget(hint)
        if not self.can_install:
            note=QLabel('Automatic installation requires the extracted Windows release. Source/development runs can check and download only.');note.setWordWrap(True);box.addWidget(note)
        buttons=QHBoxLayout();box.addLayout(buttons)
        for attr,title,callback in [('check_button','Check again',self.check),('download_button','Download update',self.download),('install_button','Install and restart',self.install),('cancel_button','Cancel download',self.cancel),('folder_button','Open download folder',self.open_folder)]:
            item=QPushButton(title);item.clicked.connect(callback);buttons.addWidget(item);setattr(self,attr,item)
        self.download_button.setEnabled(False);self.install_button.setEnabled(False);self.cancel_button.setEnabled(False);self.folder_button.setEnabled(False);self.check_button.setEnabled(False)
        footer=QHBoxLayout();buttons.removeWidget(self.folder_button);footer.addWidget(self.folder_button)
        releases=QPushButton('View GitHub releases');releases.clicked.connect(lambda:QDesktopServices.openUrl(QUrl(REPO+'/releases/latest')));footer.addWidget(releases);footer.addStretch();close=QPushButton('Close');close.clicked.connect(self.close);footer.addWidget(close);box.addLayout(footer)
        QTimer.singleShot(0,self.check)

    def run(self,operation,kind):
        self.generation+=1;generation=self.generation;self.operation=kind;self.cancel_event=threading.Event();self.check_button.setEnabled(False);self.download_button.setEnabled(False);self.install_button.setEnabled(False);self.cancel_button.setEnabled(kind=='download')
        event=self.cancel_event
        def work():
            try:value,error=operation(generation,event),None
            except Exception as exc:value,error=None,exc
            try:self.signals.finished.emit(generation,value,error)
            except RuntimeError:pass
        threading.Thread(target=work,daemon=True).start()

    def check(self):
        if self.operation:return
        self.release=None;self.staged=None;self.status.setText('Checking the latest stable GitHub release…');self.run(lambda generation,event:self.checker(),'check')

    def download(self):
        if self.operation or not self.release:return
        release=self.release;job=self.cache_root/uuid.uuid4().hex;self.status.setText('Downloading and verifying the update…');self.progress.setValue(0);self.progress.show()
        def operation(generation,event):
            def progress(done,total):
                try:self.signals.progress.emit(generation,done,total)
                except RuntimeError:event.set()
            return self.downloader(release,job,cancel=event.is_set,progress=progress)
        self.run(operation,'download')

    def progressed(self,generation,done,total):
        if generation==self.generation:self.progress.setValue(round(100*done/total) if total else 0)

    def _finished(self,generation,value,error):
        if generation!=self.generation:return
        kind=self.operation;self.operation=None;self.check_button.setEnabled(True);self.cancel_button.setEnabled(False)
        if error:
            self.status.setText('Download cancelled.' if isinstance(error,Cancelled) else 'Could not complete update: '+str(error));self.download_button.setEnabled(bool(self.release));return
        if kind=='check':
            self.release=value;newer=is_newer(value['version'],self.current);self.versions.setText('Installed: '+self.current+'    Latest stable release: '+value['version']);self.notes.setPlainText(value.get('notes',''));self.download_button.setEnabled(newer);self.status.setText('A new version is available. Download it when you are ready.' if newer else 'No newer stable release is available for this version.')
        else:
            self.staged=Path(value);self.install_button.setEnabled(self.can_install);self.folder_button.setEnabled(True);self.status.setText('Download verified. Install and restart when your work is ready to save.');self.progress.setValue(100)

    def cancel(self):
        self.cancel_event.set();self.cancel_button.setEnabled(False);self.status.setText('Cancelling download…')

    def install(self):
        if self.operation or not self.staged or not self.can_install or not self.installer:return
        self.install_button.setEnabled(False)
        try:
            if not self.installer(self.staged,self.release['version']):self.install_button.setEnabled(True)
        except Exception as exc:self.status.setText('Installation did not start: '+str(exc));self.install_button.setEnabled(True)

    def open_folder(self):
        if self.staged:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.staged.parents[1])))

    def closeEvent(self,event):
        self.cancel_event.set();self.generation+=1;self.operation=None;event.accept()
