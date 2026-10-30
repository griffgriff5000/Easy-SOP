"""Standalone updater entry point, frozen separately without Qt."""
from sop_capture.update_install import main

if __name__=='__main__':raise SystemExit(main())
