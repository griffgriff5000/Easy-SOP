"""Local text-to-speech: pinned sherpa-onnx engine and Kokoro model fetched from their distributor after consent."""
from pathlib import Path
import hashlib,math,os,re,shutil,subprocess,tarfile,tempfile,time,unicodedata,urllib.request,uuid,wave
from .media_runtime import TrustedRedirect

RELEASES="https://github.com/k2-fsa/sherpa-onnx/releases/download/"
ENGINE_DIR="sherpa-onnx-v2.0.1-win-x64-shared-MD-Release"
MODEL_DIR="kokoro-int8-multi-lang-v1_0"
ASSETS=[
    dict(dir="engine",url=RELEASES+"v2.0.1/"+ENGINE_DIR+".tar.bz2",size=21921136,
         sha256="ce987d5bfca42c74b54f7b3bbaaa8c1febe3c5cd0fea8f94be80ea30e72f1f61",
         files=[ENGINE_DIR+"/bin/"+n for n in ("sherpa-onnx-offline-tts.exe","onnxruntime.dll","onnxruntime_providers_shared.dll")]),
    dict(dir="model",url=RELEASES+"tts-models/"+MODEL_DIR+".tar.bz2",size=132353410,
         sha256="72c347230107ef8a31098ec4d468a605244beef5f1ed00db97efa13518800653",
         files=[MODEL_DIR+"/"+n for n in ("LICENSE","README.md","lexicon-gb-en.txt","model.int8.onnx","tokens.txt","voices.bin")]),
]
# (path below the cache folder, size, sha256) of every file that is executed or read by the engine.
MANIFEST=[
    ("engine/"+ENGINE_DIR+"/bin/sherpa-onnx-offline-tts.exe",2028032,"15c7315dada3ae731819da3ff8717bae07831f3d51d02c7c4121ffd0be0a85f4"),
    ("engine/"+ENGINE_DIR+"/bin/onnxruntime.dll",17136128,"422d776ab0e3218260f7f628fcb84606aaa5c21116f720c8619a6da5e0b2e0f9"),
    ("engine/"+ENGINE_DIR+"/bin/onnxruntime_providers_shared.dll",10752,"0190137dee4933261c065c5d030c3568a68c7aa43cad942b4726a07011738bc2"),
    ("model/"+MODEL_DIR+"/LICENSE",11358,"cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"),
    ("model/"+MODEL_DIR+"/README.md",730,"87359cd32dfdff6dfeb16633b5a116aee3b9ac69dec3302378270a2cab9885b1"),
    ("model/"+MODEL_DIR+"/lexicon-gb-en.txt",6366635,"c4cbb37316f62210dff52718a7afcaae24f50c032cc75ab47ae67b831d1049e7"),
    ("model/"+MODEL_DIR+"/model.int8.onnx",114202993,"75635ea3b85a32d00094dcdd61a258aba87c160f7c264c304a7b3ae9d734195e"),
    ("model/"+MODEL_DIR+"/tokens.txt",687,"6ebb6bb288f20f3ae8d004d3c2ca27697da27c037d75e81a60e2a6a663f95425"),
    ("model/"+MODEL_DIR+"/voices.bin",28200960,"1c5a5b983d3d50d8586d437a51f3faa2da7919ce76a013c081e65671a3447c29"),
]
EXECUTABLE=MANIFEST[0][0]
DOWNLOAD_MEGABYTES=154
VOICES=[(21,"Emma","Female"),(20,"Alice","Female"),(22,"Isabella","Female"),(23,"Lily","Female"),
        (24,"Daniel","Male"),(25,"Fable","Male"),(26,"George","Male"),(27,"Lewis","Male")]
DEFAULT_VOICE=21
MAX_SCRIPT=6000
MIN_SPEED,MAX_SPEED=.5,2.0
MAX_ARCHIVE_BYTES=600*1024*1024
MAX_ARCHIVE_MEMBERS=5000
SYNTHESIS_TIMEOUT=1200
NOTICES="""Third-party speech components (downloaded on first use, not part of SOP Capture Studio)

sherpa-onnx offline TTS engine v2.0.1 - Copyright k2-fsa authors - Apache License 2.0
  https://github.com/k2-fsa/sherpa-onnx
ONNX Runtime - Copyright Microsoft Corporation - MIT License
  https://github.com/microsoft/onnxruntime
Kokoro v1.0 pretrained model (int8 multi-language package) - Apache License 2.0
  The model's own LICENSE and README are kept in the model folder beside this file.
  https://huggingface.co/hexgrad/Kokoro-82M
"""

class MissingSpeechRuntime(RuntimeError):pass

def runtime_path():
    root=Path(os.environ.get("LOCALAPPDATA",Path.home()/".local/share"))
    return root/"SOPCaptureStudio"/"SOPCaptureStudio"/"speech"/"kokoro-1.0-sherpa-2.0.1"

def _digest(path):
    with Path(path).open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()

def verify_runtime(root,manifest=None,deep=True,cancel=None):
    """True only when every manifest file exists with the pinned size (and, if deep, SHA-256)."""
    root=Path(root)
    for name,size,sha in (MANIFEST if manifest is None else manifest):
        if cancel is not None and cancel.is_set():raise RuntimeError("Speech operation cancelled.")
        path=root/name
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size!=size:return False
            if deep and _digest(path)!=sha:return False
        except OSError:return False
    return True

def installed_runtime(target=None,deep=False):
    target=Path(target) if target is not None else runtime_path()
    return target if verify_runtime(target,deep=deep) else None

_RESERVED=re.compile(r"^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(\.|$)",re.I)

def _safe_name(name):
    if not isinstance(name,str) or not name or "\\" in name or name.startswith("/") or len(name)>400:raise ValueError("Unsafe path in speech archive.")
    parts=name.rstrip("/").split("/")
    for part in parts:
        if (not part or part in (".","..") or any(c in part for c in ':<>"|?*' ) or any(ord(c)<32 for c in part)
                or part.endswith((" ",".")) or _RESERVED.match(part)):raise ValueError("Unsafe path in speech archive.")
    return parts

def extract_archive(stream,destination,allowed=None,cancel=None):
    """Extract regular files from a .tar.bz2 stream; reject links, devices, unsafe paths and oversized archives.
    Files outside `allowed` (when given) are validated but not written."""
    destination=Path(destination).resolve();destination.mkdir(parents=True,exist_ok=True)
    allowed=None if allowed is None else set(allowed);total=0;count=0;written=set()
    with tarfile.open(fileobj=stream,mode="r|bz2") as archive:
        for member in archive:
            if cancel is not None and cancel.is_set():raise RuntimeError("Speech operation cancelled.")
            count+=1;parts=_safe_name(member.name)
            if count>MAX_ARCHIVE_MEMBERS:raise ValueError("Speech archive has too many files.")
            if member.isdir():continue
            if not member.isreg() or member.size<0:raise ValueError("Speech archive contains a link or special file.")
            total+=member.size
            if total>MAX_ARCHIVE_BYTES:raise ValueError("Speech archive is larger than expected.")
            if allowed is not None and "/".join(parts) not in allowed:continue
            target=destination.joinpath(*parts)
            if not target.resolve().is_relative_to(destination):raise ValueError("Unsafe path in speech archive.")
            target.parent.mkdir(parents=True,exist_ok=True)
            try:
                with archive.extractfile(member) as source,target.open("xb") as output:
                    while True:
                        if cancel is not None and cancel.is_set():raise RuntimeError("Speech operation cancelled.")
                        chunk=source.read(1024*1024)
                        if not chunk:break
                        output.write(chunk)
            except FileExistsError as exc:raise ValueError("Duplicate path in speech archive.") from exc
            written.add("/".join(parts))
    return written

def _replace_directory(staging,target):
    backup=target.with_name(target.name+".old-"+uuid.uuid4().hex)
    had=target.exists()
    if had:os.replace(target,backup)
    try:os.replace(staging,target)
    except OSError:
        if had:os.replace(backup,target)
        raise
    if had:shutil.rmtree(backup,ignore_errors=True)

def install_runtime(*,target=None,cancel=None,progress=lambda value:None,opener=None,manifest=None):
    target=Path(target) if target is not None else runtime_path()
    target.parent.mkdir(parents=True,exist_ok=True)
    def check():
        if cancel is not None and cancel.is_set():raise RuntimeError("Speech download cancelled.")
    check()
    opener=opener or urllib.request.build_opener(TrustedRedirect()).open
    grand=sum(a["size"] for a in ASSETS);done=0
    staging=Path(tempfile.mkdtemp(prefix=".speech-install-",dir=target.parent))
    try:
        for index,asset in enumerate(ASSETS):
            archive=staging/f"download-{index}.tar.bz2";total=0;digest=hashlib.sha256()
            request=urllib.request.Request(asset["url"],headers={"User-Agent":"SOPCaptureStudio"})
            with opener(request,timeout=30) as response,archive.open("wb") as output:
                while True:
                    check();chunk=response.read(1024*1024)
                    if not chunk:break
                    total+=len(chunk)
                    if total>asset["size"]:raise ValueError("Speech download exceeds expected size.")
                    digest.update(chunk);output.write(chunk);progress(min(90,(done+total)*90//grand))
            if total!=asset["size"] or digest.hexdigest()!=asset["sha256"]:raise ValueError("Speech download checksum mismatch; nothing was installed.")
            done+=total;check()
            with archive.open("rb") as stream:
                try:extract_archive(stream,staging/asset.get("dir",f"asset{index}"),asset.get("files"),cancel)
                except RuntimeError:raise RuntimeError("Speech download cancelled.") from None
            archive.unlink()
        check()
        if not verify_runtime(staging,manifest,cancel=cancel):raise ValueError("Speech files failed verification; nothing was installed.")
        (staging/"THIRD-PARTY-NOTICES.txt").write_text(NOTICES,encoding="utf-8")
        check();_replace_directory(staging,target);progress(100)
    finally:shutil.rmtree(staging,ignore_errors=True)
    return target

def validate_script(text,voice,speed):
    if not isinstance(text,str):raise ValueError("Enter a narration script.")
    text=" ".join(text.split())
    if not text:raise ValueError("Enter a narration script.")
    if len(text)>MAX_SCRIPT:raise ValueError(f"Use up to {MAX_SCRIPT:,} characters per section narration.")
    if any(unicodedata.category(c)=="Cc" for c in text):raise ValueError("The script contains unsupported control characters.")
    if text.startswith("-"):raise ValueError("Start the script with a word, not a dash.")
    if isinstance(voice,bool) or voice not in {v[0] for v in VOICES}:raise ValueError("Choose one of the listed British English voices.")
    if isinstance(speed,bool) or not isinstance(speed,(int,float)) or not math.isfinite(speed) or not MIN_SPEED<=speed<=MAX_SPEED:
        raise ValueError(f"Choose a speaking speed from {MIN_SPEED:g} to {MAX_SPEED:g}.")
    return text

def arguments(root,text,voice,speed,output):
    """Command line for sherpa-onnx-offline-tts (flags checked against `--help` of v2.0.1)."""
    model=Path(root)/"model"/MODEL_DIR
    return [str(Path(root)/EXECUTABLE),f"--kokoro-model={model/'model.int8.onnx'}",f"--kokoro-voices={model/'voices.bin'}",
        f"--kokoro-tokens={model/'tokens.txt'}",f"--kokoro-lexicon={model/'lexicon-gb-en.txt'}",
        f"--sid={voice}",f"--speed={speed:g}","--num-threads=2",f"--output-filename={output}",text]

def wav_duration(path):
    try:
        with wave.open(str(path),"rb") as audio:
            rate,frames=audio.getframerate(),audio.getnframes()
            if audio.getnchannels() not in (1,2) or audio.getsampwidth()!=2 or not 8000<=rate<=96000 or frames<=0:raise ValueError
            duration=frames/rate
            if duration>3600:raise ValueError
            audio.readframes(min(frames,rate))
            return duration
    except (wave.Error,EOFError,OSError,ValueError) as exc:raise ValueError("The speech engine produced an unusable audio file.") from exc

def synthesize(text,voice,speed,output,*,cancel=None,target=None,progress=None):
    """Render narration to `output` (a WAV) and return its duration. Existing output is only replaced by a valid result."""
    text=validate_script(text,voice,speed);output=Path(output)
    def check():
        if cancel is not None and cancel.is_set():raise RuntimeError("Speech generation cancelled.")
    check()
    root=Path(target) if target is not None else runtime_path()
    if not (root/EXECUTABLE).is_file():raise MissingSpeechRuntime("Speech files are not installed yet.")
    try:ready=verify_runtime(root,cancel=cancel)
    except RuntimeError:raise RuntimeError("Speech generation cancelled.") from None
    if not ready:raise MissingSpeechRuntime("The installed speech files are damaged or incomplete. Download them again.")
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_name("."+output.stem+"."+uuid.uuid4().hex+".tmp.wav")
    flags=getattr(subprocess,"CREATE_NO_WINDOW",0)
    try:
        process=subprocess.Popen(arguments(root,text,voice,speed,temporary),cwd=str((root/EXECUTABLE).parent),
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=flags,shell=False)
        started=time.monotonic();log=b""
        try:
            while True:
                try:log,_=process.communicate(timeout=.2);break
                except subprocess.TimeoutExpired:
                    if cancel is not None and cancel.is_set():raise RuntimeError("Speech generation cancelled.")
                    if time.monotonic()-started>SYNTHESIS_TIMEOUT:raise RuntimeError("Speech generation took too long and was stopped.")
        except BaseException:
            process.kill();process.communicate();raise
        if process.returncode!=0:raise RuntimeError("The speech engine failed: "+log.decode("utf-8","replace").strip()[-300:])
        duration=wav_duration(temporary);check()
        os.replace(temporary,output)
        if progress:progress(100)
        return duration
    finally:temporary.unlink(missing_ok=True)
