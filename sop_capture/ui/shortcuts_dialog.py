"""Shortcut editor; changes are staged until Apply."""
import json
import uuid
from copy import deepcopy
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QKeySequenceEdit, QPushButton, QListWidget,
    QComboBox, QDialogButtonBox, QMessageBox, QFileDialog, QTabWidget, QWidget)
from .components import page_header,menu_button
from ..shortcuts import ACTIONS, default_profile, validate_profile
from ..storage import atomic_bytes


def key_editor(text=''):
    editor = QKeySequenceEdit(QKeySequence(text))
    editor.setMaximumSequenceLength(1)
    editor.setClearButtonEnabled(True)
    return editor


class SequenceDialog(QDialog):
    def __init__(self, sequence=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Edit action sequence')
        self.resize(520, 520)
        self.identity = sequence['id'] if sequence else uuid.uuid4().hex
        box = QVBoxLayout(self)
        self.name = QLineEdit(sequence['name'] if sequence else '')
        self.name.setMaxLength(100)
        self.name.setPlaceholderText('Sequence name')
        box.addWidget(self.name)
        self.key = key_editor(sequence.get('shortcut','') if sequence else '')
        box.addWidget(QLabel('Shortcut (optional)'))
        box.addWidget(self.key)
        box.addWidget(QLabel('Actions run from top to bottom. Up to 20 actions.'))
        self.steps = QListWidget()
        for action in sequence['actions'] if sequence else []: self.add_action(action)
        box.addWidget(self.steps)
        self.action = QComboBox()
        for action, row in ACTIONS.items():
            if row[2]: self.action.addItem(row[0], action)
        box.addWidget(self.action)
        row = QHBoxLayout()
        for title, callback in [('Add action', lambda: self.add_action(self.action.currentData())), ('Remove', self.remove), ('Up', lambda: self.move(-1)), ('Down', lambda: self.move(1))]:
            button=QPushButton(title);button.clicked.connect(callback);row.addWidget(button)
        box.addLayout(row)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.finish);buttons.rejected.connect(self.reject);box.addWidget(buttons)

    def add_action(self, action):
        if self.steps.count() >= 20: return
        from PySide6.QtWidgets import QListWidgetItem
        item=QListWidgetItem(ACTIONS[action][0]);item.setData(Qt.ItemDataRole.UserRole,action)
        self.steps.addItem(item);self.steps.setCurrentItem(item)

    def remove(self):
        self.steps.takeItem(self.steps.currentRow())

    def move(self, delta):
        row=self.steps.currentRow();target=row+delta
        if 0 <= row < self.steps.count() and 0 <= target < self.steps.count():
            self.steps.insertItem(target,self.steps.takeItem(row));self.steps.setCurrentRow(target)

    def value(self):
        return {'id':self.identity,'name':self.name.text().strip(), 'shortcut':self.key.keySequence().toString(QKeySequence.SequenceFormat.PortableText),
                'actions':[self.steps.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.steps.count())]}

    def finish(self):
        if not self.name.text().strip() or not self.steps.count():
            QMessageBox.warning(self,'Incomplete sequence','Enter a name and add at least one action.');return
        self.accept()


class ShortcutsDialog(QDialog):
    def __init__(self, profile, capture_key, apply_profile, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Customise shortcuts')
        self.resize(780, 650)
        self.capture_key, self.apply_profile = capture_key, apply_profile
        self.profile=deepcopy(profile)
        box=QVBoxLayout(self)
        page_header(box,'Keyboard shortcuts','Assign keys to app actions and create reusable action sequences.')
        note=QLabel('Shortcuts work while SOP Capture Studio is active. Clear a key to disable it.\nManual capture remains a global shortcut in Settings. Sequences run editor actions in order.')
        note.setWordWrap(True);box.addWidget(note)
        tabs=QTabWidget();box.addWidget(tabs)
        actions=QWidget();actions.setObjectName("scrollPage");layout=QVBoxLayout(actions)
        self.search=QLineEdit();self.search.setPlaceholderText('Find an action...');layout.addWidget(self.search)
        self.table=QTableWidget(len(ACTIONS),2);self.table.setHorizontalHeaderLabels(['Action','Shortcut']);self.table.verticalHeader().hide();self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.horizontalHeader().setStretchLastSection(True);self.table.setColumnWidth(0,330);layout.addWidget(self.table)
        self.search.textChanged.connect(self.filter)
        tabs.addTab(actions,'App actions')
        sequences=QWidget();sequences.setObjectName("scrollPage");layout=QVBoxLayout(sequences)
        self.sequences=QListWidget();layout.addWidget(self.sequences)
        row=QHBoxLayout()
        for title,callback in [('New sequence',lambda:self.edit_sequence(True)),('Edit sequence',lambda:self.edit_sequence(False)),('Delete sequence',self.delete_sequence),('Run selected',self.run_selected)]:
            b=QPushButton(title);b.clicked.connect(callback);row.addWidget(b)
        layout.addLayout(row);tabs.addTab(sequences,'Action sequences')
        self.sequences.itemDoubleClicked.connect(lambda _:self.edit_sequence(False))
        row=QHBoxLayout()
        row.addWidget(menu_button('Profiles',[('Import profile...',self.import_profile),('Export profile...',self.export_profile),('Restore defaults',self.reset)]));row.addStretch()
        box.addLayout(row)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Apply|QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply)
        buttons.rejected.connect(self.reject);box.addWidget(buttons)
        self.populate()

    def populate(self):
        self.editors={}
        for row,(action,details) in enumerate(ACTIONS.items()):
            item=QTableWidgetItem(details[0]);item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable);self.table.setItem(row,0,item)
            editor=key_editor(self.profile['bindings'][action]);self.editors[action]=editor;self.table.setCellWidget(row,1,editor)
        self.refresh_sequences();self.filter(self.search.text())

    def filter(self,text):
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row,text.lower() not in self.table.item(row,0).text().lower())

    def refresh_sequences(self):
        self.sequences.clear()
        for sequence in self.profile['sequences']:
            self.sequences.addItem(sequence['name']+'  '+(sequence['shortcut'] or '(no shortcut)'))

    def collect(self):
        profile=deepcopy(self.profile)
        profile['bindings']={action:editor.keySequence().toString(QKeySequence.SequenceFormat.PortableText) for action,editor in self.editors.items()}
        return validate_profile(profile,self.capture_key())

    def edit_sequence(self,new):
        row=self.sequences.currentRow()
        if not new and row < 0: return
        editor=SequenceDialog(None if new else self.profile['sequences'][row],self)
        if editor.exec():
            if new: self.profile['sequences'].append(editor.value())
            else: self.profile['sequences'][row]=editor.value()
            self.refresh_sequences()

    def delete_sequence(self):
        row=self.sequences.currentRow()
        if row>=0: self.profile['sequences'].pop(row);self.refresh_sequences()

    def apply(self):
        try:
            profile=self.collect();self.apply_profile(profile);self.profile=profile
            return True
        except (ValueError,OSError) as exc:
            QMessageBox.warning(self,'Shortcut profile',str(exc));return False

    def run_selected(self):
        row=self.sequences.currentRow()
        if row>=0 and self.apply():
            identity=self.profile['sequences'][row]['id'];self.accept()
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0,lambda:self.parent().run_shortcut_sequence(identity))

    def reset(self):
        if QMessageBox.question(self,'Restore defaults','Replace all bindings and remove custom sequences?') == QMessageBox.StandardButton.Yes:
            self.profile=default_profile();self.populate()

    def import_profile(self):
        path,_=QFileDialog.getOpenFileName(self,'Import shortcut profile','','JSON profile (*.json)')
        if not path:return
        try:
            if Path(path).stat().st_size>1024*1024:raise ValueError('Profile is too large.')
            profile=validate_profile(json.loads(Path(path).read_text(encoding='utf-8-sig')),self.capture_key())
            self.profile=profile;self.populate()
        except (ValueError,OSError,TypeError,RecursionError) as exc: QMessageBox.warning(self,'Import failed',str(exc))

    def export_profile(self):
        try:profile=self.collect()
        except ValueError as exc: QMessageBox.warning(self,'Invalid shortcuts',str(exc));return
        path,_=QFileDialog.getSaveFileName(self,'Export shortcut profile','','JSON profile (*.json)')
        if not path:return
        output=Path(path)
        if output.suffix.lower()!='.json':output=output.with_suffix('.json')
        if output.exists() and QMessageBox.question(self,'Replace profile?',f'Replace {output.name}?') != QMessageBox.StandardButton.Yes:return
        try:atomic_bytes(output,json.dumps(profile,indent=2).encode('utf-8'))
        except OSError as exc:QMessageBox.warning(self,'Export failed',str(exc))
