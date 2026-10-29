from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget,QApplication
from sop_capture.ui.workspaces import DockWorkspace


def host(name):
    w=DockWorkspace(name,QWidget());w.add_panel('outline','Items',QWidget(),'left');w.add_panel('properties','Properties',QWidget(),'right')
    w.set_actions({'save':QAction('Save',w),'undo':QAction('Undo',w)},['save','undo']);w.seal_defaults();return w


def test_docks_independent_copy_reset_and_toolbar_order():
    app=QApplication.instance();editor=host('editor');review=host('review');editor.resize(900,600);editor.show();app.processEvents()
    editor.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea,editor.panels['outline']);editor.panels['properties'].hide();editor.set_toolbar(['undo','save'])
    layout=editor.capture();assert layout['panels']['outline']['area']=='bottom'
    review.apply_layout(layout,portable=True)
    assert review.capture()['toolbar']==['undo','save'] and review.panels['properties'].isHidden()
    review.reset_layout();assert review.capture()['panels']['outline']['area']=='left'
    assert editor.panels['properties'].isHidden()
    editor.set_locked(True);assert not (editor.panels['outline'].features() & editor.panels['outline'].DockWidgetFeature.DockWidgetMovable)
    editor.close();review.close();editor.deleteLater();review.deleteLater()


def test_floating_panels_hide_on_navigation_and_restore():
    app=QApplication.instance();workspace=host('editor');workspace.show();workspace.panels['outline'].setFloating(True);app.processEvents()
    workspace.deactivate();assert not workspace.panels['outline'].isVisible()
    workspace.activate();app.processEvents();assert workspace.panels['outline'].isVisible()
    workspace.close();workspace.deleteLater()


def test_invalid_native_state_falls_back_to_panel_positions():
    workspace=host('editor');layout=workspace.capture();layout['state']='bm90LXEtc3RhdGU='
    layout['panels']['outline']['area']='bottom';workspace.apply_layout(layout)
    assert workspace.capture()['panels']['outline']['area']=='bottom'
    workspace.close();workspace.deleteLater()
