import io,tarfile,hashlib,threading,wave,subprocess
import pytest
from sop_capture import speech_runtime as speech


def archive(name,data=b'file'):
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w:bz2') as out:
        member=tarfile.TarInfo(name);member.size=len(data);out.addfile(member,io.BytesIO(data))
    return stream.getvalue()


def test_safe_archive_rejects_traversal_links_and_windows_aliases(tmp_path):
    for name in ('../outside','/absolute','model/../../outside','C:/escape','model/NUL','model/file.','model/file:ads','model/one\\two'):
        with pytest.raises(ValueError):speech.extract_archive(io.BytesIO(archive(name)),tmp_path)
    data=io.BytesIO()
    with tarfile.open(fileobj=data,mode='w:bz2') as out:
        member=tarfile.TarInfo('model/link');member.type=tarfile.SYMTYPE;member.linkname='../outside';out.addfile(member)
    data.seek(0)
    with pytest.raises(ValueError):speech.extract_archive(data,tmp_path)


def test_install_verifies_hash_and_preserves_previous_cache_on_failure(tmp_path,monkeypatch):
    data=archive('model/file');asset={'url':'https://github.com/original/archive','size':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    monkeypatch.setattr(speech,'ASSETS',[asset]);target=tmp_path/'voices';target.mkdir();(target/'previous.txt').write_text('keep')
    with pytest.raises(ValueError,match='checksum'):
        speech.install_runtime(target=target,opener=lambda *a,**k:io.BytesIO(b'x'*len(data)))
    assert (target/'previous.txt').read_text()=='keep'
    cancel=threading.Event();cancel.set()
    with pytest.raises(RuntimeError,match='cancelled'):
        speech.install_runtime(target=target,cancel=cancel,opener=lambda *a,**k:io.BytesIO(data))
    assert (target/'previous.txt').read_text()=='keep'


def test_script_voice_and_speed_are_bounded():
    assert speech.validate_script('  Open the project.  ',21,1)=='Open the project.'
    for text,voice,speed in [('',21,1),('x'*6001,21,1),('Open',999,1),('Open',21,float('nan')),('Open',21,.1)]:
        with pytest.raises(ValueError):speech.validate_script(text,voice,speed)


def test_cli_arguments_use_british_lexicon_and_argument_list(tmp_path):
    args=speech.arguments(tmp_path,'Click "Open" and continue.',21,.9,tmp_path/'out.wav')
    assert args[-1]=='Click "Open" and continue.'
    assert '--sid=21' in args and '--speed=0.9' in args
    assert any('lexicon-gb-en.txt' in a for a in args)


def test_cancelled_synthesis_does_not_replace_existing_file(tmp_path):
    target=tmp_path/'existing.wav';target.write_bytes(b'previous');cancel=threading.Event();cancel.set()
    with pytest.raises(RuntimeError,match='cancelled'):speech.synthesize('Test phrase.',21,1,target,cancel=cancel)
    assert target.read_bytes()==b'previous'


def test_install_success_replaces_cache_and_keeps_licence_files(tmp_path,monkeypatch):
    data=archive('model/file',b'voice');asset={'url':'https://github.com/original/archive','size':len(data),'sha256':hashlib.sha256(data).hexdigest(),'dir':'model','files':['model/file']}
    monkeypatch.setattr(speech,'ASSETS',[asset]);target=tmp_path/'voices';target.mkdir();(target/'previous.txt').write_text('old')
    manifest=[('model/model/file',5,hashlib.sha256(b'voice').hexdigest())];seen=[]
    speech.install_runtime(target=target,manifest=manifest,progress=seen.append,opener=lambda *a,**k:io.BytesIO(data))
    assert (target/'model/model/file').read_bytes()==b'voice' and not (target/'previous.txt').exists()
    assert 'Apache' in (target/'THIRD-PARTY-NOTICES.txt').read_text() and seen[-1]==100
    assert not [p for p in tmp_path.iterdir() if p.name.startswith('.speech')] and len(list(tmp_path.iterdir()))==1


def test_install_failed_verification_or_unsafe_archive_preserves_cache(tmp_path,monkeypatch):
    target=tmp_path/'voices';target.mkdir();(target/'previous.txt').write_text('keep')
    for data,manifest,error in [(archive('model/file',b'voice'),[('model/model/other',5,'0'*64)],'verification'),(archive('../x'),[],'Unsafe')]:
        asset={'url':'https://github.com/original/archive','size':len(data),'sha256':hashlib.sha256(data).hexdigest(),'dir':'model'}
        monkeypatch.setattr(speech,'ASSETS',[asset])
        with pytest.raises(ValueError,match=error):speech.install_runtime(target=target,manifest=manifest,opener=lambda *a,**k:io.BytesIO(data))
        assert (target/'previous.txt').read_text()=='keep' and len(list(tmp_path.iterdir()))==1


def test_archive_size_and_duplicate_limits(tmp_path,monkeypatch):
    monkeypatch.setattr(speech,'MAX_ARCHIVE_BYTES',3)
    with pytest.raises(ValueError,match='larger'):speech.extract_archive(io.BytesIO(archive('a/file',b'1234')),tmp_path)
    monkeypatch.setattr(speech,'MAX_ARCHIVE_BYTES',100)
    assert speech.extract_archive(io.BytesIO(archive('a/file',b'1234')),tmp_path,allowed={'a/other'})==set() and not (tmp_path/'a/file').exists()


def test_runtime_integrity_requires_exact_files(tmp_path):
    (tmp_path/'f').write_bytes(b'abc');good=[('f',3,hashlib.sha256(b'abc').hexdigest())]
    assert speech.verify_runtime(tmp_path,good) and not speech.verify_runtime(tmp_path,[('f',3,'0'*64)])
    assert speech.verify_runtime(tmp_path,[('f',3,'0'*64)],deep=False) and not speech.verify_runtime(tmp_path,[('missing',1,'0')])


def test_voice_catalogue_and_text_edge_cases():
    assert [v[0] for v in speech.VOICES][0]==speech.DEFAULT_VOICE==21 and sorted(v[0] for v in speech.VOICES)==list(range(20,28))
    assert speech.validate_script('One\ntwo\tthree',24,1.25)=='One two three'
    for text in ('--help','\x00a'):
        with pytest.raises(ValueError):speech.validate_script(text,21,1)
    for voice in (True,'21',None):
        with pytest.raises(ValueError):speech.validate_script('Open',voice,1)
    with pytest.raises(ValueError):speech.validate_script('Open',21,True)


class FakeProcess:
    def __init__(self,args,behaviour,**kwargs):
        self.args=args;self.behaviour=behaviour;self.kwargs=kwargs;self.returncode=0;self.killed=False
    def communicate(self,timeout=None):
        out=[a.split('=',1)[1] for a in self.args if a.startswith('--output-filename=')][0]
        return self.behaviour(self,out)
    def kill(self):self.killed=True


def prepare(tmp_path,monkeypatch,behaviour):
    exe=tmp_path/speech.EXECUTABLE;exe.parent.mkdir(parents=True);exe.write_bytes(b'x');monkeypatch.setattr(speech,'verify_runtime',lambda *a,**k:True)
    made=[];monkeypatch.setattr(speech.subprocess,'Popen',lambda args,**kw:made.append(FakeProcess(args,behaviour,**kw)) or made[-1]);return made


def write_wave(path,seconds=1,rate=24000):
    with wave.open(path,'wb') as out:out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate);out.writeframes(b'\x01\x00'*int(rate*seconds))


def test_synthesis_runs_without_shell_validates_and_replaces_atomically(tmp_path,monkeypatch):
    def ok(process,out):write_wave(out,1.5);return b'',None
    made=prepare(tmp_path,monkeypatch,ok);target=tmp_path/'out.wav';target.write_bytes(b'previous')
    assert speech.synthesize('Open the project.',24,1,target,target=tmp_path)==pytest.approx(1.5)
    assert made[0].kwargs['shell'] is False and made[0].kwargs['stdin']==subprocess.DEVNULL and made[0].kwargs['creationflags']==subprocess.CREATE_NO_WINDOW
    assert speech.wav_duration(target)==pytest.approx(1.5) and not [p for p in tmp_path.glob('.*.tmp.wav')]


def test_failed_or_invalid_synthesis_never_overwrites_existing_narration(tmp_path,monkeypatch):
    target=tmp_path/'out.wav';target.write_bytes(b'previous')
    def fail(process,out):process.returncode=3;return b'bad model',None
    prepare(tmp_path,monkeypatch,fail)
    with pytest.raises(RuntimeError,match='bad model'):speech.synthesize('Open.',21,1,target,target=tmp_path)
    def garbage(process,out):open(out,'wb').write(b'not a wav');return b'',None
    monkeypatch.setattr(speech.subprocess,'Popen',lambda args,**kw:FakeProcess(args,garbage,**kw))
    with pytest.raises(ValueError,match='unusable'):speech.synthesize('Open.',21,1,target,target=tmp_path)
    def empty(process,out):write_wave(out,0);return b'',None
    monkeypatch.setattr(speech.subprocess,'Popen',lambda args,**kw:FakeProcess(args,empty,**kw))
    with pytest.raises(ValueError,match='unusable'):speech.synthesize('Open.',21,1,target,target=tmp_path)
    assert target.read_bytes()==b'previous' and not list(tmp_path.glob('.*.tmp.wav'))


def test_cancel_kills_only_its_process_and_keeps_existing_file(tmp_path,monkeypatch):
    cancel=threading.Event();target=tmp_path/'out.wav';target.write_bytes(b'previous')
    def slow(process,out):
        if process.killed:return b'',None
        cancel.set();raise subprocess.TimeoutExpired('x',.2)
    made=prepare(tmp_path,monkeypatch,slow)
    with pytest.raises(RuntimeError,match='cancelled'):speech.synthesize('Open.',21,1,target,cancel=cancel,target=tmp_path)
    assert made[0].killed and target.read_bytes()==b'previous'


def test_missing_and_damaged_runtime_have_clear_errors(tmp_path,monkeypatch):
    with pytest.raises(speech.MissingSpeechRuntime,match='not installed'):speech.synthesize('Open.',21,1,tmp_path/'o.wav',target=tmp_path)
    exe=tmp_path/speech.EXECUTABLE;exe.parent.mkdir(parents=True);exe.write_bytes(b'tampered')
    with pytest.raises(speech.MissingSpeechRuntime,match='damaged'):speech.synthesize('Open.',21,1,tmp_path/'o.wav',target=tmp_path)
