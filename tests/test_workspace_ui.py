import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PIL import Image
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication
from sop_capture.ui.main_window import MainWindow
from sop_capture.models import Project,Step
from sop_capture.storage import ProjectStore

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])

def test_canvas_has_working_space_and_contextual_inspector(tmp_path):
    window=MainWindow();store=ProjectStore(tmp_path)
    step=Step();step.image=store.add_image(Image.new('RGB',(900,600),'white'),step.id)
    window.set_project(Project(steps=[step]),store);window.resize(1280,800);window.show_page(1);window.show();QApplication.processEvents()
    assert window.canvas.height()>=400
    assert window.editor_inspector.count()==2
    window.tool_picker.setCurrentIndex(window.tool_picker.findData('text'));QApplication.processEvents()
    assert window.annotation_text.isVisible()
    assert not window.annotation_width.isVisible()
    window.tool_picker.setCurrentIndex(window.tool_picker.findData('arrow'));QApplication.processEvents()
    assert window.annotation_width.isVisible()
    assert not window.annotation_text.isVisible()
    before=window.canvas.image_rect();window.canvas.set_zoom(2)
    assert window.canvas.image_rect().width()==pytest.approx(before.width()*2)
    point=(450,300);mapped=window.canvas.image_point(window.canvas.display_point(point))
    assert mapped==pytest.approx(point)
    window.close()


def test_form_tabs_reveal_fields(tmp_path):
    window=MainWindow();window.set_project(Project(steps=[Step()]),ProjectStore(tmp_path))
    window.show();window.show_page(2);window.reveal_document_field('scope');QApplication.processEvents()
    assert window.document_fields['scope'].isVisible()
    window.reveal_document_field('approver');QApplication.processEvents()
    assert window.document_fields['approver'].isVisible()
    window.show_page(3);window.settings.show_category('Capture');QApplication.processEvents()
    assert window.settings.fields['delay'].isVisible()
    window.settings.show_category('Files and defaults');QApplication.processEvents()
    assert window.settings.fields['location'].isVisible()
    window.close()

def test_fit_pan_and_new_step_reset(tmp_path):
    from PySide6.QtCore import Qt,QPoint
    from PySide6.QtTest import QTest
    window=MainWindow();store=ProjectStore(tmp_path)
    first,second=Step(),Step()
    for step in (first,second):step.image=store.add_image(Image.new('RGB',(900,600),'white'),step.id)
    window.set_project(Project(steps=[first,second]),store);window.show_page(1);window.show();QApplication.processEvents()
    canvas=window.canvas;start=QPoint(100,100);end=QPoint(150,130)
    QTest.mousePress(canvas,Qt.MouseButton.MiddleButton,pos=start);QTest.mouseMove(canvas,end);QTest.mouseRelease(canvas,Qt.MouseButton.MiddleButton,pos=end)
    assert canvas.pan==QPointF()
    canvas.set_zoom(2)
    QTest.mousePress(canvas,Qt.MouseButton.MiddleButton,pos=start);QTest.mouseMove(canvas,end);QTest.mouseRelease(canvas,Qt.MouseButton.MiddleButton,pos=end)
    assert canvas.pan!=QPointF()
    window.steps_list.setCurrentRow(1)
    assert canvas.pan==QPointF()
    canvas.pan=QPointF(20,30);canvas.set_zoom(1)
    assert canvas.pan==QPointF()
    window.close()


def test_studio_pan_does_not_edit_design(tmp_path):
    from PySide6.QtCore import Qt,QPoint
    from PySide6.QtTest import QTest
    from sop_capture.ui.annotation_studio import AnnotationStudio
    from sop_capture.designs import AnnotationLibrary
    studio=AnnotationStudio(AnnotationLibrary(tmp_path/'library'))
    studio.show();QApplication.processEvents();studio.canvas.set_zoom(2);QApplication.processEvents()
    view=studio.canvas;before=(view.horizontalScrollBar().value(),view.verticalScrollBar().value())
    QTest.mousePress(view.viewport(),Qt.MouseButton.MiddleButton,pos=QPoint(200,180));QTest.mouseMove(view.viewport(),QPoint(240,210));QTest.mouseRelease(view.viewport(),Qt.MouseButton.MiddleButton,pos=QPoint(240,210))
    assert before!=(view.horizontalScrollBar().value(),view.verticalScrollBar().value())
    assert not studio.document.history
    studio.accept()


def test_shared_menus_update_after_shortcut_rebinding():
    from sop_capture.shortcuts import default_profile
    window=MainWindow()
    assert not window.action_bindings['save'].isEnabled()
    assert window.action_bindings['new'].isEnabled()
    profile=default_profile();profile['bindings']['help']='Ctrl+Alt+H'
    window.apply_shortcut_profile(profile,persist=False)
    assert len(window.menuBar().actions())==5
    assert window.app_menus['File'].actions()[0] is window.action_bindings['new']
    assert window.help_menu.actions()[0] is window.action_bindings['help']
    assert window.help_action.shortcut().toString()=='Ctrl+Alt+H'
    window.close()
