"""Exercise the actual frozen helper on isolated app copies, including rollback."""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib,json,shutil,subprocess,sys,time,uuid,zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sop_capture.updates import stage_archive
from sop_capture.update_install import prepare_handoff


def close_test_app(pid):
    import win32api,win32con,win32gui,win32process
    if not pid:return
    try:handle=win32api.OpenProcess(win32con.SYNCHRONIZE,False,pid)
    except Exception:return
    def close(hwnd,unused):
        if win32process.GetWindowThreadProcessId(hwnd)[1]==pid:win32gui.PostMessage(hwnd,win32con.WM_CLOSE,0,0)
    import win32event
    deadline=time.monotonic()+30;result=None
    while time.monotonic()<deadline:
        result=win32event.WaitForSingleObject(handle,100)
        if result==win32event.WAIT_OBJECT_0:break
        win32gui.EnumWindows(close,None)
    handle.Close()
    if result!=win32event.WAIT_OBJECT_0:raise RuntimeError('Synthetic updated app did not close')


def exercise(archive,root,expected):
    root.mkdir();installed=stage_archive(archive,hashlib.file_digest(archive.open('rb'),'sha256').hexdigest(),root/'original','0.2.0')
    # Same real executable, labelled as the preceding release to exercise the handoff.
    (installed/'RELEASE.json').write_text(json.dumps({'app':'SOPCaptureStudio','version':'0.1.0'}))
    job=root/'job';job.mkdir();payload=job/'SOPCaptureStudio-0.2.0-Windows-x64.zip'
    if expected=='updated':shutil.copy2(archive,payload)
    else:
        with zipfile.ZipFile(archive) as source,zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as target:
            for item in source.infolist():target.writestr(item,b'not a Windows program' if item.filename=='SOPCaptureStudio/SOPCaptureStudio.exe' else source.read(item))
    with payload.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    (job/'checksum.txt').write_text(digest+'  '+payload.name+'\n');staged=stage_archive(payload,digest,job/'staged','0.2.0')
    parent=subprocess.Popen([str(installed/'SOPCaptureStudio.exe'),'--smoke-test'],creationflags=subprocess.CREATE_NO_WINDOW)
    plan,runner,token=prepare_handoff(staged,installed,'0.1.0','0.2.0',parent.pid);data=json.loads(plan.read_text());data['quiet']=True;plan.write_text(json.dumps(data))
    helper=subprocess.Popen([str(runner),'--plan',str(plan)],creationflags=subprocess.CREATE_NO_WINDOW)
    (job/'confirmed.json').write_text(json.dumps({'token':token}));parent.wait(timeout=40);helper.wait(timeout=150)
    result=json.loads((job/'result.json').read_text());assert result['status']==expected,result
    if expected=='updated':
        assert json.loads((installed/'RELEASE.json').read_text())['version']=='0.2.0';assert Path(result['backup']).exists();close_test_app(result.get('pid'))
    else:
        assert json.loads((installed/'RELEASE.json').read_text())['version']=='0.1.0';close_test_app(result.get('restarted_pid'))
    print('Packaged updater:',expected,'passed',flush=True)


def main():
    archive=Path(sys.argv[1]).resolve()
    with TemporaryDirectory(prefix='sop-updater-smoke-') as temp:
        root=Path(temp);exercise(archive,root/'success','updated');exercise(archive,root/'rollback','rolled-back')

if __name__=='__main__':main()
