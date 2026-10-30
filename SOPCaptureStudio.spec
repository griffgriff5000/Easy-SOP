# Build on Windows: python -m PyInstaller --noconfirm SOPCaptureStudio.spec
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('reportlab', includes=['fonts/*'])
datas += [('sop_capture/assets/app.ico', 'sop_capture/assets')]
a = Analysis(['run_studio.py'], pathex=[], binaries=[], datas=datas,
             hiddenimports=['PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'win32com.client', 'win32timezone'],
             hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtQml', 'PySide6.QtQuick'],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='SOPCaptureStudio',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, uac_admin=False, icon='sop_capture/assets/app.ico')
helper = Analysis(['run_updater.py'], pathex=[], binaries=[], datas=[], hiddenimports=[],
                  hookspath=[], hooksconfig={}, runtime_hooks=[],
                  excludes=['PySide6','PIL','reportlab','docx','pdfplumber','win32com'], noarchive=False)
updater = EXE(PYZ(helper.pure), helper.scripts, helper.binaries, helper.datas, [],
              name='SOPCaptureUpdater', debug=False, strip=False, upx=False, console=False, uac_admin=False,
              icon='sop_capture/assets/app.ico')
coll = COLLECT(exe, updater, a.binaries, a.datas, strip=False, upx=False, name='SOPCaptureStudio')
