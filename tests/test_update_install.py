import json
from pathlib import Path
import pytest
from sop_capture.update_install import validate_plan,apply_update


def test_already_exited_parent_does_not_require_a_live_process_image(monkeypatch,tmp_path):
    import ctypes
    from types import SimpleNamespace
    from sop_capture.update_install import wait_parent
    class Call:
        def __init__(self,fn):self.fn=fn
        def __call__(self,*args):return self.fn(*args)
    closed=[]
    kernel=SimpleNamespace(OpenProcess=Call(lambda *a:1),CloseHandle=Call(lambda h:closed.append(h)),
        WaitForSingleObject=Call(lambda *a:0),
        QueryFullProcessImageNameW=Call(lambda *a:pytest.fail('An exited process may no longer expose its image path')))
    monkeypatch.setattr(ctypes,'WinDLL',lambda *a,**k:kernel)
    wait_parent({'parent_pid':123,'install':tmp_path})
    assert closed==[1]


def test_live_unrelated_parent_is_still_rejected(monkeypatch,tmp_path):
    import ctypes
    from types import SimpleNamespace
    from sop_capture.update_install import wait_parent
    class Call:
        def __init__(self,fn):self.fn=fn
        def __call__(self,*args):return self.fn(*args)
    def query(handle,flags,buffer,size):
        buffer.value=str(tmp_path/'unrelated.exe');return 1
    kernel=SimpleNamespace(OpenProcess=Call(lambda *a:1),CloseHandle=Call(lambda h:None),
        WaitForSingleObject=Call(lambda *a:258),QueryFullProcessImageNameW=Call(query))
    monkeypatch.setattr(ctypes,'WinDLL',lambda *a,**k:kernel)
    with pytest.raises(ValueError,match='Parent process'):
        wait_parent({'parent_pid':123,'install':tmp_path})


def test_frozen_main_app_can_prepare_external_helper(tmp_path,monkeypatch):
    import hashlib,sys,zipfile
    from sop_capture.update_install import prepare_handoff
    path,install,stage=setup(tmp_path)
    path.unlink()
    archive=stage.parents[1]/'SOPCaptureStudio-0.2.0-Windows-x64.zip'
    with zipfile.ZipFile(archive,'w') as bundle:
        for file in stage.rglob('*'):
            if file.is_file():bundle.write(file,'SOPCaptureStudio/'+file.relative_to(stage).as_posix())
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    (archive.parent/'checksum.txt').write_text(digest+'  '+archive.name)
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    monkeypatch.setattr(sys,'executable',str(install/'SOPCaptureStudio.exe'))
    plan,runner,token=prepare_handoff(stage,install,'0.1.0','0.2.0',123)
    assert runner.parent==plan.parent
    assert not runner.is_relative_to(install)
    assert runner.read_bytes()==b'helper'
    assert json.loads(plan.read_text())['token']==token


def test_frozen_updater_still_refuses_to_replace_its_own_folder(tmp_path,monkeypatch):
    import sys
    path,install,stage=setup(tmp_path)
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    monkeypatch.setattr(sys,'executable',str(install/'SOPCaptureUpdater.exe'))
    with pytest.raises(ValueError,match='outside the application folder'):
        apply_update(path,wait_parent=lambda p:pytest.fail('Must refuse before waiting'))
    assert (install/'SOPCaptureStudio.exe').read_bytes()==b'old'


def setup(tmp_path):
    install=tmp_path/'installed';stage=tmp_path/'job/staged/SOPCaptureStudio';install.mkdir();stage.mkdir(parents=True)
    for root,version,content in ((install,'0.1.0',b'old'),(stage,'0.2.0',b'new')):
        (root/'_internal').mkdir();(root/'SOPCaptureStudio.exe').write_bytes(content);(root/'SOPCaptureUpdater.exe').write_bytes(b'helper');(root/'RELEASE.json').write_text(json.dumps({'app':'SOPCaptureStudio','version':version}))
    plan={'version':1,'install':str(install),'staged':str(stage),'old_version':'0.1.0','new_version':'0.2.0','token':'a'*32,'parent_pid':123,'quiet':True}
    path=tmp_path/'job/update-plan.json';path.write_text(json.dumps(plan));return path,install,stage


def test_transaction_replaces_only_app_and_retains_backup(tmp_path):
    path,install,stage=setup(tmp_path);personal=tmp_path/'projects';personal.mkdir();(personal/'procedure.docx').write_bytes(b'private')
    def launch(exe,args):
        ack=Path(args[args.index('--update-ack')+1]);ack.write_text(json.dumps({'token':'a'*32,'version':'0.2.0'}))
        return Process()
    result=apply_update(path,wait_parent=lambda p:None,launch=launch,timeout=.1)
    assert (install/'SOPCaptureStudio.exe').read_bytes()==b'new'
    assert (Path(result['backup'])/'SOPCaptureStudio.exe').read_bytes()==b'old'
    assert (personal/'procedure.docx').read_bytes()==b'private'


class Process:
    def poll(self):return None


def test_startup_failure_restores_old_app(tmp_path):
    path,install,stage=setup(tmp_path);calls=[]
    class Failed:
        def poll(self):return 1
    def launch(exe,args):calls.append(exe);return Failed()
    result=apply_update(path,wait_parent=lambda p:None,launch=launch,timeout=.01)
    assert result['status']=='rolled-back' and (install/'SOPCaptureStudio.exe').read_bytes()==b'old'
    assert len(calls)==2


def test_running_unacknowledged_app_is_not_replaced(tmp_path):
    path,install,stage=setup(tmp_path)
    result=apply_update(path,wait_parent=lambda p:None,launch=lambda exe,args:Process(),timeout=.01)
    assert result['status']=='needs-attention'
    assert (install/'SOPCaptureStudio.exe').read_bytes()==b'new'
    assert Path(result['backup']).exists()


def test_refuse_data_in_installation_and_overlapping_paths(tmp_path):
    path,install,stage=setup(tmp_path);(install/'project.json').write_text('{}')
    with pytest.raises(ValueError):validate_plan(path)
    assert (install/'SOPCaptureStudio.exe').read_bytes()==b'old'
    (install/'project.json').unlink();data=json.loads(path.read_text());data['install']=str(path.parent);path.write_text(json.dumps(data))
    with pytest.raises(ValueError):validate_plan(path)


def test_cancelled_confirmation_does_not_wait_or_replace(tmp_path):
    path,install,stage=setup(tmp_path);plan=json.loads(path.read_text());plan.update(requires_confirmation=True,archive=str(path.parent/'SOPCaptureStudio-0.2.0-Windows-x64.zip'),sha256='0'*64);path.write_text(json.dumps(plan));(path.parent/'cancelled.json').write_text('{}')
    def must_not_wait(plan):raise AssertionError('Should not reach installation')
    result=apply_update(path,wait_parent=must_not_wait)
    assert result['status']=='cancelled' and (install/'SOPCaptureStudio.exe').read_bytes()==b'old'


def test_acknowledgement_is_bound_to_installation_token_and_version(tmp_path):
    from sop_capture.update_install import acknowledge_startup
    path,install,stage=setup(tmp_path);ack=path.parent/'ready.json'
    assert not acknowledge_startup(ack,'b'*32,'0.2.0',install/'SOPCaptureStudio.exe') and not ack.exists()
    assert acknowledge_startup(ack,'a'*32,'0.2.0',install/'SOPCaptureStudio.exe')


def test_parent_still_running_does_not_launch_a_duplicate_app(tmp_path):
    path,install,stage=setup(tmp_path);calls=[]
    def blocked(plan):raise RuntimeError('Parent is still running')
    result=apply_update(path,wait_parent=blocked,launch=lambda *args:calls.append(args))
    assert result['status']=='not-installed' and calls==[]
