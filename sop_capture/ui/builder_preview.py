"""Asynchronous, memory-backed actual-document preview embedded in Builder."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import threading
from PySide6.QtCore import QObject,Signal,Slot,QBuffer,QIODevice,Qt,QPointF,QTimer,QSize
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QSpinBox,QStackedWidget,QScrollArea


def document_key(project,root):
    data=project.to_dict();data['updated']=project.updated[:10]
    return str(Path(root).resolve())+':'+sha256(json.dumps(data,sort_keys=True).encode('utf-8')).hexdigest()


class PreviewSignals(QObject):
    finished=Signal(int,str,object,object)


class BuilderPreview(QWidget):
    refresh_requested=Signal()
    activity_changed=Signal(bool)
    def __init__(self,current_key,exporter=None):
        super().__init__();self.current_key=current_key
        from ..document_export import export_pdf
        self.exporter=exporter or export_pdf;self.running=False;self.generation=0;self.pending=None;self.loaded_key=None
        self.document=None;self.source=None
        self.signals=PreviewSignals(self);self.signals.finished.connect(self.finished)
        box=QVBoxLayout(self);box.setContentsMargins(0,0,0,0);box.setSpacing(8)
        row=QHBoxLayout();self.status=QLabel('The loaded template and captured SOP will appear here.');self.status.setWordWrap(True);self.status.setObjectName('caption');row.addWidget(self.status,1)
        self.refresh=QPushButton('Refresh preview');self.refresh.clicked.connect(self.refresh_requested);row.addWidget(self.refresh);box.addLayout(row)
        self.stack=QStackedWidget();self.empty=QLabel('Open a project to view its document.');self.empty.setWordWrap(True);self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter);self.stack.addWidget(self.empty)
        self.view=QScrollArea();self.view.setWidgetResizable(False);self.view.setAlignment(Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignTop)
        self.page_image=QLabel();self.page_image.setStyleSheet('background:white;');self.view.setWidget(self.page_image);self.stack.addWidget(self.view);box.addWidget(self.stack,1)
        self.resize_timer=QTimer(self);self.resize_timer.setSingleShot(True);self.resize_timer.setInterval(120);self.resize_timer.timeout.connect(self.render_page)
        pages=QHBoxLayout();pages.addWidget(QLabel('Page'));self.page=QSpinBox();self.page.setRange(1,1);self.page.setEnabled(False);pages.addWidget(self.page);self.page_total=QLabel('');pages.addWidget(self.page_total);pages.addStretch();box.addLayout(pages)
        self.page.valueChanged.connect(self.jump)

    def jump(self,value):
        self.render_page()
        self.view.verticalScrollBar().setValue(0)

    def reset(self):
        self.generation+=1;self.pending=None;self.loaded_key=None;self.clear_document();self.status.setText('Choose Refresh preview to display this template with the SOP.');self.empty.setText('The actual document preview will appear here.')

    def clear_document(self):
        self.resize_timer.stop();self.page_image.clear()
        if self.document:self.document.close();self.document.deleteLater();self.document=None
        if self.source:self.source.close();self.source.deleteLater();self.source=None
        self.stack.setCurrentIndex(0);self.page.setEnabled(False);self.page_total.setText('')

    def invalidate(self):
        self.status.setText('Changes saved. Refresh preview to update the document pages.' if self.loaded_key else 'Refresh preview to show the loaded template and captured SOP.')

    def request(self,project,root):
        key=document_key(project,root)
        if self.running:self.pending=(deepcopy(project),Path(root));return
        if key==self.loaded_key:self.status.setText('Preview is up to date.');return
        generation=self.generation;snapshot=deepcopy(project);root=Path(root)
        self.running=True;self.refresh.setEnabled(False);self.status.setText('Building the template and SOP preview... You can continue editing.');self.activity_changed.emit(True)
        def worker():
            try:
                with tempfile.TemporaryDirectory(prefix='sop-builder-') as temp:
                    output=self.exporter(snapshot,root,Path(temp)/'preview.pdf');data=Path(output).read_bytes()
                self.signals.finished.emit(generation,key,data,None)
            except Exception as exc:self.signals.finished.emit(generation,key,None,str(exc))
        self.thread=threading.Thread(target=worker,daemon=True);self.thread.start()

    @Slot(int,str,object,object)
    def finished(self,generation,key,data,error):
        self.running=False;self.refresh.setEnabled(True)
        if generation==self.generation:
            if error:self.status.setText('Preview unavailable: '+error)
            elif key!=self.current_key():self.status.setText('Document changed while rendering. Refresh preview to show the latest edits.')
            else:
                from PySide6.QtPdf import QPdfDocument
                self.clear_document()
                self.source=QBuffer(self);self.source.setData(data);self.source.open(QIODevice.OpenModeFlag.ReadOnly)
                self.document=QPdfDocument(self);self.document.load(self.source)
                if self.document.pageCount():
                    self.stack.setCurrentIndex(1);self.page.setRange(1,self.document.pageCount());self.page.setValue(1);self.page.setEnabled(True);self.page_total.setText('of '+str(self.document.pageCount()));self.loaded_key=key;self.render_page()
                    self.status.setText('Preview is up to date.' if key==self.current_key() else 'Document changed while rendering. Refresh preview for the latest edits.')
                else:self.status.setText('The document preview could not be read.')
        self.activity_changed.emit(False)
        if self.pending:
            project,root=self.pending;self.pending=None;self.request(project,root)


    def resizeEvent(self,event):
        super().resizeEvent(event)
        if self.document:self.resize_timer.start()

    def render_page(self):
        if self.document is None or not self.document.pageCount():return
        from PySide6.QtGui import QImage,QPainter,QPixmap
        number=max(0,min(self.document.pageCount()-1,self.page.value()-1))
        size=self.document.pagePointSize(number)
        width=max(240,min(1600,self.view.viewport().width()-20))
        height=max(1,round(width*size.height()/max(1,size.width())))
        rendered=self.document.render(number,QSize(width,height))
        paper=QImage(rendered.size(),QImage.Format.Format_RGB32);paper.fill(Qt.GlobalColor.white)
        painter=QPainter(paper);painter.drawImage(0,0,rendered);painter.end()
        self.page_image.setPixmap(QPixmap.fromImage(paper));self.page_image.resize(width,height)
