"""Public GitHub release checks, bounded downloads and validated Windows staging."""
import hashlib
import json
from pathlib import Path,PurePosixPath
import re
import shutil
import stat
import urllib.parse
import urllib.request
import zipfile

API='https://api.github.com/repos/griffgriff5000/Easy-SOP/releases/latest'
REPO='https://github.com/griffgriff5000/Easy-SOP'
MAX_DOWNLOAD=350*1024*1024


class Cancelled(Exception):pass


def version_tuple(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{1,5}\.\d{1,5}\.\d{1,5}',value):raise ValueError('Unsupported release version.')
    return tuple(int(part) for part in value.split('.'))


def is_newer(latest,current):return version_tuple(latest)>version_tuple(current)


def allowed_url(url):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or parsed.username or parsed.password or parsed.port not in {None,443}:return False
    if parsed.hostname=='api.github.com':return parsed.path=='/repos/griffgriff5000/Easy-SOP/releases/latest'
    if parsed.hostname=='github.com':return parsed.path.startswith('/griffgriff5000/Easy-SOP/releases/download/')
    return parsed.hostname in {'release-assets.githubusercontent.com','objects.githubusercontent.com','github-releases.githubusercontent.com'}


class Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,url):
        if not allowed_url(url):raise ValueError('Update download redirected outside the official release hosts.')
        return super().redirect_request(req,fp,code,msg,headers,url)


def open_url(url):
    if not allowed_url(url):raise ValueError('Update URL is not an official GitHub release URL.')
    request=urllib.request.Request(url,headers={'User-Agent':'SOPCaptureStudio-updater','Accept':'application/vnd.github+json' if url==API else 'application/octet-stream'})
    return urllib.request.build_opener(Redirects()).open(request,timeout=25)


def parse_release(data):
    if not isinstance(data,dict) or data.get('draft') or data.get('prerelease'):raise ValueError('No supported stable release was found.')
    version=str(data.get('tag_name','')).removeprefix('v');version_tuple(version)
    if data.get('html_url')!=REPO+'/releases/tag/v'+version:raise ValueError('Unexpected release repository.')
    filename=f'SOPCaptureStudio-{version}-Windows-x64.zip';assets=data.get('assets',[])
    def asset(name):
        matches=[a for a in assets if isinstance(a,dict) and a.get('name')==name]
        if len(matches)!=1:raise ValueError('The Windows update package or checksum is missing.')
        entry=matches[0];url=entry.get('browser_download_url','')
        if url!=REPO+'/releases/download/v'+version+'/'+name:raise ValueError('Unexpected update asset URL.')
        if type(entry.get('size')) is not int or not 0<entry['size']<=MAX_DOWNLOAD:raise ValueError('Invalid update download size.')
        return entry
    package=asset(filename);checksum=asset(filename+'.sha256')
    if checksum['size']>4096:raise ValueError('Invalid checksum file.')
    return {'version':version,'notes':str(data.get('body') or '')[:30000],'url':data['html_url'],'asset':package,'checksum':checksum}


def check_release():
    with open_url(API) as response:
        raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError('Release response is too large.')
    return parse_release(json.loads(raw))


def download_file(url,destination,*,cancel=lambda:False,progress=lambda done,total:None,expected_size=None,limit=MAX_DOWNLOAD):
    destination=Path(destination);partial=destination.with_suffix(destination.suffix+'.part');created=False
    if cancel():raise Cancelled('Download cancelled.')
    try:
        with open_url(url) as response,partial.open('xb') as output:
            created=True;done=0
            while chunk:=response.read(256*1024):
                if cancel():raise Cancelled('Download cancelled.')
                done+=len(chunk)
                if done>limit or (expected_size is not None and done>expected_size):raise ValueError('Update exceeds its declared size.')
                output.write(chunk);progress(done,expected_size or 0)
        if cancel():raise Cancelled('Download cancelled.')
        if expected_size is not None and done!=expected_size:raise ValueError('Update download was incomplete.')
        if destination.exists():raise ValueError('Download destination already exists.')
        partial.rename(destination);return destination
    finally:
        if created:partial.unlink(missing_ok=True)


def stage_archive(archive,expected_hash,destination,version):
    version_tuple(version);archive=Path(archive);destination=Path(destination).resolve()
    with archive.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if not re.fullmatch('[a-fA-F0-9]{64}',expected_hash) or digest!=expected_hash.lower():raise ValueError('Update checksum does not match. Nothing was installed.')
    created=False
    try:
        with zipfile.ZipFile(archive) as package:
            entries=package.infolist()
            if len(entries)>10000 or sum(e.file_size for e in entries)>2*1024**3:raise ValueError('Expanded update is too large.')
            seen=set()
            for entry in entries:
                raw=entry.filename
                parts=raw.rstrip('/').split('/')
                if '\\' in raw or not parts or parts[0]!='SOPCaptureStudio' or any(p in {'','.','..'} or ':' in p or p.endswith((' ','.')) or '\0' in p or re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)',p,re.I) for p in parts):raise ValueError('Unsafe update archive path.')
                mode=entry.external_attr>>16
                if stat.S_ISLNK(mode) or stat.S_IFMT(mode) not in {0,stat.S_IFREG,stat.S_IFDIR} or entry.flag_bits&1:raise ValueError('Links or encrypted archive entries are not supported.')
                name='/'.join(parts).casefold()
                if name in seen:raise ValueError('Duplicate update archive path.')
                seen.add(name)
            required={'sopcapturestudio/sopcapturestudio.exe','sopcapturestudio/sopcaptureupdater.exe','sopcapturestudio/release.json'}
            if not required.issubset(seen) or not any(n.startswith('sopcapturestudio/_internal/') for n in seen):raise ValueError('This is not a complete SOP Capture Studio update.')
            if package.getinfo('SOPCaptureStudio/RELEASE.json').file_size>4096:raise ValueError('Update manifest is too large.')
            manifest=json.loads(package.read('SOPCaptureStudio/RELEASE.json'))
            if manifest!={'app':'SOPCaptureStudio','version':version}:raise ValueError('Update app/version manifest does not match the release.')
            if shutil.disk_usage(destination.parent).free<sum(e.file_size for e in entries)+20*1024*1024:raise OSError('Not enough free disk space to stage this update.')
            destination.mkdir(parents=True,exist_ok=False);created=True
            for entry in entries:
                target=destination.joinpath(*PurePosixPath(entry.filename).parts)
                if not target.resolve().is_relative_to(destination):raise ValueError('Archive path escapes update staging.')
                if entry.is_dir():target.mkdir(parents=True,exist_ok=True)
                else:
                    target.parent.mkdir(parents=True,exist_ok=True)
                    with package.open(entry) as source,target.open('xb') as output:shutil.copyfileobj(source,output,256*1024)
        return destination/'SOPCaptureStudio'
    except BaseException:
        if created:shutil.rmtree(destination)
        raise


def prepare_update(release,job,*,cancel=lambda:False,progress=lambda done,total:None):
    job=Path(job);job.mkdir(parents=True,exist_ok=False)
    checksum=download_file(release['checksum']['browser_download_url'],job/'checksum.txt',cancel=cancel,expected_size=release['checksum']['size'],limit=4096).read_text(encoding='utf-8').strip()
    match=re.fullmatch(r'([a-fA-F0-9]{64})\s+\*?'+re.escape(release['asset']['name']),checksum)
    if not match:raise ValueError('Release checksum is missing or names another package.')
    archive=download_file(release['asset']['browser_download_url'],job/release['asset']['name'],cancel=cancel,progress=progress,expected_size=release['asset']['size'])
    if cancel():raise Cancelled('Download cancelled.')
    staged=stage_archive(archive,match[1],job/'staged',release['version'])
    if cancel():raise Cancelled('Download cancelled.')
    return staged
