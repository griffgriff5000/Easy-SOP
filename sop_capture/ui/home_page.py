"""Home workspace: start/open projects and reach the reusable libraries."""
from pathlib import Path
from PySide6.QtCore import Qt,Signal,QSize
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QListWidget,QListWidgetItem
from .components import page_header


class HomePage(QWidget):
    new_requested=Signal();browse_requested=Signal();templates_requested=Signal();annotations_requested=Signal()
    open_requested=Signal(str);remove_requested=Signal(str);continue_requested=Signal()

    def __init__(self):
        super().__init__();box=QVBoxLayout(self);box.setSpacing(14)
        page_header(box,'Welcome to SOP Capture Studio','Start a project, continue your work or manage reusable templates and annotations.')
        cards=QHBoxLayout();box.addLayout(cards)
        for attribute,title,signal in [('new_button','New project\nName, template and folder',self.new_requested),('browse_button','Open project\nBrowse your files',self.browse_requested),('templates_button','Template library\nPreview and manage',self.templates_requested),('annotations_button','Annotation library\nBrowse your designs',self.annotations_requested)]:
            item=QPushButton(title);item.setMinimumHeight(80);item.clicked.connect(lambda checked=False,sig=signal:sig.emit());cards.addWidget(item,1);setattr(self,attribute,item)
        current=QHBoxLayout();self.current_label=QLabel('No project open');self.current_label.setWordWrap(True);current.addWidget(self.current_label,1)
        self.continue_button=QPushButton('Continue editing');self.continue_button.clicked.connect(lambda:self.continue_requested.emit());current.addWidget(self.continue_button);box.addLayout(current)
        heading=QHBoxLayout();heading.addWidget(QLabel('Recent projects'));heading.addStretch();self.counts=QLabel();self.counts.setObjectName('caption');heading.addWidget(self.counts);box.addLayout(heading)
        self.projects=QListWidget();self.projects.setWordWrap(True);self.projects.currentItemChanged.connect(self.selection_changed);self.projects.itemActivated.connect(lambda item:self.open_selected());box.addWidget(self.projects,1)
        self.empty=QLabel('Your recent projects will appear here after you create or open an SOP.');self.empty.setWordWrap(True);box.addWidget(self.empty)
        actions=QHBoxLayout();self.open_button=QPushButton('Open selected project');self.open_button.clicked.connect(self.open_selected);actions.addWidget(self.open_button)
        self.remove_button=QPushButton('Remove from recent');self.remove_button.setToolTip('Remove this shortcut from the list; project files are kept.');self.remove_button.clicked.connect(self.remove_selected);actions.addWidget(self.remove_button);actions.addStretch();box.addLayout(actions)
        self.selection_changed()

    def refresh(self,rows,project,template_count,annotation_count):
        current=self.projects.currentItem();selected=current.data(Qt.ItemDataRole.UserRole) if current else None
        self.projects.clear()
        for row in rows:
            root=Path(row['root']);available=(root/'project.json').is_file() or (root/'project.backup.json').is_file()
            label=f"{row['title']}"+(' — unavailable' if not available else '')
            item=QListWidgetItem(label+'\n'+row.get('template','')+'\n'+str(root));item.setData(Qt.ItemDataRole.UserRole,str(root));item.setData(Qt.ItemDataRole.UserRole+1,available);item.setToolTip(str(root));item.setSizeHint(QSize(100,78));self.projects.addItem(item)
            if str(root)==selected:self.projects.setCurrentItem(item)
        if self.projects.count() and self.projects.currentRow()<0:self.projects.setCurrentRow(0)
        self.empty.setVisible(not rows);self.counts.setText(f'{template_count} templates · {annotation_count} custom annotations')
        self.current_label.setText('Currently open: '+project.title if project else 'No project open');self.continue_button.setVisible(bool(project));self.selection_changed()

    def selection_changed(self,*args):
        item=self.projects.currentItem();self.open_button.setEnabled(bool(item and item.data(Qt.ItemDataRole.UserRole+1)));self.remove_button.setEnabled(item is not None)

    def open_selected(self):
        item=self.projects.currentItem()
        if item and item.data(Qt.ItemDataRole.UserRole+1):self.open_requested.emit(item.data(Qt.ItemDataRole.UserRole))

    def remove_selected(self):
        item=self.projects.currentItem()
        if item:self.remove_requested.emit(item.data(Qt.ItemDataRole.UserRole))
