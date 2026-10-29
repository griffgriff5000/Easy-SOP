from pathlib import Path
from PIL import Image
from sop_capture.models import Project,Step
from sop_capture.storage import ProjectStore
from sop_capture.templates import TemplateLibrary
from sop_capture.recent_projects import RecentProjects


def test_recent_projects_are_bounded_deduplicated_and_removable(tmp_path):
    recent=RecentProjects(tmp_path/'recent.json',limit=2)
    a,b,c=[tmp_path/name for name in ('a','b','c')]
    recent.record(Project(title='A'),a);recent.record(Project(title='B'),b);recent.record(Project(title='A updated'),a)
    assert [item['title'] for item in recent.entries()]==['A updated','B']
    recent.record(Project(title='C'),c)
    assert [item['root'] for item in recent.entries()]==[str(c.resolve()),str(a.resolve())]
    recent.remove(c);assert recent.entries()[0]['title']=='A updated'
    assert not c.exists()  # history never creates/deletes project folders
    assert RecentProjects(recent.path).entries()==recent.entries()


def test_home_can_open_recent_project_and_missing_entries_are_safe(tmp_path):
    from sop_capture.ui.main_window import MainWindow
    recent=RecentProjects(tmp_path/'recent.json');root=tmp_path/'project';store=ProjectStore(root);store.save(Project(title='Open me'))
    recent.record(store.load(),root);recent.record(Project(title='Missing'),tmp_path/'missing')
    window=MainWindow(recent_projects=recent,template_library=TemplateLibrary(tmp_path/'templates'))
    assert window.pages.currentWidget() is window.home_page
    window.home_page.projects.setCurrentRow(0);assert not window.home_page.open_button.isEnabled()
    window.home_page.projects.setCurrentRow(1);window.home_page.open_button.click()
    assert window.project.title=='Open me' and window.store.root==root.resolve()
    assert recent.entries()[0]['title']=='Open me'
    window.close();window.deleteLater()


def test_new_project_dialog_has_all_choices_and_creates_no_folder_until_accepted(tmp_path):
    from sop_capture.ui.new_project_dialog import NewProjectDialog
    library=TemplateLibrary(tmp_path/'templates');profile=library.save('Company',{})
    dialog=NewProjectDialog(library.list(),str(tmp_path))
    dialog.title.setText('My SOP');dialog.template.setCurrentIndex(dialog.template.findData(profile['id']))
    assert dialog.values()==('My SOP',profile['id'],str(tmp_path))
    assert not (tmp_path/'SOP - My SOP').exists()
    assert 'SOP - My SOP' in dialog.folder_preview.text()
    dialog.reject();dialog.deleteLater()


def test_libraries_can_be_browsed_without_a_project(tmp_path):
    from sop_capture.ui.main_window import MainWindow
    from sop_capture.designs import AnnotationLibrary,new_design,new_layer
    library=AnnotationLibrary(tmp_path/'annotations');design=new_design(100,100);design['layers']=[new_layer('rect',x=10,y=10,w=80,h=80)]
    identity=library.save('Shared design',design)
    window=MainWindow(template_library=TemplateLibrary(tmp_path/'templates'),recent_projects=RecentProjects(tmp_path/'recent.json'),annotation_library=library)
    window.show_page(6);assert window.annotation_library_page.entries.count()==1
    assert window.annotation_library_page.current_identity()==identity
    assert window.annotation_library_page.edit_button.isEnabled()
    assert not window.annotation_library_page.use_button.isEnabled()
    window.show_page(4);assert window.templates_page.preview_button.isEnabled()
    assert not window.templates_page.apply_button.isEnabled()
    window.home_page.annotations_button.click();assert window.pages.currentWidget() is window.annotation_library_page
    window.home_page.templates_button.click();assert window.pages.currentWidget() is window.templates_page
    window.close();window.deleteLater()


def test_template_preview_does_not_apply_or_modify_current_project(tmp_path,monkeypatch):
    from sop_capture.ui.main_window import MainWindow
    from sop_capture import ui
    import sop_capture.ui.main_window as main
    library=TemplateLibrary(tmp_path/'templates');profile=library.save('Preview this',{})
    window=MainWindow(template_library=library,recent_projects=RecentProjects(tmp_path/'recent.json'))
    store=ProjectStore(tmp_path/'active');window.set_project(Project(title='Keep my project'),store)
    before=window.project.to_dict();saved=(store.root/'project.json').read_bytes()
    calls=[]
    def export(project,root,output):
        assert root!=store.root and project.title=='Template preview'
        output.write_bytes(b'preview');return output
    monkeypatch.setattr(main,'export_pdf',export)
    monkeypatch.setattr(window,'run_task',lambda operation,callback:callback(operation(),None))
    monkeypatch.setattr(window,'_show_pdf_preview',lambda path:calls.append(path))
    window.preview_template(profile['id'])
    assert calls and window.project.to_dict()==before
    assert (store.root/'project.json').read_bytes()==saved
    window.close();window.deleteLater()


def test_annotation_library_duplicate_delete_and_import_keep_project_copies(tmp_path,monkeypatch):
    from copy import deepcopy
    from PySide6.QtWidgets import QInputDialog,QMessageBox
    from sop_capture.designs import AnnotationLibrary,new_design,new_layer
    from sop_capture.models import Annotation
    from sop_capture.ui.annotation_library_page import AnnotationLibraryPage
    library=AnnotationLibrary(tmp_path/'annotations');design=new_design(100,100);design['layers']=[new_layer('rect',x=10,y=10,w=80,h=80)]
    identity=library.save('Original',design);project=Project(steps=[Step(annotations=[Annotation(kind='design',points=[0,0,100,100],design=deepcopy(design))])])
    store=ProjectStore(tmp_path/'project');store.save(project)
    page=AnnotationLibraryPage(library)
    monkeypatch.setattr(QInputDialog,'getText',lambda *a,**kw:('Copy',True));page.duplicate()
    assert len(library.entries())==2 and page.current_identity()!=identity
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**kw:QMessageBox.StandardButton.Yes);page.delete()
    assert library.entries()==[(identity,'Original')]
    assert store.load().steps[0].annotations[0].design==design
    page.close();page.deleteLater()


def test_corrupt_history_and_new_dialog_validation(tmp_path):
    from sop_capture.ui.new_project_dialog import NewProjectDialog
    from PySide6.QtWidgets import QDialogButtonBox
    recent=RecentProjects(tmp_path/'recent.json');recent.path.write_text('invalid')
    assert recent.entries()==[]
    import json
    recent.path.write_text(json.dumps({'version':1,'projects':[{'root':str(tmp_path),'title':'Valid','template':None,'opened':[]}]}))
    assert recent.entries()[0]['template']=='' and recent.entries()[0]['opened']==''
    dialog=NewProjectDialog(TemplateLibrary(tmp_path/'templates').list(),str(tmp_path))
    assert not dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    dialog.title.setText('Valid');assert dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    dialog.location.setText('relative/path');assert not dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    dialog.reject();dialog.deleteLater()
