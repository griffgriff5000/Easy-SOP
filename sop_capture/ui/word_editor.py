"""Desktop Word hosted as a native child window, with project snapshot saves."""
from hashlib import sha256
from pathlib import Path
import tempfile

from ..word_session import WordSession

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QWindow
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton




class WordEditor(QWidget):
    problem = Signal(str)
    open_requested = Signal()
    rebuild_requested = Signal()

    def __init__(self, persist, parent=None):
        super().__init__(parent)
        self.persist = persist
        self.session = self.foreign = self.container = self.temporary = None
        self.path = None
        self.bound_document_ref = None
        self.source_key = ''
        self.saved_hash = None
        layout = QVBoxLayout(self);layout.setContentsMargins(0, 0, 0, 0)
        toolbar = QHBoxLayout();layout.addLayout(toolbar)
        self.open_button = QPushButton('Open document editor');toolbar.addWidget(self.open_button)
        self.open_button.clicked.connect(self.open_requested)
        self.edit_buttons = []
        for label, command in [('Save', None), ('Undo', 'Undo'), ('Redo', 'Redo'),
                               ('B', 'Bold'), ('I', 'Italic'), ('U', 'Underline')]:
            item = QPushButton(label);toolbar.addWidget(item);self.edit_buttons.append(item)
            item.clicked.connect(lambda checked=False, name=command:self._command(name))
        toolbar.addStretch()
        self.rebuild_button = QPushButton('Rebuild from captured steps');toolbar.addWidget(self.rebuild_button)
        self.rebuild_button.clicked.connect(self.rebuild_requested)
        self.status = QLabel('Click and type directly on the document. Desktop Microsoft Word is required.');self.status.setWordWrap(True);layout.addWidget(self.status)
        self.host = QWidget();self.host_layout = QVBoxLayout(self.host);self.host_layout.setContentsMargins(0,0,0,0);layout.addWidget(self.host,1)
        self.timer = QTimer(self);self.timer.setInterval(5000);self.timer.timeout.connect(self._autosave)
        self._controls()

    def _controls(self):
        for item in self.edit_buttons:item.setEnabled(self.session is not None)
        self.open_button.setVisible(self.session is None)

    def open_document(self, path, temporary, reference, source_key):
        if self.temporary and self.session is None:self.close_document(save=False)
        self.path = Path(path);self.temporary = temporary
        self.bound_document_ref = reference;self.source_key = source_key
        self.saved_hash = sha256(self.path.read_bytes()).digest() if reference else None
        try:
            self.session = WordSession(self.path)
            self.foreign = QWindow.fromWinId(self.session.hwnd)
            if self.foreign is None:raise RuntimeError('Word could not be embedded in the document pane.')
            self.container = QWidget.createWindowContainer(self.foreign, self.host)
            self.host_layout.addWidget(self.container)
            self.save_document()
            self.timer.start();self._controls()
            QTimer.singleShot(250,self._refresh_native)
            self.status.setText('Edit directly on the pages. Changes save to this project every five seconds. '
                                'Use Word shortcuts or right-click for more editing options.')
        except Exception:
            # Keep the working file if opening or initial persistence failed.
            self._controls()
            raise

    def _refresh_native(self):
        if self.session is not None and self.isVisible():
            try:
                self.session.document.Activate()
                self.session.word.ScreenRefresh()
            except Exception:
                # A Word modal dialog can temporarily reject repaint requests.
                # Saving reports actionable errors separately.
                pass

    def showEvent(self,event):
        super().showEvent(event)
        QTimer.singleShot(250,self._refresh_native)

    def save_document(self):
        if self.session is None:return
        still_open = self.session.save()
        # Native Save As is available in Word's ribbon. Follow its actual saved
        # document rather than silently snapshotting the old working filename.
        path = self.session.saved_path if hasattr(self.session,'saved_path') else self.path
        data = Path(path).read_bytes();digest = sha256(data).digest()
        if digest != self.saved_hash:
            reference = self.persist(data, self.source_key)
            self.bound_document_ref = reference
            self.saved_hash = digest
        if still_open is False:
            self.close_document(save=False)
            self.status.setText('Word closed this document. The last saved version is retained. Click Open document editor to continue.')

    def _autosave(self):
        try:self.save_document()
        except Exception as exc:
            self.status.setText(f'{exc} Working copy: {self.path}')
            self.problem.emit(str(exc))

    def _command(self, name):
        try:
            if name:self.session.command(name)
            self.save_document()
        except Exception as exc:self.problem.emit(str(exc))

    def close_document(self, save=True):
        if save:self.save_document()
        self.timer.stop()
        if self.session:self.session.close()
        self.session = None
        if self.container:
            self.host_layout.removeWidget(self.container);self.container.deleteLater()
        self.container = self.foreign = None
        if self.temporary:self.temporary.cleanup()
        self.temporary = None;self.path = None;self.bound_document_ref = None
        self._controls()
