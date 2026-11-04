from types import SimpleNamespace
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow
from sop_capture.ui.main_window import MainWindow


@pytest.mark.parametrize('state', [Qt.WindowState.WindowNoState, Qt.WindowState.WindowMaximized, Qt.WindowState.WindowFullScreen])
@pytest.mark.parametrize('failure', [None, 'activate', 'capture'])
def test_retake_restores_window_state(qt_application, state, failure):
    class Window(QMainWindow):
        retake_image = MainWindow.retake_image
        def current_step(self): return self.step
        def notice(self, text): pass
        def fail(self, error): self.error = error
        def _replace_step_image(self, step, image): pass
        def run_task(self, task, finished):
            finished(None if failure else ('image', None), RuntimeError('capture') if failure else None)

    # Use the production state helpers when present, keeping the test red before the fix.
    for name in ('_minimize_for_capture', '_restore_after_capture'):
        if hasattr(MainWindow, name): setattr(Window, name, getattr(MainWindow, name))
    window = Window()
    window.step = object()
    window.project = object()
    window.target = object()
    window.active = window.busy = False
    def activate(target):
        if failure == 'activate': raise RuntimeError('activate')
    window.backend = SimpleNamespace(activate=activate)
    window.setWindowState(state)
    window.show()
    window.retake_image()
    assert window.windowState() & (Qt.WindowState.WindowMaximized | Qt.WindowState.WindowFullScreen | Qt.WindowState.WindowMinimized) == state
    window.close()
