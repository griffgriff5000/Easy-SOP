import hashlib,json,zipfile
from pathlib import Path
import pytest
from sop_capture.updates import parse_release,is_newer,stage_archive,Cancelled,download_file


def release(version='0.2.0'):
    name=f'SOPCaptureStudio-{version}-Windows-x64.zip';base='https://github.com/griffgriff5000/Easy-SOP/releases/download/v'+version+'/'
    return {'tag_name':'v'+version,'draft':False,'prerelease':False,'html_url':'https://github.com/griffgriff5000/Easy-SOP/releases/tag/v'+version,'body':'Changes','assets':[{'name':name,'size':100,'browser_download_url':base+name},{'name':name+'.sha256','size':120,'browser_download_url':base+name+'.sha256'}]}


def archive(path,extra=None):
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('SOPCaptureStudio/SOPCaptureStudio.exe',b'MZmain');z.writestr('SOPCaptureStudio/SOPCaptureUpdater.exe',b'MZhelper');z.writestr('SOPCaptureStudio/_internal/runtime.dll',b'dll')
        z.writestr('SOPCaptureStudio/RELEASE.json',json.dumps({'app':'SOPCaptureStudio','version':'0.2.0'}))
        if extra:z.writestr(*extra)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_versions_and_only_correct_stable_release_assets():
    assert is_newer('0.2.0','0.1.9') and not is_newer('0.2.0','0.2.0') and not is_newer('0.1.0','0.2.0')
    assert parse_release(release())['version']=='0.2.0'
    bad=release();bad['prerelease']=True
    with pytest.raises(ValueError):parse_release(bad)
    bad=release();bad['assets'][0]['browser_download_url']='https://evil.example/app.zip'
    with pytest.raises(ValueError):parse_release(bad)


def test_setup_assets_do_not_change_existing_portable_update_selection():
    data=release('0.3.0')
    base='https://github.com/griffgriff5000/Easy-SOP/releases/download/v0.3.0/'
    for name in ('SOPCaptureStudio-0.3.0-Windows-x64-Setup.exe','SOPCaptureStudio-0.3.0-Windows-x64-Setup.exe.sha256'):
        data['assets'].append({'name':name,'size':100,'browser_download_url':base+name})
    parsed=parse_release(data)
    assert parsed['asset']['name']=='SOPCaptureStudio-0.3.0-Windows-x64.zip'
    assert parsed['checksum']['name'].endswith('.zip.sha256')


def test_staging_checks_hash_manifest_and_zip_paths(tmp_path):
    path=tmp_path/'app.zip';digest=archive(path);staged=stage_archive(path,digest,tmp_path/'stage','0.2.0')
    assert (staged/'SOPCaptureStudio.exe').read_bytes()==b'MZmain'
    with pytest.raises(ValueError):stage_archive(path,'0'*64,tmp_path/'wrong','0.2.0')
    with pytest.raises(ValueError):stage_archive(path,digest,tmp_path/'version','0.3.0')
    for name in ('../escape','SOPCaptureStudio/../../escape','SOPCaptureStudio/C:/escape','SOPCaptureStudio/_internal/CON','SOPCaptureStudio/file:stream'):
        digest=archive(path,(name,b'bad'))
        with pytest.raises(ValueError):stage_archive(path,digest,tmp_path/'unsafe','0.2.0')
    assert not (tmp_path/'escape').exists()


def test_cancelled_download_does_not_keep_partial_file(tmp_path):
    with pytest.raises(Cancelled):download_file('https://github.com/griffgriff5000/Easy-SOP/releases/download/v0.2.0/app.zip',tmp_path/'app.zip',cancel=lambda:True)
    assert not (tmp_path/'app.zip').exists()
