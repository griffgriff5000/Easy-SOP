"""Application identity shared by source and packaged Windows launches."""
from pathlib import Path
import sys

APP_USER_MODEL_ID = 'SOPCaptureStudio.Desktop'


def application_icon_path() -> Path:
    return Path(__file__).with_name('assets') / 'app.ico'


def set_windows_application_identity():
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
