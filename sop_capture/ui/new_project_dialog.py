"""Project name, reusable template and parent directory in one dialog."""
from pathlib import Path
import re
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QFormLayout,QLineEdit,QComboBox,QLabel,QHBoxLayout,QPushButton,QDialogButtonBox,QFileDialog


def project_folder_name(title):
    safe=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',title).strip(' .')[:100] or 'Procedure'
    return 'SOP - '+safe


class NewProjectDialog(QDialog):
    def __init__(self,profiles,location,current='standard',parent=None):
        super().__init__(parent);self.setWindowTitle('New project');self.resize(620,340)
        box=QVBoxLayout(self);form=QFormLayout();form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows);box.addLayout(form)
        self.title=QLineEdit();self.title.setMaxLength(200);self.title.setPlaceholderText('Name this SOP');form.addRow('Project name',self.title)
        self.template=QComboBox()
        for profile in profiles:self.template.addItem(profile['name'],profile['id'])
        self.template.setCurrentIndex(max(0,self.template.findData(current)));form.addRow('Saved template',self.template)
        row=QHBoxLayout();self.location=QLineEdit(location);row.addWidget(self.location,1)
        browse=QPushButton('Browse…');browse.clicked.connect(self.browse);row.addWidget(browse);form.addRow('Parent folder',row)
        self.folder_preview=QLabel();self.folder_preview.setWordWrap(True);self.folder_preview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);form.addRow('New project folder',self.folder_preview)
        note=QLabel('A separate folder is created for this project. The saved template stays in your library; this project gets its own copy.');note.setWordWrap(True);box.addWidget(note)
        self.status=QLabel();self.status.setWordWrap(True);box.addWidget(self.status)
        self.buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Create project')
        self.buttons.accepted.connect(self.accept);self.buttons.rejected.connect(self.reject);box.addWidget(self.buttons)
        self.title.textChanged.connect(self.refresh);self.location.textChanged.connect(self.refresh);self.refresh()

    def values(self):return self.title.text().strip(),self.template.currentData(),self.location.text().strip()

    def refresh(self):
        title,identity,location=self.values();path=Path(location).expanduser() if location else None
        valid=bool(title and identity and path and path.is_absolute() and not (path.exists() and not path.is_dir()))
        if path:
            base=project_folder_name(title);candidate=path/base;suffix=2
            while candidate.exists():candidate=path/f'{base} ({suffix})';suffix+=1
            self.folder_preview.setText(str(candidate))
        else:self.folder_preview.setText('Choose a parent folder')
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(valid)
        self.status.setText('' if valid else 'Enter a project name and choose an absolute parent folder.')

    def browse(self):
        path=QFileDialog.getExistingDirectory(self,'Choose parent folder',self.location.text())
        if path:self.location.setText(path)

    def accept(self):
        self.refresh()
        if self.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled():super().accept()
