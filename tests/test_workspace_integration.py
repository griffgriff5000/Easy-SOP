from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from sop_capture.ui.main_window import MainWindow
from sop_capture.workspace_layouts import LayoutLibrary


def test_independent_screen_copy_and_persistence(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    def fail(*args,**kwargs):raise AssertionError(str(args))
    monkeypatch.setattr(QMessageBox,'warning',fail)
    app=QApplication.instance();library=LayoutLibrary(tmp_path/'layouts.json');window=MainWindow(layout_library=library);window.show();window.show_page(7);app.processEvents()
    review=window.workspaces.hosts['revision'];editor=window.workspaces.hosts['editor']
    review.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea,review.panels['outline']);review.options['font_size']=12
    assert editor.capture()['panels']['outline']['area']=='left'
    window.workspaces.copy('revision',['editor']);assert editor.capture()['panels']['outline']['area']=='top'
    assert editor.options['font_size']==12
    window.show_page(1);window.show_page(7);assert review.capture()['panels']['outline']['area']=='top'
    window.close();reopened=MainWindow(layout_library=LayoutLibrary(library.path));assert reopened.workspaces.hosts['editor'].options['font_size']==12;reopened.close();window.deleteLater();reopened.deleteLater()


def test_workspace_toolbar_resolves_rebound_actions(tmp_path):
    from sop_capture.shortcuts import default_profile
    window=MainWindow(layout_library=LayoutLibrary(tmp_path/'layouts.json'));host=window.workspaces.hosts['editor'];window.apply_shortcut_profile(default_profile(),persist=False)
    assert host.actions['help'].isEnabled();host.actions['help'].trigger();assert window.help_dialog is not None
    window.close();window.deleteLater()


def test_customise_dialog_named_layout_and_write_failure_navigation(tmp_path,monkeypatch):
    from sop_capture.ui.workspaces import WorkspaceDialog
    window=MainWindow(layout_library=LayoutLibrary(tmp_path/'layouts.json'));window.show_page(7)
    dialog=WorkspaceDialog(window.workspaces,'revision',window);dialog.font.setValue(13);dialog.density.setCurrentText('compact');assert dialog.apply()
    window.workspaces.library.save_preset('My layout',window.workspaces.hosts['revision'].capture())
    window.workspaces.hosts['revision'].reset_layout();dialog.presets.addItem('My layout');dialog.presets.setCurrentText('My layout');dialog.load_preset()
    assert window.workspaces.hosts['revision'].options['font_size']==13
    def unwritable():raise OSError('Read only preferences')
    monkeypatch.setattr(window.workspaces.library,'write',unwritable);window.show_page(5)
    assert window.pages.currentIndex()==5
    window.close();window.deleteLater();dialog.deleteLater()


def test_copy_does_not_add_sop_edit_commands_to_document_review(tmp_path):
    window=MainWindow(layout_library=LayoutLibrary(tmp_path/'layouts.json'))
    window.workspaces.copy('editor',['revision'])
    review=window.workspaces.hosts['revision']
    assert 'add_step' not in review.actions and 'add_step' not in review.toolbar_ids
    assert 'screen_export' in review.toolbar_ids
    window.close();window.deleteLater()
