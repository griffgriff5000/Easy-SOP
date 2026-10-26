import os
import time
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PIL import Image
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QDialog
from sop_capture.models import Project, Step
from sop_capture.storage import ProjectStore
from sop_capture.ui.main_window import MainWindow


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
