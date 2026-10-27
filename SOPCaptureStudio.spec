# Build on Windows: python -m PyInstaller --noconfirm SOPCaptureStudio.spec
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('reportlab', includes=['fonts/*'])
a = Analysis(['run_studio.py'], pathex=[], binaries=[], datas=datas,
             hiddenimports=['PySide6.QtPdf', 'PySide6.QtPdfWidgets'],
             hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtQml', 'PySide6.QtQuick'],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='SOPCaptureStudio',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, uac_admin=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='SOPCaptureStudio')
