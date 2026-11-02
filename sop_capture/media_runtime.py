"""Optional export engine fetched directly from its distributor after consent."""
from pathlib import Path
import hashlib,os,tempfile,zipfile,urllib.request
from urllib.parse import urlsplit

URL="https://github.com/GyanD/codexffmpeg/releases/download/9.0.2/ffmpeg-9.0.2-essentials_build.zip"
ARCHIVE_SIZE=114768076
ARCHIVE_SHA256="60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba"
BINARY_SIZE=105423872
BINARY_SHA256="3256173f3f8bffd7df12227c68adf68025edb1832273a9530688a7bb1ed8edec"

class MissingMediaRuntime(RuntimeError):pass

class TrustedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        url=urlsplit(newurl)
        if url.scheme!="https" or url.hostname not in {"github.com","release-assets.githubusercontent.com","objects.githubusercontent.com","github-releases.githubusercontent.com"} or url.username or url.password:
            raise ValueError("Untrusted video tool download redirect.")
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def runtime_path():
    root=Path(os.environ.get("LOCALAPPDATA",Path.home()/".local/share"))
    return root/"SOPCaptureStudio"/"SOPCaptureStudio"/"media-tools"/"ffmpeg-9.0.2.exe"

def _digest(path):
    with Path(path).open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()

def installed_runtime(target=None):
    target=Path(target) if target is not None else runtime_path()
    try:
        if target.stat().st_size==BINARY_SIZE and _digest(target)==BINARY_SHA256:return target
    except OSError:pass
    return None

def install_runtime(*,target=None,cancel=None,progress=lambda value:None,opener=None):
    target=Path(target) if target is not None else runtime_path()
    target.parent.mkdir(parents=True,exist_ok=True)
    def check():
        if cancel is not None and cancel.is_set():raise RuntimeError("Video tool download cancelled.")
    check()
    opener=opener or urllib.request.build_opener(TrustedRedirect()).open
    with tempfile.TemporaryDirectory(prefix=".video-tool-",dir=target.parent) as directory:
        archive=Path(directory)/"download.zip";total=0;digest=hashlib.sha256()
        request=urllib.request.Request(URL,headers={"User-Agent":"SOPCaptureStudio"})
        with opener(request,timeout=30) as response,archive.open("wb") as output:
            while True:
                check();chunk=response.read(1024*1024)
                if not chunk:break
                total+=len(chunk)
                if total>ARCHIVE_SIZE:raise ValueError("Video tool download exceeds expected size.")
                digest.update(chunk);output.write(chunk);progress(min(90,total*90//ARCHIVE_SIZE))
        if total!=ARCHIVE_SIZE or digest.hexdigest()!=ARCHIVE_SHA256:raise ValueError("Video tool archive checksum mismatch.")
        check();binary=Path(directory)/"ffmpeg.exe"
        with zipfile.ZipFile(archive) as bundle:
            members=[item for item in bundle.infolist() if item.filename.endswith("/bin/ffmpeg.exe")]
            if len(members)!=1 or members[0].file_size!=BINARY_SIZE:raise ValueError("Unexpected video tool archive contents.")
            with bundle.open(members[0]) as source,binary.open("wb") as output:
                while True:
                    check();chunk=source.read(1024*1024)
                    if not chunk:break
                    output.write(chunk)
        if installed_runtime(binary) is None:raise ValueError("Video tool executable checksum mismatch.")
        check();binary.replace(target);progress(100)
    return target
