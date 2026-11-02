from sop_capture.ui.main_window import MainWindow
from sop_capture.models import Project
from sop_capture.storage import ProjectStore


def test_document_layout_is_project_specific_saved_and_undoable(tmp_path):
    window=MainWindow();store=ProjectStore(tmp_path)
    window.set_project(Project(),store)
    window.document_layout.count.setCurrentIndex(window.document_layout.count.findData(4))
    window.document_layout.mode.setCurrentIndex(window.document_layout.mode.findData('grid'))
    window.flush_save();saved=store.load()
    assert saved.template['settings']['screenshots_per_page']==4
    assert saved.template['settings']['screenshot_layout']=='grid'
    window.undo();assert window.project.template['settings']['screenshot_layout']=='vertical'
    window.set_project(Project(),ProjectStore(tmp_path/'other'))
    assert window.document_layout.values()=={'screenshots_per_page':0,'screenshot_layout':'vertical'}
    window.close()


def test_saved_template_reuses_screenshot_layout_without_changing_other_projects(tmp_path):
    from sop_capture.templates import TemplateLibrary
    library=TemplateLibrary(tmp_path/'templates');window=MainWindow(template_library=library)
    page=window.templates_page;page.new_custom();page.name.setText('Four on a page')
    page.screenshot_layout.count.setCurrentIndex(page.screenshot_layout.count.findData(4))
    page.screenshot_layout.mode.setCurrentIndex(page.screenshot_layout.mode.findData('grid'))
    profile=page.save_changes()
    assert library.load(profile['id'])['settings']['screenshots_per_page']==4
    page.refresh(profile['id']);assert page.screenshot_layout.values()['screenshot_layout']=='grid'
    window.close()
