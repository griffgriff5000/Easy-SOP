"""Stdlib-only transactional helper; never runs from the folder it replaces."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

APP_FILES={'SOPCaptureStudio.exe','SOPCaptureUpdater.exe','_internal','RELEASE.json','LICENSE.txt','START_HERE.txt','THIRD_PARTY_COMPONENTS.json','QT_NOTICE.txt','licenses'}


def manifest(root,version):
    try:data=json.loads((root/'RELEASE.json').read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc:raise ValueError('Extract the complete official release ZIP before using automatic updates.') from exc
    if data!={'app':'SOPCaptureStudio','version':version}:raise ValueError('Installed/staged application manifest is not the expected version.')
    if not (root/'SOPCaptureStudio.exe').is_file() or not (root/'SOPCaptureUpdater.exe').is_file() or not (root/'_internal').is_dir():raise ValueError('The complete application folder is required.')


def owned_installation(install,version):
    manifest(install,version)
    allowed={name.casefold() for name in APP_FILES}
    if any(p.name.casefold() not in allowed for p in install.iterdir()):raise ValueError('The application folder contains extra files. Move projects/personal files out before updating, or install manually in a new folder.')
    for path in install.rglob('*'):
        if path.is_symlink() or (hasattr(path,'is_junction') and path.is_junction()):raise ValueError('Links/junctions inside the application folder require a manual update.')
        if path.name.casefold() in {'project.json','revision.json','project.backup.json'} or path.suffix.lower()=='.sopannotation':raise ValueError('Project/library data was found inside the application folder. Automatic replacement was refused.')


def validate_plan(path):
    path=Path(path).resolve();job=path.parent
    if path.name!='update-plan.json' or path.stat().st_size>16384:raise ValueError('Invalid update plan.')
    plan=json.loads(path.read_text(encoding='utf-8'))
    if plan.get('version')!=1 or not re.fullmatch('[0-9a-f]{32}',str(plan.get('token',''))):raise ValueError('Invalid update transaction.')
    for field in ('old_version','new_version'):
        if not re.fullmatch(r'\d{1,5}\.\d{1,5}\.\d{1,5}',str(plan.get(field,''))):raise ValueError('Invalid application version.')
    if tuple(map(int,plan['new_version'].split('.')))<=tuple(map(int,plan['old_version'].split('.'))):raise ValueError('Only newer application versions can be installed.')
    if type(plan.get('parent_pid')) is not int or not 0<plan['parent_pid']<2**31:raise ValueError('Invalid parent process.')
    if not Path(plan['install']).is_absolute() or not Path(plan['staged']).is_absolute():raise ValueError('Update folders must be absolute.')
    install=Path(plan['install']).resolve();staged=Path(plan['staged']).resolve()
    if install==Path(install.anchor) or install in {Path.home().resolve(),Path.home().parent.resolve()} or job.is_relative_to(install) or install.is_relative_to(job) or staged!=job/'staged/SOPCaptureStudio':raise ValueError('Unsafe or overlapping update folders.')
    owned_installation(install,plan['old_version']);manifest(staged,plan['new_version'])
    if plan.get('requires_confirmation'):
        archive=Path(plan.get('archive','')).resolve()
        if archive!=job/f'SOPCaptureStudio-{plan["new_version"]}-Windows-x64.zip' or not re.fullmatch('[a-f0-9]{64}',str(plan.get('sha256',''))):raise ValueError('Invalid verified update archive.')
    plan.update(install=install,staged=staged,job=job)
    return plan


def wait_parent(plan,timeout=90):
    if os.name!='nt':
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            try:os.kill(plan['parent_pid'],0)
            except ProcessLookupError:return
            time.sleep(.1)
        raise RuntimeError('The previous application did not close.')
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];kernel.WaitForSingleObject.restype=wintypes.DWORD
    handle=kernel.OpenProcess(0x100000|0x1000,False,plan['parent_pid'])
    if not handle:
        if ctypes.get_last_error()==87:return
        raise OSError('Could not verify the running application process.')
    try:
        # A closed process can remain queryable by PID while another handle exists,
        # but Windows may already have discarded its executable image information.
        if kernel.WaitForSingleObject(handle,0)==0:return
        buffer=ctypes.create_unicode_buffer(32768);size=wintypes.DWORD(len(buffer))
        if not kernel.QueryFullProcessImageNameW(handle,0,buffer,ctypes.byref(size)):
            if kernel.WaitForSingleObject(handle,0)==0:return
            raise ValueError('Parent process is not the installed SOP application.')
        if Path(buffer.value).resolve()!=plan['install']/'SOPCaptureStudio.exe':raise ValueError('Parent process is not the installed SOP application.')
        if kernel.WaitForSingleObject(handle,int(timeout*1000))!=0:raise RuntimeError('SOP Capture Studio is still running. No files were replaced.')
    finally:kernel.CloseHandle(handle)


def start_app(executable,args):
    return subprocess.Popen([str(executable),*map(str,args)],cwd=str(executable.parent),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),close_fds=True)


def rename_retry(source,target):
    deadline=time.monotonic()+8
    while True:
        try:source.rename(target);return
        except OSError:
            if time.monotonic()>=deadline:raise
            time.sleep(.2)


def write_result(job,result):
    temporary=job/'result.tmp';temporary.write_text(json.dumps(result,indent=2),encoding='utf-8');temporary.replace(job/'result.json');return result


def prepare_handoff(staged,install,old_version,new_version,parent_pid):
    staged=Path(staged).resolve();install=Path(install).resolve();job=staged.parents[1];token=uuid.uuid4().hex
    path=job/'update-plan.json'
    if path.exists():raise ValueError('Prepare a fresh update download before retrying installation.')
    archive=job/f'SOPCaptureStudio-{new_version}-Windows-x64.zip';checksum=(job/'checksum.txt').read_text(encoding='utf-8').strip()
    match=re.fullmatch(r'([a-fA-F0-9]{64})\s+\*?'+re.escape(archive.name),checksum)
    if not match:raise ValueError('The verified update checksum is missing.')
    with archive.open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=match[1].lower():raise ValueError('The downloaded archive changed. Download a fresh update.')
    plan={'version':1,'install':str(install),'staged':str(staged),'old_version':old_version,'new_version':new_version,'parent_pid':parent_pid,'token':token,'requires_confirmation':True,'archive':str(archive),'sha256':match[1].lower()}
    path.write_text(json.dumps(plan),encoding='utf-8');validate_plan(path)
    probe=install.parent/('.sop-update-probe-'+token)
    with probe.open('xb') as stream:stream.write(b'probe')
    probe.unlink();runner=job/'updater-runner.exe';shutil.copy2(install/'SOPCaptureUpdater.exe',runner)
    return path,runner,token


def acknowledge_startup(path,token,version,executable=None):
    path=Path(path).resolve();plan_path=path.parent/'update-plan.json'
    if path.name!='ready.json' or not plan_path.is_file() or plan_path.stat().st_size>16384:return False
    plan=json.loads(plan_path.read_text(encoding='utf-8'))
    if plan.get('token')!=token or plan.get('new_version')!=version or not re.fullmatch('[a-f0-9]{32}',token):return False
    if Path(plan.get('install','')).resolve()!=Path(executable or sys.executable).resolve().parent:return False
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps({'token':token,'version':version}),encoding='utf-8');temporary.replace(path);return True


def apply_update(path,*,wait_parent=wait_parent,launch=start_app,timeout=90):
    plan=validate_plan(path);install=plan['install'];job=plan['job'];suffix=plan['token'][:12]
    # Preparation runs in the main app; only the replacement helper must be external.
    if getattr(sys,'frozen',False) and Path(sys.executable).resolve().is_relative_to(install):raise ValueError('Updater must run outside the application folder.')
    prepared=install.parent/(install.name+'.update-'+suffix);replacement=prepared;backup=install.parent/(install.name+'.previous-'+suffix);ack=job/'ready.json';process=None;moved=False;installed=False;parent_closed=False
    if prepared.exists() or backup.exists() or ack.exists():raise ValueError('This update transaction has already been used.')
    log=job/'install.log'
    def note(message):
        with log.open('a',encoding='utf-8') as stream:stream.write(message+'\n')
    try:
        if plan.get('requires_confirmation'):
            deadline=time.monotonic()+120
            while True:
                if (job/'cancelled.json').exists():return write_result(job,{'status':'cancelled'})
                try:confirmation=json.loads((job/'confirmed.json').read_text(encoding='utf-8'))
                except (OSError,ValueError):confirmation={}
                if confirmation=={'token':plan['token']}:break
                if time.monotonic()>=deadline:raise RuntimeError('Installation was not confirmed. No application files were replaced.')
                time.sleep(.1)
        wait_parent(plan);parent_closed=True;note('Previous process closed.')
        owned_installation(install,plan['old_version']);manifest(plan['staged'],plan['new_version'])
        required=sum(p.stat().st_size for p in plan['staged'].rglob('*') if p.is_file())
        if shutil.disk_usage(install.parent).free<required+20*1024*1024:raise OSError('Not enough free disk space to stage the application.')
        if plan.get('archive'):
            from .updates import stage_archive
            replacement=stage_archive(plan['archive'],plan['sha256'],prepared,plan['new_version'])
        else:shutil.copytree(plan['staged'],prepared)
        manifest(replacement,plan['new_version']);note('Verified replacement prepared beside installation.')
        owned_installation(install,plan['old_version'])
        rename_retry(install,backup);moved=True
        rename_retry(replacement,install);installed=True;note('Installed new application; waiting for startup acknowledgement.')
        process=launch(install/'SOPCaptureStudio.exe',['--update-ack',str(ack),'--update-token',plan['token']]);deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if ack.exists():
                try:data=json.loads(ack.read_text(encoding='utf-8'))
                except (ValueError,OSError):data={}
                if data=={'token':plan['token'],'version':plan['new_version']}:note('New UI started successfully.');return write_result(job,{'status':'updated','version':plan['new_version'],'backup':str(backup),'pid':getattr(process,'pid',None)})
            if process.poll() is not None:raise RuntimeError('The new application exited before confirming startup.')
            time.sleep(.1)
        if process.poll() is None:
            note('New process is still running but did not acknowledge; not replacing live files.')
            return write_result(job,{'status':'needs-attention','error':'The new app did not confirm startup. Previous files are retained; close the new app before manual recovery.','backup':str(backup)})
        raise RuntimeError('The new app did not confirm startup.')
    except Exception as exc:
        note('Update failed: '+str(exc))
        if process is not None and process.poll() is None:
            return write_result(job,{'status':'needs-attention','error':str(exc),'backup':str(backup)})
        try:
            if moved:
                if installed and install.exists():rename_retry(install,replacement)
                rename_retry(backup,install);note('Restored previous application.')
            result=write_result(job,{'status':'rolled-back' if moved else 'not-installed','error':str(exc),'backup':str(backup) if backup.exists() else ''})
            if parent_closed and (install/'SOPCaptureStudio.exe').is_file():
                restarted=launch(install/'SOPCaptureStudio.exe',[]);result['restarted_pid']=getattr(restarted,'pid',None);write_result(job,result)
            return result
        except Exception as recovery:
            return write_result(job,{'status':'needs-attention','error':str(exc)+' Recovery: '+str(recovery),'backup':str(backup)})


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--plan',type=Path);parser.add_argument('--self-test',action='store_true');args=parser.parse_args()
    if args.self_test:return 0
    if args.plan is None:return 2
    try:
        result=apply_update(args.plan)
        quiet=json.loads(args.plan.read_text(encoding='utf-8')).get('quiet',False)
        if result['status'] not in {'updated','cancelled'} and not quiet and os.name=='nt':ctypes.windll.user32.MessageBoxW(None,result.get('error','Update could not complete.')+'\n\nDetails: '+str(args.plan.parent/'install.log'),'SOP Capture Studio update',0x30)
        return 0 if result['status'] in {'updated','cancelled'} else 1
    except Exception as exc:
        if os.name=='nt':ctypes.windll.user32.MessageBoxW(None,str(exc)+'\n\nThe existing installation was not replaced.','SOP Capture Studio update',0x30)
        return 1
