"""Visual magnifier QA using a synthetic screenshot, never a user capture."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageDraw,ImageFont
from PySide6.QtWidgets import QApplication
from sop_capture.models import Project,Step
from sop_capture.storage import ProjectStore
from sop_capture.imaging import font_path,render_step
from sop_capture.ui.main_window import MainWindow

app=QApplication([]);output=Path('.superpowers/magnifier');output.mkdir(parents=True,exist_ok=True)
with TemporaryDirectory() as temporary:
    image=Image.new('RGB',(1200,700),'#f4f7fa');draw=ImageDraw.Draw(image)
    draw.rectangle((0,0,1200,85),fill='#15344b')
    draw.text((45,23),'Project dashboard',font=ImageFont.truetype(str(font_path(True)),32),fill='white')
    draw.text((70,135),'Select the required project',font=ImageFont.truetype(str(font_path()),24),fill='#15344b')
    draw.rounded_rectangle((180,220,1080,600),radius=10,fill='white',outline='#b8c8d5',width=2)
    draw.text((550,355),'Permit ID: 0421',font=ImageFont.truetype(str(font_path(True)),16),fill='#15344b')
    draw.text((550,385),'Status: Ready',font=ImageFont.truetype(str(font_path()),16),fill='#15344b')
    store=ProjectStore(temporary);step=Step(title='Read the permit details',description='Draw a magnifier around the field, then adjust its zoom.')
    step.image=store.add_image(image,step.id);original=store.resolve(step.image).read_bytes()
    window=MainWindow();window.set_project(Project(steps=[step]),store);window.resize(1440,900);window.show();window.show_page(1);app.processEvents()
    window.annotation_gallery.default_buttons['magnifier'].click();window.canvas.set_annotation_style(color='#087f8c')
    window.canvas.apply_gesture((420,250),(850,530));app.processEvents()
    window.grab().save(str(output/'editor.png'));render_step(store.root,step,1).save(output/'magnified.png');image.save(output/'original.png')
    assert store.resolve(step.image).read_bytes()==original
    window.close();window.deleteLater();app.processEvents()
print('Magnifier visual QA complete; original screenshot unchanged.')
