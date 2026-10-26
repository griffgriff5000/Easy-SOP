"""Source and PyInstaller entry point (safe for Windows multiprocessing)."""
from sop_capture.app import main

if __name__ == "__main__":
    raise SystemExit(main())
