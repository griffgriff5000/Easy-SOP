"""Render and inspect the compact default/custom annotation gallery."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PIL import Image
from sop_capture.ui.main_window import MainWindow
from sop_capture.designs import AnnotationLibrary,new_design,new_layer
from sop_capture.models import Project,Step
from sop_capture.storage import ProjectStore

app=QApplication([])
with TemporaryDirectory() as temporary:
    root=Path(temporary);library=AnnotationLibrary(root/'annotations')
    for name,kind in [('Outline label','rect'),('Oval label','ellipse'),('Diamond','diamond')]:
        design=new_design(180,100);design['layers']=[new_layer(kind,x=10,y=10,w=160,h=80,stroke='#087f8c',fill='#ffffff')];library.save(name,design)
    MainWindow._annotation_library=lambda self:library
    window=MainWindow();store=ProjectStore(root/'project');step=Step(title='Select a project');step.image=store.add_image(Image.new('RGB',(900,550),'#e6eff6'),step.id)
    window.set_project(Project(steps=[step]),store);window.show();window.show_page(1);window.editor_inspector.setCurrentIndex(1)
    output=Path('.superpowers/quick-annotations');output.mkdir(parents=True,exist_ok=True)
    for width in (1000,1320,1440):
        window.resize(width,900);app.processEvents();window.annotation_gallery.default_buttons['arrow'].click();app.processEvents()
        for grid in (window.annotation_gallery.defaults,window.annotation_gallery.custom):
            assert all(button.geometry().right()<grid.width() for button in grid.buttons)
        window.grab().save(str(output/f'gallery-{width}.png'))
    window.close();window.deleteLater();app.processEvents()
print('Gallery fits at 1000, 1320 and 1440 pixels.')
