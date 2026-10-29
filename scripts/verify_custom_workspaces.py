"""Inspect personal layout controls and floating panels with isolated preferences."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QStandardPaths,Qt
from PySide6.QtWidgets import QApplication
from sop_capture.workspace_layouts import LayoutLibrary
from sop_capture.storage import ProjectStore
from sop_capture.ui.main_window import MainWindow
from sop_capture.ui.workspaces import WorkspaceDialog


def main():
    QStandardPaths.setTestModeEnabled(True);app=QApplication([]);out=Path('.superpowers/custom-workspaces');out.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory() as temporary:
        root=Path(temporary);shutil.copytree('demo/Permit Management',root/'project');store=ProjectStore(root/'project')
        window=MainWindow(layout_library=LayoutLibrary(root/'layouts.json'));window.set_project(store.load(),store);window.resize(1320,900);window.show();window.show_page(1);app.processEvents()
        for dark in (False,True):
            window._set_theme(dark);theme='dark' if dark else 'light'
            dialog=WorkspaceDialog(window.workspaces,'editor',window);dialog.show();app.processEvents();dialog.grab().save(str(out/f'customise-{theme}.png'));dialog.reject()
        host=window.workspaces.hosts['editor'];host.panels['properties'].setFloating(True);host.panels['properties'].resize(340,580);app.processEvents();host.panels['properties'].grab().save(str(out/'floating-properties.png'))
        window.workspaces.library.save_preset('My SOP editing',host.capture());window.workspaces.copy('editor',['document','revision']);window.show_page(5);app.processEvents();assert not host.panels['properties'].isVisible()
        window.show_page(1);app.processEvents();assert host.panels['properties'].isVisible();host.reset_layout();window.grab().save(str(out/'reset-editor.png'));window.close()
    print(out.resolve())

if __name__=='__main__':main()
