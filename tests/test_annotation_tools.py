import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from PIL import Image, ImageChops
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from sop_capture.models import Annotation, Project, Step
from sop_capture.imaging import render_step
from sop_capture.storage import ProjectStore
from sop_capture.pdf_export import export_pdf
from sop_capture.ui.main_window import MainWindow


def test_new_shapes_roundtrip_and_render(tmp_path):
    store = ProjectStore(tmp_path)
    step = Step(annotations=[Annotation(kind="line", points=[10, 10, 90, 10], color="#0000ff", width=6),
                             Annotation(kind="highlighter", points=[10, 25, 90, 60], color="#ff0000", opacity=50),
                             Annotation(kind="text", points=[10, 65, 190, 115], color="#000000", text="Choose this", font_size=22)])
    step.image = store.add_image(Image.new("RGB", (200, 120), "white"), step.id)
    store.save(Project(steps=[step]))
    reopened = store.load()
    assert reopened.steps[0].annotations[1].opacity == 50
    assert reopened.steps[0].annotations[2].text == "Choose this"
    image = render_step(tmp_path, reopened.steps[0], 1)
    assert image.getpixel((50, 10)) == (0, 0, 255)
    assert image.getpixel((50, 40)) == (255, 127, 127)
    assert any(image.getpixel((x, y)) != (255, 255, 255) for x in range(10, 170) for y in range(65, 110))
    from pypdf import PdfReader
    pdf = PdfReader(export_pdf(reopened, tmp_path, tmp_path / "styled.pdf"))
    screenshots = [item.image for page in pdf.pages for item in page.images]
    assert any(shot.size == (200, 120) and shot.getpixel((50, 10)) == (0, 0, 255) for shot in screenshots)


@pytest.mark.parametrize("field,value", [("font_size", 0), ("font_size", 300), ("opacity", -1), ("opacity", 101), ("text", 123)])
def test_invalid_annotation_style_rejected(field, value):
    data = Project(steps=[Step(annotations=[Annotation(points=[0, 0, 20, 20])])]).to_dict()
    data["steps"][0]["annotations"][0][field] = value
    with pytest.raises(ValueError): Project.from_dict(data)


def make_editor(tmp_path, annotations=None):
    app = QApplication.instance() or QApplication([])
    step = Step(annotations=annotations or [])
    store = ProjectStore(tmp_path)
    step.image = store.add_image(Image.new("RGB", (600, 300), "white"), step.id)
    window = MainWindow()
    window.set_project(Project(steps=[step]), store)
    window.show_page(1)
    window.show()
    app.processEvents()
    return app, window


def screen(canvas, x, y):
    rect = canvas.image_rect()
    return QPoint(round(rect.x()+x*rect.width()/600), round(rect.y()+y*rect.height()/300))


def test_drag_preview_is_actual_shape_without_mutating_step(tmp_path):
    app, window = make_editor(tmp_path)
    canvas = window.canvas
    canvas.set_tool("line")
    canvas.set_annotation_style(color="#0000ff", width=8)
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=screen(canvas, 100, 100))
    QTest.mouseMove(canvas, screen(canvas, 300, 100))
    preview = canvas.preview_image()
    assert preview.getpixel((200, 100)) == (0, 0, 255)
    assert not window.current_step().annotations
    QTest.keyClick(canvas, Qt.Key.Key_Escape)
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=screen(canvas, 300, 100))
    assert not window.current_step().annotations
    assert canvas.preview_image().getpixel((200, 100)) == (255, 255, 255)
    window.close()


def test_selected_style_changes_undo_and_persist(tmp_path):
    app, window = make_editor(tmp_path, [Annotation(kind="arrow", points=[40, 40, 200, 100])])
    canvas = window.canvas
    canvas.set_tool("edit")
    canvas.apply_gesture((120, 70), (120, 70))
    canvas.set_annotation_style(color="#00ff00", width=12)
    assert window.current_step().annotations[0].color == "#00ff00"
    assert window.current_step().annotations[0].width == 12
    window.undo()
    assert window.current_step().annotations[0].color == "#ef4444"
    window.redo()
    window.flush_save()
    assert window.store.load().steps[0].annotations[0].width == 12
    window.close()


def test_edit_preview_replaces_old_shape_but_does_not_commit(tmp_path):
    app, window = make_editor(tmp_path, [Annotation(kind="line", points=[100, 100, 300, 100], color="#0000ff", width=6)])
    canvas = window.canvas
    canvas.set_tool("edit")
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=screen(canvas, 200, 100))
    QTest.mouseMove(canvas, screen(canvas, 200, 150))
    image = canvas.preview_image()
    assert image.getpixel((200, 100)) == (255, 255, 255)
    assert image.getpixel((200, 150)) == (0, 0, 255)
    assert window.current_step().annotations[0].points == [100, 100, 300, 100]
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=screen(canvas, 200, 150))
    assert abs(window.current_step().annotations[0].points[1]-150) < 2
    window.close()


@pytest.mark.parametrize("tool", ["arrow", "line", "circle", "highlight", "highlighter", "text", "redact", "blur", "marker"])
def test_preview_matches_committed_render(tmp_path, tool):
    app, window = make_editor(tmp_path)
    canvas = window.canvas
    canvas.set_tool(tool)
    canvas.set_annotation_style(color="#0088ff", width=7, text="Preview label", font_size=24, opacity=45)
    start, end = screen(canvas, 100, 80), screen(canvas, 400, 220)
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(canvas, end)
    preview = canvas.preview_image()
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=end)
    committed = render_step(window.store.root, window.current_step(), 1, window.project)
    assert ImageChops.difference(preview, committed).getbbox() is None
    window.close()


def test_toolbar_styles_selected_text_and_highlighter(tmp_path):
    app, window = make_editor(tmp_path, [Annotation(kind="text", points=[40, 40, 220, 120], text="Old", font_size=18),
                                       Annotation(kind="highlighter", points=[300, 150, 500, 250], opacity=30)])
    window.tool_picker.setCurrentIndex(window.tool_picker.findData("edit"))
    window.canvas.apply_gesture((120, 80), (120, 80))
    assert window.annotation_text.isVisible()
    assert window.annotation_text.text() == "Old"
    window.annotation_text.setText("Updated text")
    window.annotation_text.setCursorPosition(1)
    QTest.keyClicks(window.annotation_text, "XY")
    window.annotation_font_size.setValue(36)
    assert window.current_step().annotations[0].text == "UXYpdated text"
    assert window.current_step().annotations[0].font_size == 36
    window.canvas.apply_gesture((400, 200), (400, 200))
    assert window.annotation_opacity.isEnabled()
    window.annotation_opacity.setValue(65)
    window.flush_save()
    assert window.store.load().steps[0].annotations[1].opacity == 65
    window.close()


def test_new_shape_does_not_cover_redaction(tmp_path):
    app, window = make_editor(tmp_path, [Annotation(kind="redact", points=[40, 40, 220, 120])])
    canvas = window.canvas
    canvas.set_tool("highlighter")
    canvas.set_annotation_style(color="#ffff00", opacity=100)
    canvas.apply_gesture((20, 20), (250, 150))
    assert render_step(window.store.root, window.current_step(), 1).getpixel((100, 80)) == (0, 0, 0)
    window.close()
