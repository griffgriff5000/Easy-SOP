"""Built-in layered annotation designer and reusable design library."""
from copy import deepcopy
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QKeySequence, QShortcut, QIcon
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QWidget,QSplitter,QLabel,
    QPushButton,QComboBox,QLineEdit,QPlainTextEdit,QDoubleSpinBox,QSpinBox,QCheckBox,QListWidget,
    QListWidgetItem,QAbstractItemView,QColorDialog,QFileDialog,QMessageBox,QScrollArea,QTabWidget,QToolButton)
from ..designs import new_design, import_artwork, render_design, load_pack, save_pack
from ..design_document import DesignDocument
from .design_canvas import DesignCanvas
from .canvas import image_pixmap
from .components import page_header,menu_button,form_page,scroll_panel,tool_rail


class AnnotationStudio(QDialog):
    def __init__(self, library, design=None, can_use=False, parent=None):
        super().__init__(parent)
        self.library=library;self.identity=None;self.syncing=False
        self.document=DesignDocument(design)
        self.baseline=deepcopy(self.document.design)
        self.draw_style=dict(stroke='#ef4444',fill=None,width=4,text='Label',font_size=32,font='sans',bold=False,italic=False,opacity=100,arrow_style='solid')
        self.setWindowTitle('Annotation Studio');self.resize(1400,900);self.setMinimumSize(1000,700)
        outer=QVBoxLayout(self);outer.setSpacing(10)
        page_header(outer,'Annotation Studio','Draw, combine and reuse your own annotations.')
        row=QHBoxLayout()
        row.addWidget(menu_button('File',[('New design',self.new),('Save design',self.save_library),('Save as new design',lambda:self.save_library(True)),(None,None),('Import artwork...',self.import_image),('Import editable pack...',self.import_pack),(None,None),('Export editable pack...',self.export_pack),('Export transparent PNG...',self.export_png)]))
        self.name=QLineEdit('Untitled design');self.name.setMaxLength(120);self.name.setMaximumWidth(300);self.name.setAccessibleName('Design name');row.addWidget(self.name)
        self.add_button(row,'Save',self.save_library)
        self.undo_button=self.add_button(row,'Undo',self.document.undo);self.redo_button=self.add_button(row,'Redo',self.document.redo)
        row.addStretch()
        self.use_button=self.add_button(row,'Use design on step',self.use_design);self.use_button.setObjectName('primary');self.use_button.setEnabled(can_use)
        outer.addLayout(row)
        splitter=QSplitter();outer.addWidget(splitter,1)
        self.tool=QComboBox(self)
        for title,kind in [('Select / move','select'),('Rectangle','rect'),('Ellipse','ellipse'),('Triangle','triangle'),('Diamond','diamond'),('Arrow','arrow'),('Line','line'),('Text','text'),('Freehand','path')]:self.tool.addItem(title,kind)
        self.tool.hide()
        rail=tool_rail(self.tool);rail.setFixedWidth(50);splitter.addWidget(rail)
        centre=QWidget();workspace=QVBoxLayout(centre);workspace.setContentsMargins(0,0,0,0);workspace.setSpacing(8)
        controls=QHBoxLayout();self.active_tool=QLabel('Select / move');self.active_tool.setObjectName('caption');controls.addWidget(self.active_tool);controls.addStretch()
        self.zoom=QComboBox();self.zoom.setAccessibleName('Design zoom')
        for label,value in [('Fit',1),('125%',1.25),('150%',1.5),('200%',2)]:self.zoom.addItem(label,value)
        controls.addWidget(self.zoom);workspace.addLayout(controls)
        self.canvas=DesignCanvas(self.document,lambda:deepcopy(self.draw_style),self.error);workspace.addWidget(self.canvas,1)
        self.zoom.currentIndexChanged.connect(lambda:self.canvas.set_zoom(self.zoom.currentData()))
        self.zoom.activated.connect(lambda:self.canvas.set_zoom(self.zoom.currentData()))
        splitter.addWidget(centre)
        self.inspector=QTabWidget();self.inspector.setMinimumWidth(260);self.inspector.setMaximumWidth(360)
        properties,form=form_page();self.properties_form=form
        self.layer_name=QLineEdit();self.layer_name.setMaxLength(120);self.layer_name.editingFinished.connect(lambda:self.set_property('name',self.layer_name.text()))
        form.addRow('Layer name',self.layer_name)
        self.transform_group=QWidget();self.transform_group.setObjectName('scrollPage');transform_layout=QVBoxLayout(self.transform_group);transform_layout.setContentsMargins(0,0,0,0);transform_layout.setSpacing(4)
        self.transform_toggle=QToolButton();self.transform_toggle.setText('Position and size');self.transform_toggle.setCheckable(True);self.transform_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon);self.transform_toggle.setArrowType(Qt.ArrowType.RightArrow)
        transform_layout.addWidget(self.transform_toggle)
        transform_content,self.geometry_form=form_page();transform_content.layout().setContentsMargins(0,8,0,0);transform_layout.addWidget(transform_content);transform_content.hide()
        self.transform_toggle.toggled.connect(transform_content.setVisible)
        self.transform_toggle.toggled.connect(lambda checked:self.transform_toggle.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow))
        form.addRow(self.transform_group)
        self.fields={}
        for key,label,lo,hi in [('x','X',-4096,4096),('y','Y',-4096,4096),('w','Width',1,2048),('h','Height',1,2048),('rotation','Rotation',-360,360),('opacity','Opacity %',0,100),('width','Stroke',0,30),('font_size','Text size',8,144)]:
            spin=QDoubleSpinBox();spin.setDecimals(1);spin.setRange(lo,hi);spin.setKeyboardTracking(False)
            spin.valueChanged.connect(lambda value,k=key:self.set_property(k,value));self.fields[key]=spin;(self.geometry_form if key in {"x","y","w","h","rotation"} else form).addRow(label,spin)
        self.arrow_style=QComboBox();self.arrow_style.addItems(['solid','open','double']);self.arrow_style.currentTextChanged.connect(lambda value:self.set_property('arrow_style',value));form.addRow('Arrow heads',self.arrow_style)
        self.stroke=QPushButton('Choose outline / text colour');self.stroke.clicked.connect(lambda:self.choose_colour('stroke'));form.addRow(self.stroke)
        self.fill=QPushButton('Choose fill');self.fill.clicked.connect(lambda:self.choose_colour('fill'));form.addRow(self.fill)
        self.no_fill=QCheckBox('Transparent fill');self.no_fill.toggled.connect(self.toggle_fill);form.addRow(self.no_fill)
        self.font=QComboBox();self.font.addItems(['sans','serif','mono','vera']);self.font.currentTextChanged.connect(lambda value:self.set_property('font',value));form.addRow('Font family',self.font)
        self.bold=QCheckBox('Bold');self.bold.toggled.connect(lambda value:self.set_property('bold',value));form.addRow(self.bold)
        self.italic=QCheckBox('Italic');self.italic.toggled.connect(lambda value:self.set_property('italic',value));form.addRow(self.italic)
        self.text=QPlainTextEdit();self.text.setMaximumHeight(90);self.text.setPlaceholderText('Text for labels');self.text.textChanged.connect(lambda:self.set_property('text',self.text.toPlainText()));form.addRow(self.text)
        self.visible=QCheckBox('Visible');self.visible.toggled.connect(lambda value:self.set_property('visible',value));form.addRow(self.visible)
        self.locked=QCheckBox('Locked');self.locked.toggled.connect(lambda value:self.set_property('locked',value));form.addRow(self.locked)
        info=QLabel('Select multiple layers with Ctrl. Grouped layers move together. Drag the white corner handle to resize a single layer. Artwork keeps its aspect ratio inside its box.');info.setWordWrap(True);form.addRow(info)
        self.inspector.addTab(scroll_panel(properties),'Properties')
        layers_page=QWidget();layers_page.setObjectName('scrollPage');layers_box=QVBoxLayout(layers_page);layers_box.setSpacing(8)
        self.layers=QListWidget();self.layers.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection);self.layers.itemSelectionChanged.connect(self.select_layers)
        layers_box.addWidget(QLabel('Front to back'));layers_box.addWidget(self.layers,1)
        layer_actions=QHBoxLayout()
        layer_actions.addWidget(menu_button('Arrange',[('Bring forward',lambda:self.document.reorder(1)),('Send backward',lambda:self.document.reorder(-1)),(None,None),('Group',self.document.group),('Ungroup',lambda:self.document.group(True))]))
        self.add_button(layer_actions,'Duplicate',self.document.duplicate);self.add_button(layer_actions,'Delete',self.document.remove);layers_box.addLayout(layer_actions)
        self.align=QComboBox()
        for label,mode in [('Align left','left'),('Align right','right'),('Align top','top'),('Align bottom','bottom'),('Centre on canvas','center'),('Middle of canvas','middle')]:self.align.addItem(label,mode)
        align_row=QHBoxLayout();align_row.addWidget(self.align,1);self.add_button(align_row,'Align',lambda:self.document.align(self.align.currentData()));layers_box.addLayout(align_row)
        self.inspector.addTab(layers_page,'Layers')
        library_page,library_form=form_page()
        self.library_picker=QComboBox();library_form.addRow('Saved designs',self.library_picker)
        library_actions=QHBoxLayout();self.add_button(library_actions,'Load',self.load_library);self.add_button(library_actions,'Delete saved',self.delete_library);library_form.addRow(library_actions)
        self.canvas_width=QSpinBox();self.canvas_height=QSpinBox()
        for widget,value in zip((self.canvas_width,self.canvas_height),self.document.design['size']):widget.setRange(16,2048);widget.setValue(value)
        library_form.addRow('Canvas width',self.canvas_width);library_form.addRow('Canvas height',self.canvas_height)
        resize_button=QPushButton('Resize canvas');resize_button.clicked.connect(self.resize_canvas);library_form.addRow(resize_button)
        tip=QLabel('Save a named design once to reuse it across all projects. Placed annotations are independent copies. File contains artwork and editable-pack import/export.');tip.setWordWrap(True);tip.setObjectName('caption');library_form.addRow(tip)
        self.inspector.addTab(scroll_panel(library_page),'Library');splitter.addWidget(self.inspector)
        splitter.setSizes([50,850,300]);splitter.setStretchFactor(1,1)
        for index in range(3):splitter.setCollapsible(index,False)
        self.status=QLabel('Drag to draw. Ctrl selects multiple layers. Esc cancels the current gesture.');self.status.setObjectName('caption');self.status.setWordWrap(True)
        bottom=QHBoxLayout();bottom.addWidget(self.status,1);self.add_button(bottom,'Close',self.reject);outer.addLayout(bottom)
        def choose_tool():
            self.canvas.set_tool(self.tool.currentData());self.active_tool.setText(self.tool.currentText())
            if self.tool.currentData()!='select':self.document.set_selection([])
            self.inspector.setCurrentIndex(0);self.sync_properties()
        self.tool.currentIndexChanged.connect(choose_tool)
        self.document.changed.connect(self.refresh);self.document.selection_changed.connect(self.sync_properties)
        for key,callback in [('Ctrl+Z',self.document.undo),('Ctrl+Y',self.document.redo)]:
            shortcut=QShortcut(QKeySequence(key),self);shortcut.activated.connect(callback)
        self.refresh_library();self.refresh()

    def add_button(self,layout,title,callback):
        def invoke():
            try:callback()
            except (ValueError,OSError) as exc:self.error(exc)
        button=QPushButton(title);button.clicked.connect(lambda checked=False:invoke());layout.addWidget(button);return button

    def error(self,message):
        QMessageBox.warning(self,'Annotation Studio',str(message))

    def refresh_library(self):
        self.library_picker.clear()
        for identity,name in self.library.entries():self.library_picker.addItem(name,identity)
        if self.identity:self.library_picker.setCurrentIndex(self.library_picker.findData(self.identity))

    def refresh(self):
        self.syncing=True;self.layers.clear()
        for layer in reversed(self.document.design['layers']):
            suffix=(' [locked]' if layer['locked'] else '')+(' [hidden]' if not layer['visible'] else '')+(' [group]' if layer['group'] else '')
            item=QListWidgetItem(layer['name']+suffix);item.setData(Qt.ItemDataRole.UserRole,layer['id']);self.layers.addItem(item);item.setSelected(layer['id'] in self.document.selected)
        self.canvas_width.setValue(self.document.design['size'][0]);self.canvas_height.setValue(self.document.design['size'][1])
        self.undo_button.setEnabled(bool(self.document.history));self.redo_button.setEnabled(bool(self.document.future))
        self.syncing=False;self.sync_properties()

    def select_layers(self):
        if self.syncing:return
        self.document.set_selection([item.data(Qt.ItemDataRole.UserRole) for item in self.layers.selectedItems()])

    def sync_properties(self):
        self.syncing=True
        selected=self.document.selected_layers();layer=selected[-1] if selected else self.draw_style
        for i in range(self.layers.count()):self.layers.item(i).setSelected(self.layers.item(i).data(Qt.ItemDataRole.UserRole) in self.document.selected)
        self.layer_name.setText(layer.get('name',''));self.layer_name.setEnabled(bool(selected))
        locked=bool(selected) and all(row['locked'] for row in selected)
        for key,widget in self.fields.items():
            widget.setValue(layer.get(key,0 if key in {'x','y','rotation'} else 100));widget.setEnabled((bool(selected) or key in {'opacity','width','font_size'}) and not locked)
        for key,widget in [('bold',self.bold),('italic',self.italic),('visible',self.visible),('locked',self.locked)]:widget.setChecked(bool(layer.get(key,True if key=='visible' else False)))
        self.visible.setEnabled(bool(selected));self.locked.setEnabled(bool(selected))
        self.font.setCurrentText(layer.get('font','sans'))
        if self.text.toPlainText()!=layer.get('text','Label'):self.text.setPlainText(layer.get('text','Label'))
        self.no_fill.setChecked(layer.get('fill') is None)
        self.arrow_style.setCurrentText(layer.get('arrow_style','solid'))
        for key,button in [('stroke',self.stroke),('fill',self.fill)]:
            colour=layer.get(key) or '#ffffff';foreground='white' if QColor(colour).lightness()<130 else '#183247'
            button.setStyleSheet(f'background:{colour};color:{foreground};')
        kind=layer.get('kind',self.tool.currentData())
        geometry=bool(selected)
        for key in ('x','y','w','h','rotation'):self.geometry_form.setRowVisible(self.fields[key],geometry)
        self.properties_form.setRowVisible(self.transform_group,geometry)
        self.properties_form.setRowVisible(self.layer_name,geometry)
        for widget,visible in [(self.fields['width'],kind not in {'image','text','select'}),(self.stroke,kind not in {'image','select'}),
                               (self.fill,kind in {'rect','ellipse','triangle','diamond','text'}),(self.no_fill,kind in {'rect','ellipse','triangle','diamond','text'}),
                               (self.font,kind=='text'),(self.fields['font_size'],kind=='text'),(self.bold,kind=='text'),(self.italic,kind=='text'),(self.text,kind=='text'),
                               (self.arrow_style,kind=='arrow'),(self.visible,geometry),(self.locked,geometry)]:self.properties_form.setRowVisible(widget,visible)
        self.syncing=False

    def set_property(self,key,value):
        if self.syncing:return
        try:
            if key=='text' and len(value)>5000:raise ValueError('Labels support up to 5000 characters.')
            if self.document.selected:self.document.update({key:value})
            if key in self.draw_style:self.draw_style[key]=value
        except ValueError as exc:self.error(exc);self.sync_properties()

    def choose_colour(self,key):
        layer=(self.document.selected_layers() or [self.draw_style])[-1]
        colour=QColorDialog.getColor(QColor(layer.get(key) or '#ffffff'),self,'Layer colour')
        if colour.isValid():self.set_property(key,colour.name());self.sync_properties()

    def toggle_fill(self,checked):
        if not self.syncing:self.set_property('fill',None if checked else '#ffffff');self.sync_properties()

    def resize_canvas(self):
        design=deepcopy(self.document.design);design['size']=[self.canvas_width.value(),self.canvas_height.value()]
        self.document.commit(design);self.canvas.fit_canvas()

    def discard_changes(self):
        if self.document.design==self.baseline:return True
        return QMessageBox.question(self,'Unsaved design','Discard changes to this design? Save to the library first to keep them.',QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel)==QMessageBox.StandardButton.Discard

    def replace_document(self,design,name,identity=None):
        self.canvas.cancel_gesture();self.document.design=deepcopy(design);self.document.history.clear();self.document.future.clear();self.document.selected=[]
        self.baseline=deepcopy(design);self.identity=identity;self.name.setText(name)
        self.document.changed.emit();self.refresh_library();self.canvas.fit_canvas()

    def new(self):
        if self.discard_changes():self.replace_document(new_design(),'Untitled design')

    def load_library(self):
        identity=self.library_picker.currentData()
        if not identity or not self.discard_changes():return
        try:name,design=self.library.load(identity);self.replace_document(design,name,identity)
        except (ValueError,OSError) as exc:self.error(exc)

    def save_library(self,as_new=False):
        try:
            self.identity=self.library.save(self.name.text(),self.document.design,None if as_new else self.identity)
            self.baseline=deepcopy(self.document.design);self.refresh_library();self.status.setText('Design saved to the app annotation library. Available in every project.')
        except (ValueError,OSError) as exc:self.error(exc)

    def delete_library(self):
        identity=self.library_picker.currentData()
        if identity and QMessageBox.question(self,'Delete saved design','Delete this library entry? Designs already placed in SOPs are kept.')==QMessageBox.StandardButton.Yes:
            try:self.library.delete(identity)
            except (ValueError,OSError) as exc:self.error(exc);return
            if self.identity==identity:self.identity=None
            self.refresh_library()

    def import_image(self):
        path,_=QFileDialog.getOpenFileName(self,'Import artwork','','Artwork (*.png *.jpg *.jpeg *.webp *.svg)')
        if not path:return
        try:self.document.add(import_artwork(path))
        except (ValueError,OSError) as exc:self.error(exc)

    def import_pack(self):
        path,_=QFileDialog.getOpenFileName(self,'Import editable annotation','','Annotation pack (*.sopannotation *.json)')
        if not path or not self.discard_changes():return
        try:name,design=load_pack(path);self.replace_document(design,name)
        except (ValueError,OSError) as exc:self.error(exc)

    def output_path(self,title,suffix,filter):
        path,_=QFileDialog.getSaveFileName(self,title,'',filter)
        if not path:return None
        chosen=Path(path);output=chosen if chosen.suffix.lower()==suffix else chosen.with_suffix(suffix)
        if chosen!=output and output.exists() and QMessageBox.question(self,'Replace file?',f'Replace {output.name}?')!=QMessageBox.StandardButton.Yes:return None
        return output

    def export_pack(self):
        path=self.output_path('Export editable annotation','.sopannotation','Annotation pack (*.sopannotation)')
        if path:
            try:save_pack(path,self.name.text(),self.document.design)
            except (ValueError,OSError) as exc:self.error(exc)

    def export_png(self):
        path=self.output_path('Export transparent annotation','.png','PNG image (*.png)')
        if path:
            try:
                from io import BytesIO
                from ..storage import atomic_bytes
                data=BytesIO();render_design(self.document.design).save(data,'PNG');atomic_bytes(path,data.getvalue())
            except (ValueError,OSError) as exc:self.error(exc)

    def use_design(self):
        if not self.document.design['layers'] or not render_design(self.document.design).getbbox():
            self.error('Draw or import at least one visible element before placing the design.');return
        self.accept()

    def reject(self):
        if self.discard_changes():super().reject()
