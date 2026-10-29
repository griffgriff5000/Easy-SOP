"""Visual check of the basic document builder and company-info export order."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys,shutil
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QBuffer,QIODevice,Qt
from PySide6.QtGui import QImage,QPainter
from PySide6.QtPdf import QPdfDocument
from sop_capture.storage import ProjectStore
from sop_capture.ui.main_window import MainWindow
from sop_capture.ui.theme import stylesheet
from sop_capture.pdf_export import export_pdf
from sop_capture.word_export import export_docx

INFO='''<h2>Company-required information</h2><p>Complete these checks before starting the procedure.</p><table border="1"><tr><td><b>Document owner</b></td><td>Example operations team</td></tr><tr><td><b>Department</b></td><td>Site operations</td></tr><tr><td><b>Required approval</b></td><td>Supervisor sign-off</td></tr><tr><td><b>Risk assessment</b></td><td>RA-001</td></tr></table><p><b>Before you start</b></p><ul><li>Read the current risk assessment.</li><li>Check that the permit is valid.</li></ul>'''

def main():
    app=QApplication([]);output=Path('.superpowers/company-builder');output.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory() as temp:
        root=Path(temp)/'project';shutil.copytree('demo/Permit Management',root)
        store=ProjectStore(root);project=store.load();project.company_information=INFO;store.save(project)
        window=MainWindow();window.set_project(project,store);window.builder_modes.setCurrentIndex(1);window.show();window.show_page(2)
        for dark in (False,True):
            window.setStyleSheet(stylesheet(dark))
            for width,height in [(1000,760),(1280,800)]:
                window.resize(width,height);app.processEvents();window.grab().save(str(output/f'builder-{width}-{ "dark" if dark else "light"}.png'))
        pdf=export_pdf(project,root,output/'company-procedure.pdf');export_docx(project,root,output/'company-procedure.docx')
        source=QBuffer();source.setData(pdf.read_bytes());source.open(QIODevice.OpenModeFlag.ReadOnly)
        doc=QPdfDocument();doc.load(source)
        for number in range(doc.pageCount()):
            page=doc.render(number,doc.pagePointSize(number).toSize()*2)
            paper=QImage(page.size(),QImage.Format.Format_RGB32);paper.fill(Qt.GlobalColor.white)
            painter=QPainter(paper);painter.drawImage(0,0,page);painter.end();paper.save(str(output/f'page-{number+1}.png'))
        doc.close();source.close();window.close()
    print(output.resolve())

if __name__=='__main__':main()
