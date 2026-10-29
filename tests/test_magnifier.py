from copy import deepcopy
import pytest
from PIL import Image,ImageDraw
from sop_capture.models import Project,Step,Annotation
from sop_capture.storage import ProjectStore
from sop_capture.imaging import render_image


def scene():
    image=Image.new('RGB',(120,100),'#eeeeee');draw=ImageDraw.Draw(image)
    draw.rectangle((50,40,69,59),fill='red');return image


def test_magnifier_enlarges_inside_box_without_changing_source_or_outside():
    source=scene();before=source.tobytes()
    lens=Annotation(kind='magnifier',points=[20,10,100,90],zoom=2,color='#008080',width=2)
    rendered=render_image(source,Step(annotations=[lens]),1)
    assert rendered.size==source.size and source.tobytes()==before
    assert source.getpixel((44,50))==(238,238,238)
    assert rendered.getpixel((44,50))==(255,0,0)
    assert rendered.crop((0,0,20,100)).tobytes()==source.crop((0,0,20,100)).tobytes()
    assert rendered.crop((101,0,120,100)).tobytes()==source.crop((101,0,120,100)).tobytes()


@pytest.mark.parametrize('reverse',[False,True])
def test_magnifier_never_copies_redacted_pixels_elsewhere(reverse):
    source=scene();lens=Annotation(kind='magnifier',points=[20,10,100,90],zoom=4,width=1)
    mask=Annotation(kind='redact',points=[40,30,80,70])
    annotations=[lens,mask] if not reverse else [mask,lens]
    output=render_image(source,Step(annotations=annotations),1)
    assert output.getpixel((30,50))==(0,0,0)  # lens output outside original redaction


def test_magnifier_roundtrip_and_zoom_validation(tmp_path):
    store=ProjectStore(tmp_path);project=Project(steps=[Step(annotations=[Annotation(kind='magnifier',points=[10,10,80,80],zoom=2.5)])])
    store.save(project);loaded=store.load()
    assert loaded.schema_version==8 and loaded.steps[0].annotations[0].zoom==2.5
    for value in (0,1,6,float('nan'),True,'2'):
        data=deepcopy(project.to_dict());data['steps'][0]['annotations'][0]['zoom']=value
        with pytest.raises(ValueError):Project.from_dict(data)
    old=Project(steps=[Step(annotations=[Annotation(points=[1,1,10,10])])]).to_dict()
    assert 'zoom' not in old['steps'][0]['annotations'][0]


def test_canvas_magnifier_preview_and_zoom_edit(tmp_path):
    from sop_capture.ui.main_window import MainWindow
    window=MainWindow();store=ProjectStore(tmp_path);step=Step();step.image=store.add_image(scene(),step.id)
    window.set_project(Project(steps=[step]),store)
    window.annotation_gallery.default_buttons['magnifier'].click()
    assert window.canvas.tool=='magnifier'
    window.annotation_zoom.setValue(3)
    annotation=window.canvas.new_annotation((20,10),(100,90))
    assert annotation.zoom==3
    window.canvas.anchor=window.canvas.display_point((20,10));window.canvas.pointer=window.canvas.display_point((100,90))
    assert window.canvas.preview_image().tobytes()!=window.canvas.original.tobytes()
    assert not step.annotations
    window.canvas.cancel_gesture();step.annotations.append(annotation);window.canvas.refresh();window.canvas.select(0)
    window.annotation_zoom.setValue(2.5);assert step.annotations[0].zoom==2.5
    window.close();window.deleteLater()


def test_magnifier_is_flattened_into_word_and_pdf_exports(tmp_path):
    from io import BytesIO
    from zipfile import ZipFile
    from pypdf import PdfReader
    from sop_capture.word_export import export_docx
    from sop_capture.document_export import export_pdf
    store=ProjectStore(tmp_path);step=Step(title='Inspect the detail',description='Read the enlarged field.')
    step.image=store.add_image(scene(),step.id)
    source_bytes=store.resolve(step.image).read_bytes()
    step.annotations=[Annotation(kind='magnifier',points=[20,10,100,90],zoom=2)]
    project=Project(steps=[step]);store.save(project)
    with ZipFile(export_docx(project,tmp_path,tmp_path/'result.docx')) as archive:
        image=Image.open(BytesIO(archive.read(next(n for n in archive.namelist() if n.startswith('word/media/')))))
        assert image.convert('RGB').getpixel((44,50))==(255,0,0)
    pdf=PdfReader(export_pdf(project,tmp_path,tmp_path/'result.pdf'))
    embedded=[image.image for page in pdf.pages for image in page.images]
    assert any(image.size==(120,100) and image.convert('RGB').getpixel((44,50))==(255,0,0) for image in embedded)
    assert store.resolve(step.image).read_bytes()==source_bytes


def test_magnifier_draw_move_resize_undo_and_invalid_style(tmp_path):
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from PySide6.QtCore import Qt
    from sop_capture.ui.main_window import MainWindow
    window=MainWindow();store=ProjectStore(tmp_path);step=Step();step.image=store.add_image(scene(),step.id)
    window.set_project(Project(steps=[step]),store);window.show();window.show_page(1);QApplication.processEvents()
    window.annotation_gallery.default_buttons['magnifier'].click()
    canvas=window.canvas
    first=canvas.display_point((20,10)).toPoint();last=canvas.display_point((100,90)).toPoint()
    QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=first);QTest.mouseMove(canvas,last);QTest.mouseRelease(canvas,Qt.MouseButton.LeftButton,pos=last)
    assert len(window.current_step().annotations)==1
    lens=window.current_step().annotations[0];assert lens.kind=='magnifier'
    moved=canvas.edit_points(lens,None,(30,30),(35,35));assert moved[0]==pytest.approx(lens.points[0]+5)
    resized=canvas.edit_points(lens,2,(100,90),(110,95));assert resized[2:]==[110,95]
    canvas.select(0)
    with pytest.raises(ValueError):canvas.set_annotation_style(zoom=0)
    assert lens.zoom==2
    window.undo();assert not window.current_step().annotations
    window.redo();assert window.current_step().annotations[0].kind=='magnifier'
    window.close();window.deleteLater()
