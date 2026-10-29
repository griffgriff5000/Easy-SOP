from copy import deepcopy
from PIL import Image
from PySide6.QtWidgets import QInputDialog
from sop_capture.models import Project,Step,Annotation
from sop_capture.storage import ProjectStore
from sop_capture.designs import AnnotationLibrary
from sop_capture.ui.main_window import MainWindow


def test_save_annotation_once_and_reuse_across_projects(tmp_path,monkeypatch):
    library=AnnotationLibrary(tmp_path/'shared-library')
    monkeypatch.setattr(MainWindow,'_annotation_library',lambda self:library)
    monkeypatch.setattr(QInputDialog,'getText',lambda *a,**kw:('Company arrow',True))
    first=ProjectStore(tmp_path/'project1');step=Step(annotations=[Annotation(kind='arrow',points=[30,30,150,90],color='#008080',width=6)])
    step.image=first.add_image(Image.new('RGB',(400,300),'white'),step.id)
    window=MainWindow();window.set_project(Project(steps=[step]),first);window.canvas.select(0)
    before=deepcopy(step.annotations)
    identity=window.save_selected_annotation()
    assert identity and library.entries()==[(identity,'Company arrow')]
    assert step.annotations==before
    second=ProjectStore(tmp_path/'project2');other=Step();other.image=second.add_image(Image.new('RGB',(400,300),'white'),other.id)
    window.set_project(Project(steps=[other]),second)
    assert identity in window.annotation_gallery.custom_buttons
    window.annotation_gallery.custom_buttons[identity].click();window.canvas.apply_gesture((20,20),(180,120))
    saved_design=library.load(identity)[1]
    assert other.annotations[0].design==saved_design
    other.annotations[0].design['layers'][0]['stroke']='#ff0000';window.flush_save()
    assert library.load(identity)[1]==saved_design
    assert first.load().steps[0].annotations==before
    library.delete(identity)
    assert second.load().steps[0].annotations[0].design['layers'][0]['stroke']=='#ff0000'
    window.close();window.deleteLater()


def test_cancel_saving_does_not_change_library_or_project(tmp_path,monkeypatch):
    library=AnnotationLibrary(tmp_path/'shared-library');monkeypatch.setattr(MainWindow,'_annotation_library',lambda self:library)
    monkeypatch.setattr(QInputDialog,'getText',lambda *a,**kw:('',False))
    store=ProjectStore(tmp_path/'project');step=Step(annotations=[Annotation(points=[10,10,50,50])]);step.image=store.add_image(Image.new('RGB',(100,100),'white'),step.id)
    window=MainWindow();window.set_project(Project(steps=[step]),store);window.canvas.select(0)
    assert window.save_selected_annotation() is None and not library.entries()
    assert len(step.annotations)==1
    window.close();window.deleteLater()
