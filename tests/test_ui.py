import os
import time
import pytest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PIL import Image
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QDialog
from sop_capture.models import Project, Step, Annotation
from sop_capture.storage import ProjectStore
from sop_capture.ui.main_window import MainWindow


@pytest.mark.parametrize("selected,expected", [(0, ["First", "New step", "Last"]), (-1, ["First", "Last", "New step"])])
def test_add_step_after_selection_or_append(tmp_path, selected, expected):
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    store = ProjectStore(tmp_path)
    window.set_project(Project(steps=[Step(title="First"), Step(title="Last")]), store)
    window.steps_list.setCurrentRow(selected)
    window.add_step()
    assert [step.title for step in window.project.steps] == expected
    assert window.current_step().title == "New step"
    window.flush_save()
    assert [step.title for step in store.load().steps] == expected
    window.undo()
    assert [step.title for step in window.project.steps] == ["First", "Last"]
    window.close()


def test_editor_roundtrip_undo_and_export(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.set_project(Project(title="UI procedure"), ProjectStore(tmp_path))
    window.add_step()
    window.step_title.setText("Open dashboard")
    window.step_description.setPlainText("Select the dashboard.")
    window.flush_save()
    assert ProjectStore(tmp_path).load().steps[0].title == "Open dashboard"
    window.add_step()
    assert len(window.project.steps) == 2
    window.undo()
    assert len(window.project.steps) == 1
    window.redo()
    assert len(window.project.steps) == 2
    window.reorder_steps(list(reversed([s.id for s in window.project.steps])))
    assert window.project.steps[1].title == "Open dashboard"
    path = window.export_to(tmp_path / "ui.pdf")
    assert path.exists()
    window.close()
    app.processEvents()


def test_canvas_redaction_edit_is_persisted(tmp_path):
    app = QApplication.instance() or QApplication([])
    store = ProjectStore(tmp_path)
    step = Step(title="Example")
    step.image = store.add_image(Image.new("RGB", (400, 200), "white"), step.id)
    window = MainWindow()
    window.set_project(Project(steps=[step]), store)
    window.canvas.set_tool("redact")
    window.canvas.apply_gesture((20, 20), (100, 100))
    window.flush_save()
    assert store.load().steps[0].annotations[0].kind == "redact"
    window.undo()
    assert not window.project.steps[0].annotations
    window.close()


def test_horizontal_arrow_is_accepted(tmp_path):
    app = QApplication.instance() or QApplication([])
    store = ProjectStore(tmp_path)
    step = Step()
    step.image = store.add_image(Image.new("RGB", (400, 200), "white"), step.id)
    window = MainWindow()
    window.set_project(Project(steps=[step]), store)
    window.canvas.set_tool("arrow")
    window.canvas.apply_gesture((20, 20), (100, 20))
    assert len(window.current_step().annotations) == 1
    window.close()


def test_initial_capture_callback_cannot_capture_a_new_session():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    class Session:
        state = "recording"
        count = 0
        def manual(self): self.count += 1
    first, second = Session(), Session()
    window.session = second
    window._initial_capture(first)
    assert second.count == 0
    window.session = None
    window.close()


def test_pdf_preview_loads_and_main_window_closes(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    errors = []
    monkeypatch.setattr(window, "fail", lambda message: errors.append(str(message)))
    window.set_project(Project(title="Preview test", steps=[Step(title="Action")]), ProjectStore(tmp_path))
    window.preview_pdf()
    deadline = time.monotonic()+5
    while window.busy and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    assert not window.busy
    from PySide6.QtPdf import QPdfDocument
    documents = window.findChildren(QPdfDocument)
    assert documents and documents[0].pageCount() >= 3
    assert window.close(), errors
    assert not errors
    assert not (tmp_path / ".project.lock").exists()


def test_duplicate_step_independent_and_undoable(tmp_path):
    app = QApplication.instance() or QApplication([])
    store = ProjectStore(tmp_path)
    source = Step(title="Open page", description="First action", marker=(50, 50),
                  annotations=[Annotation(kind="arrow", points=[10, 20, 100, 120])])
    source.image = store.add_image(Image.new("RGB", (400, 200), "white"), source.id)
    last = Step(title="Last")
    window = MainWindow()
    window.set_project(Project(steps=[source, last]), store)
    window.duplicate_step()
    duplicate = window.current_step()
    assert [s.title for s in window.project.steps] == ["Open page", "Open page", "Last"]
    assert duplicate.id != source.id
    assert duplicate.image == source.image
    assert duplicate.annotations[0] is not source.annotations[0]
    window.undo()
    assert len(window.project.steps) == 2
    window.redo()
    assert len(window.project.steps) == 3
    window.steps_list.setCurrentRow(1)
    window.step_title.setText("Second action")
    window.canvas.set_tool("edit")
    window.canvas.apply_gesture((55, 70), (75, 80))
    window.flush_save()
    reopened = store.load()
    assert reopened.steps[0].annotations[0].points == [10, 20, 100, 120]
    assert reopened.steps[1].annotations[0].points == [30, 30, 120, 130]
    assert reopened.steps[0].title == "Open page"
    assert reopened.steps[1].title == "Second action"
    window.close()


def test_edit_annotation_resize_delete_and_undo(tmp_path):
    app = QApplication.instance() or QApplication([])
    store = ProjectStore(tmp_path)
    step = Step(annotations=[Annotation(kind="highlight", points=[40, 40, 140, 140]),
                             Annotation(kind="arrow", points=[200, 30, 300, 80])])
    step.image = store.add_image(Image.new("RGB", (400, 200), "white"), step.id)
    window = MainWindow()
    window.set_project(Project(steps=[step]), store)
    window.canvas.set_tool("edit")
    window.canvas.apply_gesture((140, 140), (180, 170))
    assert window.current_step().annotations[0].points == [40, 40, 180, 170]
    window.undo()
    assert window.current_step().annotations[0].points == [40, 40, 140, 140]
    window.canvas.set_tool("edit")
    window.canvas.apply_gesture((300, 80), (330, 90))
    assert window.current_step().annotations[1].points == [200, 30, 330, 90]
    window.canvas.delete_selected()
    assert len(window.current_step().annotations) == 1
    window.undo()
    assert len(window.current_step().annotations) == 2
    window.close()


def test_qt_drag_moves_annotation_using_scaled_coordinates(tmp_path):
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    app = QApplication.instance() or QApplication([])
    store = ProjectStore(tmp_path)
    step = Step(annotations=[Annotation(kind="redact", points=[40, 40, 140, 140])])
    step.image = store.add_image(Image.new("RGB", (800, 400), "white"), step.id)
    window = MainWindow()
    window.set_project(Project(steps=[step]), store)
    window.show_page(1)
    window.show()
    app.processEvents()
    canvas = window.canvas
    canvas.set_tool("edit")
    rect = canvas.image_rect()
    def screen(x, y):
        return QPoint(round(rect.x()+x*rect.width()/800), round(rect.y()+y*rect.height()/400))
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=screen(90, 90))
    QTest.mouseMove(canvas, screen(120, 110))
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=screen(120, 110))
    points = window.current_step().annotations[0].points
    assert abs(points[0]-70) < 2 and abs(points[1]-60) < 2
    assert abs(points[2]-170) < 2 and abs(points[3]-160) < 2
    window.undo()
    assert window.current_step().annotations[0].points == [40, 40, 140, 140]
    window.close()


@pytest.mark.parametrize("kind", ["circle", "highlight", "redact", "blur"])
def test_reverse_drawn_annotations_can_move(tmp_path, kind):
    app = QApplication.instance() or QApplication([])
    store = ProjectStore(tmp_path)
    step = Step(annotations=[Annotation(kind=kind, points=[140, 140, 40, 40])])
    step.image = store.add_image(Image.new("RGB", (400, 200), "white"), step.id)
    window = MainWindow()
    window.set_project(Project(steps=[step]), store)
    window.canvas.set_tool("edit")
    window.canvas.apply_gesture((90, 90), (110, 100))
    assert window.current_step().annotations[0].points == [160, 150, 60, 50]
    window.close()
