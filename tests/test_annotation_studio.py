import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import base64
from io import BytesIO
from copy import deepcopy
import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication
from sop_capture.designs import new_design, new_layer, validate_design, render_design, import_artwork, AnnotationLibrary, load_pack, save_pack
from sop_capture.models import Project, Step, Annotation
from sop_capture.storage import ProjectStore
from sop_capture.imaging import render_step

@pytest.fixture(scope='module',autouse=True)
def app():
    return QApplication.instance() or QApplication([])

def test_render_layers_transparency_rotation_and_lock(tmp_path):
    design=new_design(200,160)
    design['layers']=[new_layer('rect',x=20,y=20,w=80,h=60,fill='#ff0000',stroke='#ff0000',width=0), new_layer('ellipse',x=60,y=40,w=80,h=60,fill='#0000ff',width=0)]
    result=render_design(design)
    assert result.mode=='RGBA' and result.getpixel((0,0))[3]==0
    assert result.getpixel((70,60))[:3]==(0,0,255)
    design['layers'][1]['visible']=False
    assert render_design(design).getpixel((70,60))[:3]==(255,0,0)
    design['layers'][0].update(rotation=90,opacity=50,locked=True)
    assert 120 <= render_design(design).getpixel((60,50))[3] <= 130

@pytest.mark.parametrize('change', [lambda d:d.update(size=[100000,100]),lambda d:d['layers'].append({'kind':'shell'}), lambda d:d['layers'][0].update(x=float('nan')),lambda d:d['layers'][0].update(image='not base64')])
def test_invalid_design_rejected(change):
    design=new_design();design['layers']=[new_layer('image')]
    change(design)
    with pytest.raises(ValueError):validate_design(design)

def test_artwork_and_library_pack_are_self_contained(tmp_path):
    source=tmp_path/'art.png';Image.new('RGBA',(40,30),(0,200,0,100)).save(source)
    layer=import_artwork(source);design=new_design(200,100);design['layers']=[layer]
    source.unlink()
    library=AnnotationLibrary(tmp_path/'library');identity=library.save('Site marker',design)
    pack=tmp_path/'marker.sopannotation';save_pack(pack,'Site marker',design)
    name,loaded=load_pack(pack)
    assert name=='Site marker' and loaded==design
    library.delete(identity)
    assert render_design(loaded).getbbox()
    assert library.entries()==[]

def test_svg_import_and_external_reference_rejection(tmp_path):
    source=tmp_path/'shape.svg';source.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="30"><rect width="40" height="30" fill="red"/></svg>')
    layer=import_artwork(source)
    assert layer['kind']=='image'
    source.write_text('<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.com/a.png"/></svg>')
    with pytest.raises(ValueError):import_artwork(source)

def test_design_project_roundtrip_and_redaction(tmp_path):
    design=new_design(100,100);design['layers']=[new_layer('rect',x=0,y=0,w=100,h=100,fill='#0000ff',width=0)]
    store=ProjectStore(tmp_path);step=Step(annotations=[Annotation(kind='design',points=[10,10,110,110],design=design)])
    step.image=store.add_image(Image.new('RGB',(200,200),'white'),step.id)
    project=Project(steps=[step]);store.save(project)
    reopened=store.load();assert reopened.schema_version==4
    assert render_step(tmp_path,reopened.steps[0],1).getpixel((50,50))==(0,0,255)
    step.annotations.append(Annotation(kind='redact',points=[20,20,70,70]))
    assert render_step(tmp_path,step,1).getpixel((50,50))==(0,0,0)

def test_document_group_order_lock_and_undo():
    from sop_capture.design_document import DesignDocument
    document=DesignDocument()
    first=new_layer('rect',x=10,y=20);second=new_layer('ellipse',x=60,y=70)
    document.add(first);document.add(second)
    document.set_selection([first['id'],second['id']]);document.group()
    assert document.design['layers'][0]['group']==document.design['layers'][1]['group']
    document.align('left');assert document.design['layers'][1]['x']==10
    document.undo();assert document.design['layers'][1]['x']==60
    document.redo();assert document.design['layers'][1]['x']==10
    document.set_selection([first['id']]);document.update({'locked':True});document.update({'x':100})
    assert document.design['layers'][0]['x']==10
    document.duplicate();assert len(document.design['layers'])==3
    assert not document.selected_layers()[0]['locked']


def test_studio_draw_resize_and_discard(tmp_path,monkeypatch):
    from sop_capture.ui.annotation_studio import AnnotationStudio
    from PySide6.QtCore import Qt,QPointF
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QMessageBox
    studio=AnnotationStudio(AnnotationLibrary(tmp_path/'library'),can_use=True)
    studio.show();QApplication.processEvents();studio.canvas.fit_canvas()
    studio.tool.setCurrentIndex(studio.tool.findData('rect'))
    start=studio.canvas.mapFromScene(QPointF(80,80));end=studio.canvas.mapFromScene(QPointF(300,220))
    QTest.mousePress(studio.canvas.viewport(),Qt.MouseButton.LeftButton,pos=start)
    QTest.mouseMove(studio.canvas.viewport(),end)
    assert studio.document.design['layers']==[]
    QTest.mouseRelease(studio.canvas.viewport(),Qt.MouseButton.LeftButton,pos=end)
    assert len(studio.document.design['layers'])==1
    studio.tool.setCurrentIndex(0)
    studio.set_property('rotation',30);studio.set_property('fill','#00ff00')
    assert studio.document.design['layers'][0]['rotation']==30
    studio.document.undo();assert studio.document.design['layers'][0]['fill'] is None
    studio.document.redo();assert studio.document.design['layers'][0]['fill']=='#00ff00'
    studio.name.setText('Green box');studio.save_library()
    assert studio.library.entries()[0][1]=='Green box'
    studio.document.update({'rotation':0})
    monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.StandardButton.Discard)
    studio.reject()

def test_existing_shapes_convert_and_custom_design_can_be_placed_edited_and_undone(tmp_path,monkeypatch):
    from sop_capture.designs import from_annotation
    from sop_capture.ui.main_window import MainWindow
    from sop_capture.ui.annotation_studio import AnnotationStudio
    from PySide6.QtWidgets import QDialog
    arrow=Annotation(kind='arrow',points=[80,100,200,30],arrow_style='double',color='#0000ff')
    design,bounds=from_annotation(arrow)
    assert design['layers'][0]['arrow_style']=='double'
    assert design['layers'][0]['points'][0][1]==1
    window=MainWindow();store=ProjectStore(tmp_path)
    step=Step(annotations=[arrow]);step.image=store.add_image(Image.new('RGB',(600,400),'white'),step.id)
    window.set_project(Project(steps=[step]),store)
    original=deepcopy(step.annotations)
    def cancel(dialog):
        dialog.document.add(new_layer('rect',fill='#00ff00'))
        return QDialog.DialogCode.Rejected
    monkeypatch.setattr(AnnotationStudio,'exec',cancel)
    window.show_annotation_studio()
    assert step.annotations==original
    def accept(dialog):
        if not dialog.document.design['layers']:dialog.document.add(new_layer('rect',fill='#00ff00'))
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(AnnotationStudio,'exec',accept)
    window.show_annotation_studio()
    assert window.canvas.tool=='design'
    window.canvas.apply_gesture((100,140),(400,300))
    assert window.current_step().annotations[-1].kind=='design'
    snapshot=deepcopy(window.current_step().annotations[-1].design)
    window.canvas.set_tool('edit');window.canvas.select(1)
    window.show_annotation_studio()
    assert window.current_step().annotations[-1].design==snapshot
    window.undo()
    assert len(window.current_step().annotations)==1
    window.close()


def test_studio_resize_handle_freehand_and_text_editing(tmp_path,monkeypatch):
    from sop_capture.ui.annotation_studio import AnnotationStudio
    from PySide6.QtCore import Qt,QPointF
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QMessageBox
    studio=AnnotationStudio(AnnotationLibrary(tmp_path/'library'))
    studio.document.add(new_layer('rect',x=50,y=50,w=100,h=80))
    studio.show();QApplication.processEvents();studio.canvas.fit_canvas()
    grip=studio.canvas.mapFromScene(QPointF(150,130));end=studio.canvas.mapFromScene(QPointF(220,180))
    QTest.mousePress(studio.canvas.viewport(),Qt.MouseButton.LeftButton,pos=grip)
    QTest.mouseMove(studio.canvas.viewport(),end)
    QTest.mouseRelease(studio.canvas.viewport(),Qt.MouseButton.LeftButton,pos=end)
    assert studio.document.design['layers'][0]['w']>160
    studio.tool.setCurrentIndex(studio.tool.findData('path'))
    start=studio.canvas.mapFromScene(QPointF(100,200));mid=studio.canvas.mapFromScene(QPointF(150,250));end=studio.canvas.mapFromScene(QPointF(220,210))
    QTest.mousePress(studio.canvas.viewport(),Qt.MouseButton.LeftButton,pos=start)
    QTest.mouseMove(studio.canvas.viewport(),mid);QTest.mouseMove(studio.canvas.viewport(),end)
    QTest.mouseRelease(studio.canvas.viewport(),Qt.MouseButton.LeftButton,pos=end)
    assert studio.document.design['layers'][-1]['kind']=='path'
    studio.document.add(new_layer('text'))
    studio.text.setPlainText('');studio.text.setFocus();QTest.keyClicks(studio.text,'Hello')
    assert studio.document.design['layers'][-1]['text']=='Hello'
    monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.StandardButton.Discard)
    studio.reject()


def test_offscreen_design_clips_without_squeezing(tmp_path):
    design=new_design(100,100)
    design['layers']=[new_layer('rect',x=0,y=0,w=50,h=100,fill='#ff0000',width=0),new_layer('rect',x=50,y=0,w=50,h=100,fill='#0000ff',width=0)]
    store=ProjectStore(tmp_path);step=Step(annotations=[Annotation(kind='design',points=[-50,0,50,100],design=design)])
    step.image=store.add_image(Image.new('RGB',(200,200),'white'),step.id)
    assert render_step(tmp_path,step,1).getpixel((20,50))==(0,0,255)

def test_horizontal_arrowhead_and_existing_callout_layout(tmp_path):
    from sop_capture.designs import from_annotation,layer_image,layer_padding
    from sop_capture.imaging import callout_layout
    arrow=new_layer('arrow',x=30,y=80,w=120,h=1,width=5)
    design=new_design(200,160);design['layers']=[arrow]
    result=render_design(design)
    assert result.getpixel((138,75))[3]>0
    assert result.getpixel((80,78))[3]>0
    source=Annotation(kind='callout',points=[40,180,590,40],text='Choose this long label that wraps at the edge',font_size=20)
    box,lines,_=callout_layout(source,(600,300))
    converted,bounds=from_annotation(source,(600,300))
    rectangle=next(layer for layer in converted['layers'] if layer['kind']=='rect')
    assert rectangle['x']+bounds[0]==box[0]
    assert rectangle['w']==pytest.approx(box[2]-box[0])
    label=next(layer for layer in converted['layers'] if layer['kind']=='text')
    assert label['bold'] and label['font']=='vera'


def test_resize_click_does_not_reuse_previous_layer_size(tmp_path,monkeypatch):
    from sop_capture.ui.annotation_studio import AnnotationStudio
    from PySide6.QtCore import Qt,QPointF
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QMessageBox
    studio=AnnotationStudio(AnnotationLibrary(tmp_path/'library'))
    first=new_layer('rect',x=40,y=40,w=100,h=80);second=new_layer('ellipse',x=350,y=150,w=60,h=60)
    studio.document.add(first);studio.document.add(second);studio.document.set_selection([first['id']])
    studio.show();QApplication.processEvents();studio.canvas.fit_canvas()
    start=studio.canvas.mapFromScene(QPointF(140,120));end=studio.canvas.mapFromScene(QPointF(220,180))
    QTest.mousePress(studio.canvas.viewport(),Qt.MouseButton.LeftButton,pos=start);QTest.mouseMove(studio.canvas.viewport(),end);QTest.mouseRelease(studio.canvas.viewport(),Qt.MouseButton.LeftButton,pos=end)
    studio.document.set_selection([second['id']]);point=studio.canvas.mapFromScene(QPointF(410,210))
    QTest.mouseClick(studio.canvas.viewport(),Qt.MouseButton.LeftButton,pos=point)
    layer=next(row for row in studio.document.design['layers'] if row['id']==second['id'])
    assert layer['w']==60 and layer['h']==60
    monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.StandardButton.Discard)
    studio.reject()

def test_design_pdf_and_word_exports_have_images_and_no_spacer_page(tmp_path):
    from pypdf import PdfReader
    from docx import Document
    from sop_capture.pdf_export import export_pdf
    from sop_capture.word_export import export_docx
    design=new_design(800,500);design['layers']=[new_layer('ellipse',fill='#087f8c')]
    store=ProjectStore(tmp_path);step=Step(title='Open dashboard',section='Preparation',description='Select Dashboard.',annotations=[Annotation(kind='design',points=[20,30,780,505],design=design)])
    step.image=store.add_image(Image.new('RGB',(900,600),'white'),step.id)
    project=Project(title='Permit process',company='Example',author='Author',purpose='Review permits',scope='Site operations',steps=[step])
    pdf=PdfReader(export_pdf(project,tmp_path,tmp_path/'result.pdf'))
    assert len(pdf.pages)==3
    assert any('/XObject' in page['/Resources'] for page in pdf.pages)
    document=Document(export_docx(project,tmp_path,tmp_path/'result.docx'))
    assert len(document.inline_shapes)==1


def test_svg_with_local_gradient_and_use_is_supported(tmp_path):
    source=tmp_path/'gradient.svg'
    source.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="80" height="50"><defs><linearGradient id="g"><stop offset="0" stop-color="red"/><stop offset="1" stop-color="blue"/></linearGradient><rect id="r" width="80" height="50" fill="url(#g)"/></defs><use href="#r"/></svg>')
    assert import_artwork(source)['kind']=='image'

@pytest.mark.parametrize('dark, background, field_background', [(False,'#f2f6fa','#ffffff'),(True,'#101c29','#192a3b')])
def test_studio_properties_use_app_theme_over_native_dark_palette(tmp_path,dark,background,field_background):
    from PySide6.QtWidgets import QWidget
    from PySide6.QtGui import QPalette,QColor
    from sop_capture.ui.theme import stylesheet
    from sop_capture.ui.annotation_studio import AnnotationStudio
    app=QApplication.instance();original=app.palette();native=QPalette(original)
    native.setColor(QPalette.ColorRole.Window,QColor('#202020'))
    native.setColor(QPalette.ColorRole.Base,QColor('#292929'))
    app.setPalette(native)
    host=QWidget();host.setStyleSheet(stylesheet(dark))
    studio=AnnotationStudio(AnnotationLibrary(tmp_path/'library'),parent=host)
    try:
        studio.document.add(new_layer('rect'))
        studio.show();app.processEvents()
        properties=studio.fields['x'].parentWidget()
        assert properties.grab().toImage().pixelColor(0,0).name()==background
        assert studio.fields['x'].palette().color(QPalette.ColorRole.Base).name()==field_background
    finally:
        studio.accept();host.close();app.setPalette(original)
