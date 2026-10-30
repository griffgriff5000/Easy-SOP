import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import zipfile

import pytest

spec = importlib.util.spec_from_file_location('package_installer', Path(__file__).parents[1] / 'scripts/package_installer.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def payload(tmp_path, version='0.3.0'):
    archive = tmp_path / 'SOPCaptureStudio-0.3.0-Windows-x64.zip'
    with zipfile.ZipFile(archive, 'w') as bundle:
        for name, data in {'SOPCaptureStudio.exe': b'app', 'SOPCaptureUpdater.exe': b'helper',
                           '_internal/runtime.dll': b'runtime', 'RELEASE.json': json.dumps({'app': 'SOPCaptureStudio', 'version': version})}.items():
            bundle.writestr('SOPCaptureStudio/' + name, data)
    archive.with_suffix('.zip.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name + '\n')
    return archive


def test_installer_compiles_verified_complete_payload_and_hashes_result(tmp_path, monkeypatch):
    archive = payload(tmp_path)
    def compile(args, **kwargs):
        values = dict(arg[2:].split('=', 1) for arg in args if arg.startswith('/D'))
        app = Path(values['PayloadDir'])
        assert (app / 'SOPCaptureUpdater.exe').read_bytes() == b'helper'
        assert (app / '_internal/runtime.dll').is_file()
        assert values['AppVersion'] == '0.3.0'
        output = Path(values['OutputDir']) / 'SOPCaptureStudio-0.3.0-Windows-x64-Setup.exe'
        output.write_bytes(b'compiled setup')
        return subprocess.CompletedProcess(args, 0)
    monkeypatch.setattr(module.subprocess, 'run', compile)
    setup, checksum = module.build_installer(archive, tmp_path / 'ISCC.exe', tmp_path / 'output with spaces')
    assert checksum.read_text().strip() == hashlib.sha256(setup.read_bytes()).hexdigest() + '  ' + setup.name


@pytest.mark.parametrize('damage', ['checksum', 'version', 'missing-helper'])
def test_installer_rejects_invalid_payload_before_compiling(tmp_path, monkeypatch, damage):
    archive = payload(tmp_path, '0.2.0' if damage == 'version' else '0.3.0')
    if damage == 'checksum':
        archive.with_suffix('.zip.sha256').write_text('0' * 64 + '  ' + archive.name)
    if damage == 'missing-helper':
        with zipfile.ZipFile(archive) as source:
            data = {n: source.read(n) for n in source.namelist() if not n.endswith('SOPCaptureUpdater.exe')}
        with zipfile.ZipFile(archive, 'w') as target:
            for n, value in data.items(): target.writestr(n, value)
        archive.with_suffix('.zip.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name)
    def unexpected(*args, **kwargs): pytest.fail('Compiler must not run for invalid payload')
    monkeypatch.setattr(module.subprocess, 'run', unexpected)
    with pytest.raises(ValueError): module.build_installer(archive, tmp_path / 'ISCC.exe', tmp_path / 'output')


def test_compiler_failure_does_not_leave_stale_installer_checksum(tmp_path, monkeypatch):
    archive = payload(tmp_path)
    output = tmp_path / 'output'; output.mkdir()
    setup = output / 'SOPCaptureStudio-0.3.0-Windows-x64-Setup.exe'
    setup.write_bytes(b'old'); setup.with_suffix('.exe.sha256').write_text('old')
    def fail(*args, **kwargs): raise subprocess.CalledProcessError(1, args[0])
    monkeypatch.setattr(module.subprocess, 'run', fail)
    with pytest.raises(subprocess.CalledProcessError): module.build_installer(archive, tmp_path / 'ISCC.exe', output)
    assert not setup.exists()
    assert not setup.with_suffix('.exe.sha256').exists()
