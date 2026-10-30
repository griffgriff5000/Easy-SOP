"""Package the verified folder build for GitHub Releases; no personal app data."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata as metadata
import json
import sys
import tomllib
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PRIVATE_NAMES={'project.json','project.backup.json','revision.json','recent-projects.json','workspace-layouts.json','profile.json'}
RUNTIME=('PySide6','PySide6_Essentials','PySide6_Addons','PySide6_Pdf','PySide6_WebEngine','shiboken6','Pillow','reportlab','python-docx','lxml','pdfplumber','pdfminer.six','pypdfium2','cryptography','cffi','pycparser','charset-normalizer','pywin32')
QUICK_START='''SOP Capture Studio — Windows x64

1. Download this ZIP from the GitHub release Assets section.
2. Right-click the ZIP and choose Extract All. Keep the whole extracted folder.
3. Open SOPCaptureStudio and double-click SOPCaptureStudio.exe.
   Python and a terminal are not required. Do not move the EXE away from _internal.

Home > New project creates a separate folder for each SOP.
A fresh template library contains Standard SOP only. You may add your own templates.
Help > User guide (F1) explains capture, annotations, templates and document revision.
Workspace > Customise this workspace changes panel layouts and toolbars.

Desktop Microsoft Word must already be installed for direct Word editing and Word-based
PDF conversion. Standard SOP capture/edit/export features can be used without Word.
Optional local AI requires a separately installed Ollama service and local model.

Projects, templates and settings stay on your own machine. This download contains
no saved company templates, recent-project history, personal settings or demo projects.

The application is not digitally signed. Your organisation's Windows policy may
require IT approval before running a downloaded application. Do not bypass company policy.

This is an early release: review generated procedures before issuing controlled documents.
'''


def package(build,output,version,licenses=None):
    build=Path(build).resolve();output=Path(output).resolve()
    if not (build/'SOPCaptureStudio.exe').is_file() or not (build/'_internal').is_dir():raise ValueError('Build the complete SOPCaptureStudio folder first.')
    files=sorted(p for p in build.rglob('*') if p.is_file())
    for path in files:
        if path.name in PRIVATE_NAMES or path.suffix.lower()=='.sopannotation':raise ValueError('Private application data found in build: '+str(path.relative_to(build)))
    output.mkdir(parents=True,exist_ok=True);archive=output/f'SOPCaptureStudio-{version}-Windows-x64.zip';prefix='SOPCaptureStudio/';components=[]
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as bundle:
        for path in files:bundle.write(path,prefix+path.relative_to(build).as_posix())
        bundle.write(ROOT/'LICENSE',prefix+'LICENSE.txt');bundle.writestr(prefix+'START_HERE.txt',QUICK_START)
        for name in RUNTIME:
            try:dist=metadata.distribution(name)
            except metadata.PackageNotFoundError:continue
            components.append({'name':dist.metadata['Name'],'version':dist.version,'license':dist.metadata.get('License-Expression') or dist.metadata.get('License','See included notices'),'project_urls':dist.metadata.get_all('Project-URL',[])})
            for item in dist.files or []:
                if any(part.lower() in {'licenses','license','copying','notice'} or part.lower().startswith(('license.','copying.','notice.')) for part in item.parts):
                    source=dist.locate_file(item)
                    if source.is_file():bundle.write(source,prefix+'licenses/'+name+'/'+item.as_posix())
        if licenses:
            for path in sorted(Path(licenses).rglob('*')):
                if path.is_file():bundle.write(path,prefix+'licenses/additional/'+path.relative_to(licenses).as_posix())
        bundle.writestr(prefix+'THIRD_PARTY_COMPONENTS.json',json.dumps(components,indent=2))
        bundle.writestr(prefix+'QT_NOTICE.txt','Qt for Python/PySide6 and Qt libraries are used dynamically as replaceable DLLs.\nOpen-source licensing information: https://doc.qt.io/qtforpython-6/\nCorresponding upstream sources: https://code.qt.io/cgit/pyside/pyside-setup.git/ and https://code.qt.io/cgit/qt/\nSee THIRD_PARTY_COMPONENTS.json for component versions and licenses/ for notices.\nThe application MIT license does not replace third-party licenses.\n')
    with zipfile.ZipFile(archive) as bundle:
        bad=bundle.testzip()
        if bad:raise ValueError('Corrupt archive member: '+bad)
    with archive.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    checksum=archive.with_suffix('.zip.sha256');checksum.write_text(digest+'  '+archive.name+'\n',encoding='utf-8')
    return archive,checksum


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--build',type=Path,default=ROOT/'dist/SOPCaptureStudio');parser.add_argument('--output',type=Path,default=ROOT/'dist/releases');parser.add_argument('--licenses',type=Path);args=parser.parse_args()
    version=tomllib.loads((ROOT/'pyproject.toml').read_text())['project']['version']
    for path in package(args.build,args.output,version,args.licenses):print(path)
