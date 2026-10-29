"""Application-wide design browsing without opening a project or screenshot."""
from pathlib import Path
from copy import deepcopy
from PySide6.QtCore import Qt,Signal,QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QListWidget,QListWidgetItem,QSplitter,QFileDialog,QInputDialog,QMessageBox,QSizePolicy
from ..designs import render_design,load_pack,save_pack,import_artwork,new_design
from .annotation_studio import AnnotationStudio
from .canvas import image_pixmap
from .components import page_header,menu_button


class AnnotationLibraryPage(QWidget):
    changed=Signal();use_requested=Signal(str)

    def __init__(self,library):
        super().__init__();self.library=library;self.can_use=False;self.preview_pixmap=None
        box=QVBoxLayout(self);box.setSpacing(12);page_header(box,'Annotation library','Save designs once and reuse them across projects. Placed copies stay independent.')
        row=QHBoxLayout();self.new_button=QPushButton('New design');self.new_button.clicked.connect(lambda:self.edit_design(new=True));row.addWidget(self.new_button)
        self.edit_button=QPushButton('Edit in studio');self.edit_button.clicked.connect(self.edit_design);row.addWidget(self.edit_button)
        row.addWidget(menu_button('Import',[('Editable annotation pack…',self.import_pack),('Artwork…',self.import_art)]))
        self.duplicate_button=QPushButton('Duplicate');self.duplicate_button.clicked.connect(self.duplicate);row.addWidget(self.duplicate_button)
        self.export_button=QPushButton('Export pack');self.export_button.clicked.connect(self.export);row.addWidget(self.export_button)
        self.delete_button=QPushButton('Delete saved');self.delete_button.clicked.connect(self.delete);row.addWidget(self.delete_button);row.addStretch();box.addLayout(row)
        splitter=QSplitter();box.addWidget(splitter,1)
        self.entries=QListWidget();self.entries.setIconSize(QSize(96,64));self.entries.setMinimumWidth(210);self.entries.setWordWrap(True);self.entries.currentItemChanged.connect(self.selection_changed);self.entries.itemDoubleClicked.connect(lambda item:self.edit_design());splitter.addWidget(self.entries)
        details=QWidget();detail=QVBoxLayout(details);self.name=QLabel('No saved designs');self.name.setWordWrap(True);detail.addWidget(self.name)
        self.preview=QLabel('Create a design in Annotation Studio or import artwork.');self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter);self.preview.setWordWrap(True);self.preview.setMinimumSize(280,230);self.preview.setStyleSheet('background:#e4ebf2; border:1px solid #b8c8d5; border-radius:6px;');detail.addWidget(self.preview,1)
        self.preview.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Ignored)
        self.use_button=QPushButton('Use on current screenshot');self.use_button.clicked.connect(self.use_selected);detail.addWidget(self.use_button)
        hint=QLabel('Library edits do not alter designs already placed in SOPs. Open a screenshot step to use a design.');hint.setWordWrap(True);hint.setObjectName('caption');detail.addWidget(hint)
        splitter.addWidget(details);splitter.setSizes([250,700]);splitter.setStretchFactor(1,1);self.refresh()

    def current_identity(self):
        item=self.entries.currentItem();return item.data(Qt.ItemDataRole.UserRole) if item else None

    def refresh(self,selected=None):
        selected=selected or self.current_identity();self.entries.clear()
        for identity,name in self.library.entries():
            try:
                _,design=self.library.load(identity);width,height=design['size'];ratio=min(96/width,64/height)
                icon=QIcon(image_pixmap(render_design(design,(max(1,round(width*ratio)),max(1,round(height*ratio))))))
                item=QListWidgetItem(icon,name);item.setData(Qt.ItemDataRole.UserRole,identity);item.setToolTip(name);item.setSizeHint(QSize(180,78));self.entries.addItem(item)
                if identity==selected:self.entries.setCurrentItem(item)
            except (ValueError,OSError):continue
        if self.entries.count() and self.entries.currentRow()<0:self.entries.setCurrentRow(0)
        self.selection_changed()

    def set_can_use(self,value):
        self.can_use=value;self.use_button.setEnabled(value and self.current_identity() is not None)

    def selection_changed(self,*args):
        identity=self.current_identity()
        for button in (self.edit_button,self.duplicate_button,self.export_button,self.delete_button):button.setEnabled(identity is not None)
        self.set_can_use(self.can_use);self.preview_pixmap=None
        if not identity:
            self.name.setText('No saved designs');self.preview.clear();self.preview.setText('Create a design in Annotation Studio or import artwork.');return
        try:
            name,design=self.library.load(identity);self.name.setText(name+f" · {design['size'][0]} × {design['size'][1]} · {len(design['layers'])} layers")
            width,height=design['size'];ratio=min(700/width,500/height,1)
            image=render_design(design,(max(1,round(width*ratio)),max(1,round(height*ratio))))
            from PIL import Image
            paper=Image.new('RGBA',image.size,'white');paper.alpha_composite(image);self.preview_pixmap=image_pixmap(paper);self.resize_preview()
        except (ValueError,OSError) as exc:self.preview.setText(str(exc))

    def resize_preview(self):
        if self.preview_pixmap:self.preview.setPixmap(self.preview_pixmap.scaled(self.preview.size()-QSize(20,20),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self,event):
        super().resizeEvent(event);self.resize_preview()

    def edit_design(self,checked=False,new=False):
        try:
            identity=None if new else self.current_identity()
            name,design=self.library.load(identity) if identity else ('Untitled design',None)
            studio=AnnotationStudio(self.library,design,False,self)
            if identity:studio.replace_document(design,name,identity)
            studio.exec();self.refresh(studio.identity or identity);self.changed.emit();studio.deleteLater()
        except (ValueError,OSError) as exc:self.error(exc)

    def duplicate(self):
        identity=self.current_identity()
        if not identity:return
        try:
            name,design=self.library.load(identity);name,ok=QInputDialog.getText(self,'Duplicate annotation','New library name:',text=(name+' copy')[:120])
            if ok:self.refresh(self.library.save(name,deepcopy(design)));self.changed.emit()
        except (ValueError,OSError) as exc:self.error(exc)

    def import_pack(self):
        path,_=QFileDialog.getOpenFileName(self,'Import editable annotation','','Annotation packs (*.sopannotation)')
        if not path:return
        try:
            name,design=load_pack(path);self.refresh(self.library.save(name,design));self.changed.emit()
        except (ValueError,OSError) as exc:self.error(exc)

    def import_art(self):
        path,_=QFileDialog.getOpenFileName(self,'Import annotation artwork','','Artwork (*.png *.jpg *.jpeg *.webp *.svg)')
        if not path:return
        try:
            layer=import_artwork(path);layer['x']=layer['y']=8
            design=new_design(max(16,round(layer['w']+16)),max(16,round(layer['h']+16)));design['layers']=[layer]
            name,ok=QInputDialog.getText(self,'Name imported annotation','Library name:',text=Path(path).stem[:120])
            if ok:self.refresh(self.library.save(name,design));self.changed.emit()
        except (ValueError,OSError) as exc:self.error(exc)

    def export(self):
        identity=self.current_identity()
        if not identity:return
        path,_=QFileDialog.getSaveFileName(self,'Export annotation pack','Annotation.sopannotation','Annotation packs (*.sopannotation)')
        if path:
            try:name,design=self.library.load(identity);save_pack(path,name,design)
            except (ValueError,OSError) as exc:self.error(exc)

    def delete(self):
        identity=self.current_identity()
        if not identity:return
        if QMessageBox.question(self,'Delete saved design','Delete this library entry? Existing SOP copies are kept.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        try:self.library.delete(identity);self.refresh();self.changed.emit()
        except (ValueError,OSError) as exc:self.error(exc)

    def use_selected(self):
        identity=self.current_identity()
        if identity and self.can_use:self.use_requested.emit(identity)

    def error(self,error):QMessageBox.warning(self,'Annotation library',str(error))
