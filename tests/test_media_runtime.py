import hashlib,io,threading,zipfile
import pytest
from sop_capture import media_runtime as runtime


def fixture(monkeypatch):
    binary=b"MZ verified test exporter"
    data=io.BytesIO()
    with zipfile.ZipFile(data,"w") as z:z.writestr("ffmpeg/bin/ffmpeg.exe",binary)
    archive=data.getvalue()
    monkeypatch.setattr(runtime,"ARCHIVE_SIZE",len(archive))
    monkeypatch.setattr(runtime,"ARCHIVE_SHA256",hashlib.sha256(archive).hexdigest())
    monkeypatch.setattr(runtime,"BINARY_SIZE",len(binary))
    monkeypatch.setattr(runtime,"BINARY_SHA256",hashlib.sha256(binary).hexdigest())
    return archive,binary


def test_installs_only_verified_binary(monkeypatch,tmp_path):
    archive,binary=fixture(monkeypatch);target=tmp_path/"tool.exe";progress=[]
    result=runtime.install_runtime(target=target,opener=lambda *a,**kw:io.BytesIO(archive),progress=progress.append)
    assert result==target and target.read_bytes()==binary
    assert runtime.installed_runtime(target)==target
    assert progress[-1]==100
    target.write_bytes(b"tampered")
    assert runtime.installed_runtime(target) is None


def test_failure_and_cancel_keep_previous_binary(monkeypatch,tmp_path):
    archive,_=fixture(monkeypatch);target=tmp_path/"tool.exe";target.write_bytes(b"previous")
    with pytest.raises(ValueError,match="checksum"):
        runtime.install_runtime(target=target,opener=lambda *a,**kw:io.BytesIO(b"x"*len(archive)))
    cancelled=threading.Event();cancelled.set()
    with pytest.raises(RuntimeError,match="cancelled"):
        runtime.install_runtime(target=target,cancel=cancelled,opener=lambda *a,**kw:io.BytesIO(archive))
    assert target.read_bytes()==b"previous"
    assert list(tmp_path.iterdir())==[target]


def test_redirects_reject_untrusted_hosts():
    import urllib.request
    handler=runtime.TrustedRedirect()
    with pytest.raises(ValueError):
        handler.redirect_request(urllib.request.Request(runtime.URL),None,302,"",{},"https://evil.example/tool.exe")
    with pytest.raises(ValueError):
        handler.redirect_request(urllib.request.Request(runtime.URL),None,302,"",{},"http://github.com/tool.exe")


def test_frozen_export_requires_verified_runtime(monkeypatch):
    from sop_capture import media_export
    monkeypatch.setattr(runtime,"installed_runtime",lambda:None)
    monkeypatch.setattr(media_export.sys,"frozen",True,raising=False)
    with pytest.raises(runtime.MissingMediaRuntime):media_export.ffmpeg_executable()
