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


@pytest.mark.parametrize('selected,position',[(0,1),(-1,2)])
def test_new_captures_follow_selected_step_and_keep_capture_order(tmp_path,selected,position):
    from sop_capture.capture import CaptureResult
    window=MainWindow();store=ProjectStore(tmp_path)
    first=Step(title='First',section='Preparation');last=Step(title='Last')
    window.set_project(Project(steps=[first,last]),store)
    window.steps_list.setCurrentRow(selected)
    originals=[s.id for s in window.project.steps]
    result=CaptureResult(image=Image.new('RGB',(40,30),'white'),bounds=(0,0,40,30),marker=None,button='left',timestamp='now')
    window._captured(result)
    captured=window.current_step()
    assert window.project.steps[position].id==captured.id
    assert [s.id for s in window.project.steps if s.id!=captured.id]==originals
    assert captured.section==('Preparation' if selected==0 else '')
    window._captured(result)
    assert window.project.steps[position+1].id==window.current_step().id
    assert store.load().steps[position].id==captured.id
    window.close()


def test_move_to_position_preserves_selection_content_save_and_undo(tmp_path):
    window=MainWindow();store=ProjectStore(tmp_path)
    steps=[Step(title=str(n),description=f'Instruction {n}') for n in range(5)]
    window.set_project(Project(steps=steps),store)
    window.steps_list.setCurrentRow(1);identity=window.current_step().id
    window.move_step_to(4)
    assert [s.title for s in window.project.steps]==['0','2','3','4','1']
    assert window.current_step().id==identity
    window.move_step_to(0)
    assert [s.title for s in window.project.steps]==['1','0','2','3','4']
    window.flush_save();assert store.load().steps[0].description=='Instruction 1'
    window.undo();assert [s.title for s in window.project.steps]==['0','2','3','4','1']
    window.steps_list.setCurrentRow(-1)
    window.move_step(1)
    assert [s.title for s in window.project.steps]==['0','2','3','4','1']
    window.close()


def test_drag_move_keeps_the_dragged_step_selected(tmp_path):
    from PySide6.QtCore import QModelIndex
    window=MainWindow();store=ProjectStore(tmp_path)
    steps=[Step(title=str(n)) for n in range(3)]
    window.set_project(Project(steps=steps),store)
    window.steps_list.setCurrentRow(0);identity=window.current_step().id
    assert window.steps_list.model().moveRows(QModelIndex(),0,1,QModelIndex(),3)
    assert [s.title for s in window.project.steps]==['1','2','0']
    assert window.current_step().id==identity
    window.undo();assert [s.title for s in window.project.steps]==['0','1','2']
    window.close()


def test_add_screenshot_below_keeps_original_and_supports_undo(tmp_path,monkeypatch):
    from types import SimpleNamespace
    window=MainWindow();store=ProjectStore(tmp_path)
    monkeypatch.setattr(window,'fail',lambda message:pytest.fail(str(message)))
    first=Step(title='Original');first.image=store.add_image(Image.new('RGB',(40,30),'red'),first.id)
    last=Step(title='Last')
    window.set_project(Project(steps=[first,last]),store);window.steps_list.setCurrentRow(0)
    original=first.image
    window.target=object()
    monkeypatch.setattr(window,'backend',SimpleNamespace(close=lambda:None,activate=lambda t:None,capture=lambda t:(Image.new('RGB',(40,30),'blue'),(0,0,40,30))))
    monkeypatch.setattr(window,'run_task',lambda work,done:done(work(),None))
    window.retake_image(new_step=True)
    assert len(window.project.steps)==3
    assert window.project.steps[0].image==original
    assert window.project.steps[1].id==window.current_step().id
    assert window.project.steps[2].id==last.id
    window.undo();assert [s.id for s in window.project.steps]==[first.id,last.id]
    window.steps_list.setCurrentRow(0)
    window.retake_image()
    assert len(window.project.steps)==2
    assert window.project.steps[0].id==first.id
    assert window.project.steps[0].image!=original
    window.undo();assert window.project.steps[0].image==original
    window.close()


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
