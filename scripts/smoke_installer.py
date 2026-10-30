"""Install/update/uninstall an isolated copy using unique test-only shortcuts."""
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sop_capture.updates import stage_archive
from sop_capture.update_install import prepare_handoff
from smoke_updater import close_test_app

ROOT = Path(__file__).resolve().parents[1]


def run(archive, compiler):
    import win32com.client
    shell = win32com.client.Dispatch('WScript.Shell')
    name = 'SOP Installer Test ' + uuid.uuid4().hex
    app_id = '{' + str(uuid.uuid4()).upper() + '}'
    links = [Path(shell.SpecialFolders('Desktop')) / (name + '.lnk'),
             Path(shell.SpecialFolders('Programs')) / name / (name + '.lnk')]
    with zipfile.ZipFile(archive) as bundle:
        version = json.loads(bundle.read('SOPCaptureStudio/RELEASE.json'))['version']
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    with TemporaryDirectory(prefix='sop-setup-smoke-') as temporary:
        root = Path(temporary).resolve()
        payload = stage_archive(archive, digest, root / 'payload', version)
        # Unique AppId prevents touching any real user's uninstall registration.
        subprocess.run([str(compiler), '/Qp', f'/DAppVersion={version}',
                        f'/DPayloadDir={payload}', f'/DOutputDir={root}',
                        f'/DShortcutName={name}', f'/DApplicationId={app_id}',
                        str(ROOT / 'packaging/windows/SOPCaptureStudio.iss')], check=True)
        setup = root / f'SOPCaptureStudio-{version}-Windows-x64-Setup.exe'
        install = root / 'Installed with spaces'
        app = install / 'App'
        uninstall = install / 'unins000.exe'
        personal = Path(os.environ['LOCALAPPDATA']) / 'SOPCaptureStudio/SOPCaptureStudio' / (name + '.sentinel')
        personal.parent.mkdir(parents=True, exist_ok=True)
        personal.write_text('personal data stays here')
        try:
            # No /TASKS override: prove desktop task is selected by default.
            subprocess.run([str(setup), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                            f'/DIR={install}', f'/LOG={root / "install.log"}'], check=True, timeout=90)
            assert uninstall.is_file()
            import winreg
            registry_path = 'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\' + app_id + '_is1'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                assert winreg.QueryValueEx(key, 'DisplayVersion')[0] == version
            for link in links:
                assert link.is_file(), link
                shortcut = shell.CreateShortcut(str(link))
                assert Path(shortcut.TargetPath).resolve() == (app / 'SOPCaptureStudio.exe').resolve()
                assert Path(shortcut.WorkingDirectory).resolve() == app.resolve()
                icon_file, icon_index = shortcut.IconLocation.rsplit(',', 1)
                assert Path(icon_file).resolve() == (app / 'SOPCaptureStudio.exe').resolve()
                assert int(icon_index) == 0
                folder = win32com.client.Dispatch('Shell.Application').NameSpace(str(link.parent))
                assert folder.ParseName(link.name).ExtendedProperty('System.AppUserModel.ID') == 'SOPCaptureStudio.Desktop'
            assert (app / 'SOPCaptureUpdater.exe').is_file()
            print('Installer: per-user payload, default Desktop and Start menu links passed', flush=True)

            # Exercise the production updater against the actual installed App folder.
            (app / 'RELEASE.json').write_text(json.dumps({'app': 'SOPCaptureStudio', 'version': '0.2.0'}))
            job = root / 'job'; job.mkdir()
            update = job / archive.name; shutil.copy2(archive, update)
            (job / 'checksum.txt').write_text(digest + '  ' + archive.name + '\n')
            staged = stage_archive(update, digest, job / 'staged', version)
            parent = subprocess.Popen([str(app / 'SOPCaptureStudio.exe'), '--smoke-test'], creationflags=subprocess.CREATE_NO_WINDOW)
            plan, runner, token = prepare_handoff(staged, app, '0.2.0', version, parent.pid)
            data = json.loads(plan.read_text()); data['quiet'] = True; plan.write_text(json.dumps(data))
            helper = subprocess.Popen([str(runner), '--plan', str(plan)], creationflags=subprocess.CREATE_NO_WINDOW)
            (job / 'confirmed.json').write_text(json.dumps({'token': token}))
            parent.wait(timeout=40); helper.wait(timeout=150)
            result = json.loads((job / 'result.json').read_text())
            try:
                assert result['status'] == 'updated', result
                assert uninstall.is_file()
                assert Path(result['backup']).parent == install
                for link in links:
                    assert Path(shell.CreateShortcut(str(link)).TargetPath).is_file()
            finally:
                close_test_app(result.get('pid') or result.get('restarted_pid'))
            print('Installer: real update retained shortcut targets and uninstall records', flush=True)

            sentinel = app / 'personal-not-installed.txt'; sentinel.write_text('keep me')
            subprocess.run([str(setup), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                            f'/DIR={install}', f'/LOG={root / "reinstall.log"}'], check=True, timeout=90)
            assert sentinel.read_text() == 'keep me'
            assert uninstall.is_file()
            for link in links:
                assert Path(shell.CreateShortcut(str(link)).TargetPath).resolve() == (app / 'SOPCaptureStudio.exe').resolve()
            print('Installer: reinstall after updating preserved shortcut targets and personal file', flush=True)
            subprocess.run([str(uninstall), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                            f'/LOG={root / "uninstall.log"}'], check=True, timeout=90)
            deadline = time.monotonic() + 30
            while uninstall.exists() and time.monotonic() < deadline: time.sleep(.2)
            assert sentinel.read_text() == 'keep me'
            assert not (app / 'SOPCaptureStudio.exe').exists()
            assert all(not link.exists() for link in links)
            assert not uninstall.exists()
            assert personal.read_text() == 'personal data stays here'
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            except FileNotFoundError:
                pass
            else:
                key.Close()
                raise AssertionError('Test uninstall registration was retained')
            print('Installer: uninstall removed installed files/links and preserved personal sentinel', flush=True)
        finally:
            if uninstall.exists():
                subprocess.run([str(uninstall), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'], timeout=90, check=True)
                time.sleep(1)
            # Only unique shortcut names generated above; never touch real app shortcuts.
            for link in links:
                link.unlink(missing_ok=True)
            if links[1].parent.exists(): links[1].parent.rmdir()
            personal.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--compiler', type=Path, required=True)
    args = parser.parse_args()
    run(args.archive.resolve(), args.compiler.resolve())
