import os
import pytest
from sop_capture.windows import WindowsBackend, parse_hotkey


def test_hotkey_validation():
    assert parse_hotkey("Ctrl+Shift+F8") == (0x4006, 0x77)
    with pytest.raises(ValueError):
        parse_hotkey("F8")
    with pytest.raises(ValueError):
        parse_hotkey("Ctrl+Enter")


@pytest.mark.skipif(os.name != "nt", reason="Windows only")
def test_window_inventory_excludes_this_process():
    backend = WindowsBackend()
    try:
        assert all(w.pid != os.getpid() for w in backend.list_windows())
    finally:
        backend.close()
