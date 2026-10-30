"""Exercise the real install button handoff inside the frozen main executable."""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import multiprocessing as mp
import multiprocessing.spawn
import shutil
import sys
import textwrap
import time
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sop_capture.updates import stage_archive
from smoke_updater import close_test_app


def exercise(archive, root, rollback=False):
    root.mkdir()
    with zipfile.ZipFile(archive) as bundle:
        version = json.loads(bundle.read('SOPCaptureStudio/RELEASE.json'))['version']
    with archive.open('rb') as stream:
        original_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    installed = stage_archive(archive, original_hash, root / 'original', version)
    previous = '0.3.1'
    assert tuple(map(int, version.split('.'))) > (0, 3, 1)
    (installed / 'RELEASE.json').write_text(json.dumps({'app': 'SOPCaptureStudio', 'version': previous}))
    job = root / 'job'; job.mkdir(); payload = job / archive.name
    if rollback:
        with zipfile.ZipFile(archive) as source, zipfile.ZipFile(payload, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as target:
            for item in source.infolist():
                target.writestr(item, b'invalid executable' if item.filename == 'SOPCaptureStudio/SOPCaptureStudio.exe' else source.read(item))
    else:
        shutil.copy2(archive, payload)
    with payload.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    (job / 'checksum.txt').write_text(digest + '  ' + payload.name)
    staged = stage_archive(payload, digest, job / 'staged', version)
    executable = str(installed / 'SOPCaptureStudio.exe')
    mp.set_executable(executable)
    mp.spawn.get_command_line = lambda **kw: [executable, '--multiprocessing-fork', *[f'{key}={value}' for key,value in kw.items()]]
    code = f'''
import sys,json,traceback
from pathlib import Path
from PySide6.QtCore import QStandardPaths,QTimer
from PySide6.QtWidgets import QApplication,QMessageBox
import sop_capture
from sop_capture.ui.main_window import MainWindow
import sop_capture.update_install as update_install
assert sys.frozen and Path(sys.executable).resolve()==Path({executable!r}).resolve()
sop_capture.__version__={previous!r}
QStandardPaths.setTestModeEnabled(True)
app=QApplication([])
app.setOrganizationName('SOPCaptureStudioUpdateSmoke')
app.setApplicationName('SOPCaptureStudioUpdateSmoke')
window=MainWindow();window.show()
QMessageBox.question=lambda *args,**kwargs: QMessageBox.StandardButton.Yes
original_prepare=update_install.prepare_handoff
def prepare_quiet(*args,**kwargs):
    result=original_prepare(*args,**kwargs)
    plan=json.loads(result[0].read_text());plan['quiet']=True;result[0].write_text(json.dumps(plan))
    return result
update_install.prepare_handoff=prepare_quiet
import subprocess
original_popen=subprocess.Popen
def record_helper(*args,**kwargs):
    result=original_popen(*args,**kwargs)
    Path({str(root/'helper-pid.txt')!r}).write_text(str(result.pid))
    return result
subprocess.Popen=record_helper
def install():
    try:
        assert window.install_update(Path({str(staged)!r}),{version!r})
        Path({str(root/'handoff-passed.txt')!r}).write_text('passed')
    except BaseException:
        Path({str(root/'failure.txt')!r}).write_text(traceback.format_exc())
        app.quit()
QTimer.singleShot(200,install)
app.exec()
'''
    process = mp.get_context('spawn').Process(target=exec, args=(textwrap.dedent(code), {'__name__': '__update_smoke__'}))
    process.start(); process.join(60)
    assert not process.is_alive(), 'Frozen main app did not close'
    assert process.exitcode == 0
    assert (root / 'handoff-passed.txt').exists(), (root / 'failure.txt').read_text() if (root / 'failure.txt').exists() else 'Handoff did not run'
    result_path = job / 'result.json'; deadline = time.monotonic() + 150
    while not result_path.exists() and time.monotonic() < deadline: time.sleep(.2)
    assert result_path.exists(), 'External helper did not complete'
    result = json.loads(result_path.read_text())
    try:
        assert result['status'] == ('rolled-back' if rollback else 'updated'), result
        assert (job / 'confirmed.json').is_file()
    finally:
        close_test_app(result.get('pid') or result.get('restarted_pid'))
        close_test_app(int((root / 'helper-pid.txt').read_text()))
    print('Frozen main app install button:', result['status'], 'passed', flush=True)


def main():
    preparation = mp.spawn.get_preparation_data
    def frozen_preparation(name):
        data = preparation(name)
        for key in ('sys_path', 'init_main_from_name', 'init_main_from_path'): data.pop(key, None)
        return data
    mp.spawn.get_preparation_data = frozen_preparation
    archive = Path(sys.argv[1]).resolve()
    with TemporaryDirectory(prefix='sop-frozen-update-') as temporary:
        root = Path(temporary).resolve()
        exercise(archive, root / 'success')
        exercise(archive, root / 'rollback', rollback=True)


if __name__ == '__main__': main()
