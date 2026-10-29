"""Render Annotation Studio, screenshot placement, and exported PDF for local visual QA."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from io import BytesIO
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QBuffer,QIODevice
from PySide6.QtPdf import QPdfDocument
from sop_capture.designs import new_design,new_layer,AnnotationLibrary,render_design,import_artwork
from sop_capture.models import Annotation,Project,Step
from sop_capture.storage import ProjectStore
from sop_capture.document_export import export_pdf
from sop_capture.word_export import export_docx
from sop_capture.ui.annotation_studio import AnnotationStudio
from sop_capture.ui.main_window import MainWindow

def main():
    app=QApplication([])
    output=Path('.superpowers/visual');output.mkdir(parents=True,exist_ok=True)
    design=new_design(800,500)
    design['layers']=[
        new_layer('rect',name='Panel',x=200,y=130,w=500,h=220,fill='#ffffff',stroke='#087f8c',width=5),
        new_layer('arrow',name='Pointer',x=80,y=240,w=120,h=1,stroke='#087f8c',width=6,points=[[1,0],[0,0]]),
        new_layer('ellipse',name='Step badge',x=230,y=160,w=80,h=80,fill='#087f8c',stroke='#087f8c',width=0),
        new_layer('text',name='Number',x=249,y=165,w=50,h=70,text='1',stroke='#ffffff',font_size=45,bold=True),
        new_layer('text',name='Instruction',x=335,y=165,w=330,h=100,text='Choose Dashboard',stroke='#183247',font_size=33,bold=True),
        new_layer('text',name='Supporting text',x=235,y=270,w=430,h=70,text='Start here to review your permits.',stroke='#587084',font_size=24),
        new_layer('path',name='Freehand underline',x=235,y=326,w=420,h=5,stroke='#f59e0b',width=4,points=[[0,0],[.2,.8],[.4,.2],[.6,1],[.8,.3],[1,.5]]),
    ]
    with TemporaryDirectory() as root:
        store=ProjectStore(Path(root)/'project')
        step=Step(title='Open the dashboard',section='Preparation',description='Select Dashboard to see the available permits.',annotations=[Annotation(kind='design',points=[20,30,780,505],design=design)])
        step.image=store.add_image(Image.new('RGB',(900,600),'#e4ebf2'),step.id)
        project=Project(title='Permit process',company='Example company',author='Author',purpose='Review permits',scope='Site operations',steps=[step])
        store.save(project)
        studio=AnnotationStudio(AnnotationLibrary(Path(root)/'library'),design,True)
        studio.document.set_selection([design['layers'][0]['id']]);studio.show();app.processEvents();studio.canvas.fit_canvas();app.processEvents()
        studio.grab().save(str(output/'annotation-studio.png'))
        render_design(design).save(output/'annotation-design.png')
        studio.accept()
        window=MainWindow();window.set_project(project,store);window.show_page(1);window.show();app.processEvents()
        window.grab().save(str(output/'annotation-on-step.png'))
        pdf=export_pdf(project,store.root,output/'annotation-studio.pdf')
        export_docx(project,store.root,output/'annotation-studio.docx')
        buffer=QBuffer();buffer.setData(pdf.read_bytes());buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        document=QPdfDocument();document.load(buffer)
        for number in range(document.pageCount()):
            size=document.pagePointSize(number).toSize()*2
            rendered=document.render(number,size)
            from PySide6.QtGui import QImage
            rendered=rendered.convertToFormat(QImage.Format.Format_RGBA8888)
            pixels=Image.frombytes('RGBA',(rendered.width(),rendered.height()),bytes(rendered.bits()),'raw','RGBA',rendered.bytesPerLine())
            paper=Image.new('RGBA',pixels.size,'white');paper.alpha_composite(pixels);paper.convert('RGB').save(output/f'annotation-pdf-{number+1}.png')
        document.close();buffer.close();window.close()
    print(output.resolve())

if __name__=='__main__':main()
