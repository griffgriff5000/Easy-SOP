"""Capture every application workspace in both themes and multiple window sizes."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys,shutil
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from sop_capture.storage import ProjectStore
from sop_capture.ui.main_window import MainWindow
from sop_capture.ui.theme import stylesheet
from sop_capture.ui.annotation_studio import AnnotationStudio
from sop_capture.designs import AnnotationLibrary,new_design,new_layer
from sop_capture.ui.shortcuts_dialog import ShortcutsDialog
from sop_capture.workspace_layouts import LayoutLibrary

def main():
    app=QApplication([]);out=Path('.superpowers/workspace');out.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory() as temp:
        root=Path(temp);shutil.copytree('demo/Permit Management',root/'project')
        store=ProjectStore(root/'project');window=MainWindow(layout_library=LayoutLibrary(root/'layouts.json'));window.set_project(store.load(),store)
        window.builder_modes.setCurrentIndex(1);window.show()
        for dark in (False,True):
            theme='dark' if dark else 'light';window._set_theme(dark)
            for width,height in ((1000,760),(1280,800),(1440,900)):
                window.resize(width,height);app.processEvents()
                for page,name in enumerate(('capture','editor','document','settings','templates')):
                    window.show_page(page);app.processEvents();window.grab().save(str(out/f'{name}-{theme}-{width}.png'))
            window.resize(1280,800);window.show_page(1)
            window.tool_picker.setCurrentIndex(window.tool_picker.findData('arrow'));app.processEvents()
            window.grab().save(str(out/f'editor-properties-{theme}.png'))
            design=new_design(800,500);design['layers']=[new_layer('rect',x=100,y=130,w=500,h=220,fill='#ffffff',stroke='#087f8c'),new_layer('text',x=140,y=180,w=420,h=120,text='Choose Dashboard',stroke='#183247',font_size=36,bold=True),new_layer('arrow',x=70,y=240,w=80,h=1,stroke='#087f8c',width=5,points=[[1,0],[0,0]])]
            studio=AnnotationStudio(AnnotationLibrary(root/'annotations'),design,True,window)
            studio.document.set_selection([design['layers'][1]['id']]);studio.show();studio.resize(1280,800);app.processEvents();studio.canvas.fit_canvas()
            for i,name in enumerate(('properties','layers','library')):
                studio.inspector.setCurrentIndex(i);app.processEvents();studio.grab().save(str(out/f'studio-{name}-{theme}.png'))
            studio.resize(1000,760);app.processEvents();studio.grab().save(str(out/f'studio-{theme}-1000.png'));studio.accept()
            dialog=ShortcutsDialog(window.shortcut_profile,lambda:window.settings.value('shortcut'),lambda p:None,window)
            dialog.show();app.processEvents();dialog.grab().save(str(out/f'shortcuts-{theme}.png'));dialog.close()
            window.show_help();app.processEvents();window.help_dialog.grab().save(str(out/f'help-{theme}.png'));window.help_dialog.close()
        window.close()
    print(out.resolve())

if __name__=='__main__':main()
