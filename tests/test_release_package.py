import importlib.util
from pathlib import Path
import zipfile
import pytest
import tomllib

spec=importlib.util.spec_from_file_location('package_release',Path(__file__).parents[1]/'scripts/package_release.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_release_archive_contains_complete_folder_and_no_private_data(tmp_path,monkeypatch):
    build=tmp_path/'build';(build/'_internal').mkdir(parents=True);(build/'SOPCaptureStudio.exe').write_bytes(b'exe');(build/'SOPCaptureUpdater.exe').write_bytes(b'helper');(build/'_internal/runtime.dll').write_bytes(b'dll')
    monkeypatch.setattr(module,'RUNTIME',())
    archive,checksum=module.package(build,tmp_path/'output','0.1.0')
    with zipfile.ZipFile(archive) as package:
        assert 'SOPCaptureStudio/_internal/runtime.dll' in package.namelist()
        assert 'SOPCaptureStudio/START_HERE.txt' in package.namelist()
        import json
        assert json.loads(package.read('SOPCaptureStudio/RELEASE.json'))=={'app':'SOPCaptureStudio','version':'0.1.0'}
        assert package.testzip() is None
    assert archive.name in checksum.read_text()
    (build/'project.json').write_text('{}')
    with pytest.raises(ValueError,match='Private application data'):module.package(build,tmp_path/'output','0.1.0')


def test_install_metadata_declares_pdf_import_dependency():
    data=tomllib.loads((Path(__file__).parents[1]/'pyproject.toml').read_text())
    assert any(item.startswith('pdfplumber') for item in data['project']['dependencies'])
    from sop_capture import __version__
    assert data['project']['version']==__version__
