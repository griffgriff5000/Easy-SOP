"""Capture the Home and library workspaces using isolated sample data."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication
from sop_capture.models import Project
from sop_capture.storage import ProjectStore
from sop_capture.templates import TemplateLibrary
from sop_capture.recent_projects import RecentProjects
from sop_capture.designs import AnnotationLibrary,new_design,new_layer
from sop_capture.ui.main_window import MainWindow
from sop_capture.ui.new_project_dialog import NewProjectDialog
from sop_capture.ui.theme import stylesheet

def main():
    QStandardPaths.setTestModeEnabled(True);app=QApplication([])
    out=Path('.superpowers/home');out.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory() as temp:
        root=Path(temp);templates=TemplateLibrary(root/'templates');annotations=AnnotationLibrary(root/'annotations')
        design=new_design(500,300);design['layers']=[new_layer('rect',x=30,y=30,w=440,h=240,stroke='#087f8c',fill='#ffffff'),new_layer('text',x=70,y=100,w=360,h=90,text='Select this button',stroke='#183247',font_size=32)]
        annotations.save('Instruction callout',design)
        recent=RecentProjects(root/'recent.json');store=ProjectStore(root/'SOP - Equipment setup');project=Project(title='Equipment setup');store.save(project);recent.record(project,store.root)
        window=MainWindow(templates,recent,annotations);window.show()
        for dark in (False,True):
            theme='dark' if dark else 'light';window.setStyleSheet(stylesheet(dark))
            for width,height in ((1000,760),(1320,900)):
                window.resize(width,height)
                for index,name in ((5,'home'),(4,'templates'),(6,'annotations')):
                    window.show_page(index);app.processEvents();window.grab().save(str(out/f'{name}-{theme}-{width}.png'))
            dialog=NewProjectDialog(templates.list(),str(root),parent=window);dialog.title.setText('Equipment setup');dialog.show();app.processEvents();dialog.grab().save(str(out/f'new-project-{theme}.png'));dialog.reject()
        window.close()
    print(out.resolve())

if __name__=='__main__':main()
