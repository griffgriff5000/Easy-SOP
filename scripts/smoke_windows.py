"""Exercise native capture only against an isolated synthetic test window.

Does not inject input or read any existing application's pixels.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def fixture(info):
    from sop_capture.windows import enable_dpi_awareness
    enable_dpi_awareness()
    from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
    from PySide6.QtCore import QTimer
    app = QApplication([])
    widget = QWidget()
    widget.setWindowTitle("SOP isolated capture fixture")
    widget.resize(700, 430)
    widget.setStyleSheet("background: #edf4f8; color: #14324b; font: 20px 'Segoe UI';")
    layout = QVBoxLayout(widget)
    layout.addWidget(QLabel("SYNTHETIC CAPTURE TEST\nNo private information\nWindow-only rendering"))
    layout.addWidget(QPushButton("Example action"))
    widget.show()
    Path(info).write_text(json.dumps({"hwnd": int(widget.winId()), "pid": os.getpid()}))
    QTimer.singleShot(25000, app.quit)
    app.exec()


def main(renderer_executable=None):
    from sop_capture.windows import WindowsBackend, WindowInfo, NativeInput, enable_dpi_awareness
    from sop_capture.capture import CaptureSession, CaptureOptions
    enable_dpi_awareness()
    if renderer_executable:
        import multiprocessing
        import multiprocessing.spawn
        multiprocessing.set_executable(str(Path(renderer_executable).resolve()))
        # A source parent normally passes `-c` to a Python interpreter. A frozen
        # child expects this protocol instead, exactly as a frozen parent uses.
        executable = str(Path(renderer_executable).resolve())
        multiprocessing.spawn.get_command_line = lambda **kw: [executable, "--multiprocessing-fork", *[f"{k}={v}" for k, v in kw.items()]]
        preparation = multiprocessing.spawn.get_preparation_data
        def frozen_preparation(name):
            data = preparation(name)
            # Do not replace a frozen child's module path with this source
            # interpreter's Windows Store DLL paths or source main script.
            data["sys_path"] = [str(Path(executable).parent / "_internal")]
            data.pop("init_main_from_name", None)
            data.pop("init_main_from_path", None)
            return data
        multiprocessing.spawn.get_preparation_data = frozen_preparation
    with tempfile.TemporaryDirectory() as temporary:
        info = Path(temporary) / "window.json"
        process = subprocess.Popen([sys.executable, __file__, "--fixture", str(info)], creationflags=subprocess.CREATE_NO_WINDOW)
        backend = WindowsBackend()
        input_hook = None
        session = None
        try:
            deadline = time.monotonic()+15
            while not info.exists() and time.monotonic() < deadline:
                time.sleep(.1)
            identity = json.loads(info.read_text())
            target = WindowInfo(identity["hwnd"], identity["pid"], "Synthetic fixture", "python.exe")
            assert any(w.hwnd == target.hwnd for w in backend.list_windows())
            image, bounds = backend.capture(target, foreground=False)
            assert image.width >= 700 and image.height >= 430
            results, errors = [], []
            session = CaptureSession(backend, results.append, errors.append)
            session.start(target, CaptureOptions(delay_ms=50))
            input_hook = NativeInput(session.trigger, session.manual)
            input_hook.start("Ctrl+Shift+F8")
            input_hook.stop()
            activated = backend.activate(target)
            time.sleep(.3)
            if activated:
                session.manual()
                session.stop()
                assert len(results) == 1, errors
            else:
                session.stop()
            print(json.dumps({"inventory": "pass", "window_capture": "pass", "size": image.size,
                              "hooks_and_hotkey_registration_cleanup": "pass", "manual_session": "pass" if activated else "not verified: focus denied"}))
        finally:
            if input_hook: input_hook.stop()
            if session: session.stop()
            backend.close()
            process.terminate()
            process.wait(timeout=5)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture")
    parser.add_argument("--renderer-executable", help="Verify a packaged rendering subprocess")
    args = parser.parse_args()
    if args.fixture: fixture(args.fixture)
    else: main(args.renderer_executable)
