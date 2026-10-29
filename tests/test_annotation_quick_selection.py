from PIL import Image
from sop_capture.designs import AnnotationLibrary,new_design,new_layer
from sop_capture.models import Project,Step,Annotation
from sop_capture.storage import ProjectStore
from sop_capture.ui.main_window import MainWindow


def test_right_panel_quick_tools_and_saved_designs(tmp_path,monkeypatch):
    library=AnnotationLibrary(tmp_path/'annotations')
    design=new_design(200,100);design['layers']=[new_layer('rect',x=10,y=10,w=180,h=80)]
    identity=library.save('My callout',design)
    monkeypatch.setattr(MainWindow,'_annotation_library',lambda self:library,raising=False)
    window=MainWindow();store=ProjectStore(tmp_path/'project');step=Step()
    step.image=store.add_image(Image.new('RGB',(800,500),'white'),step.id)
    window.set_project(Project(steps=[step]),store)
    gallery=window.annotation_gallery
    gallery.default_buttons['arrow'].click()
    assert window.canvas.tool=='arrow' and window.tool_picker.currentData()=='arrow'
    step.annotations.append(Annotation(kind='arrow',points=[10,10,100,100]));window.canvas.select(0)
    gallery.default_buttons['arrow'].click();assert window.canvas.selected is None
    step.annotations.clear()
    window.tool_picker.setCurrentIndex(window.tool_picker.findData('callout'))
    assert gallery.default_buttons['callout'].isChecked()
    assert identity in gallery.custom_buttons
    assert not gallery.custom_buttons[identity].icon().isNull()
    gallery.custom_buttons[identity].click()
    assert window.canvas.tool=='design' and gallery.custom_buttons[identity].isChecked()
    assert not any(button.isChecked() for button in gallery.default_buttons.values())
    assert window.canvas.design_template==library.load(identity)[1]
    assert not step.annotations  # selecting a design only arms placement
    window.close();window.deleteLater()


def test_saved_picker_refreshes_without_opening_studio(tmp_path,monkeypatch):
    library=AnnotationLibrary(tmp_path/'annotations')
    monkeypatch.setattr(MainWindow,'_annotation_library',lambda self:library,raising=False)
    window=MainWindow();assert not window.annotation_gallery.custom_buttons
    design=new_design(100,100);design['layers']=[new_layer('ellipse',x=10,y=10,w=80,h=80)]
    identity=library.save('New circle',design)
    window.refresh_saved_annotations()
    assert identity in window.annotation_gallery.custom_buttons
    library.delete(identity);window.refresh_saved_annotations()
    assert identity not in window.annotation_gallery.custom_buttons
    window.close();window.deleteLater()
