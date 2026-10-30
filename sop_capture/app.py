import argparse
import logging
from logging.handlers import RotatingFileHandler
import multiprocessing
from pathlib import Path
import sys


def main():
    multiprocessing.freeze_support()
    from .windows import enable_dpi_awareness
    enable_dpi_awareness()
    from .branding import application_icon_path, set_windows_application_identity
    set_windows_application_identity()
    from PySide6.QtGui import QIcon
    from PySide6.QtCore import QStandardPaths, QTimer
    from PySide6.QtWidgets import QApplication
    from .ui.main_window import MainWindow
    from .storage import ProjectStore
    parser = argparse.ArgumentParser(description="Local Windows SOP capture and documentation")
    parser.add_argument("project", nargs="?", help="Project folder or project.json")
    parser.add_argument("--smoke-test", action="store_true", help="Launch briefly and exit")
    parser.add_argument('--update-ack',help=argparse.SUPPRESS)
    parser.add_argument('--update-token',help=argparse.SUPPRESS)
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setOrganizationName("SOPCaptureStudio")
    app.setApplicationName("SOPCaptureStudio")
    app.setWindowIcon(QIcon(str(application_icon_path())))
    logs = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)) / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(logs / "studio.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(name)s %(message)s")
    window = MainWindow()
    if args.project:
        root = Path(args.project)
        if root.is_file(): root = root.parent
        store = ProjectStore(root)
        try: window.set_project(store.load(), store);window.show_page(1)
        except Exception as exc: window.fail(exc)
    window.show()
    if args.update_ack and args.update_token:
        def acknowledge():
            from . import __version__
            from .update_install import acknowledge_startup
            try:acknowledge_startup(args.update_ack,args.update_token,__version__)
            except Exception:logging.getLogger(__name__).exception('Could not acknowledge update startup')
        QTimer.singleShot(500,acknowledge)
    if args.smoke_test:
        QTimer.singleShot(1200, window.close)
        QTimer.singleShot(2000, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
