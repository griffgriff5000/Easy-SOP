from PIL import Image
from PySide6.QtGui import QIcon

from sop_capture.branding import application_icon_path


def test_application_icon_contains_clear_small_and_large_windows_sizes(qt_application):
    path = application_icon_path()
    with Image.open(path) as icon:
        assert {(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)} <= icon.ico.sizes()
        assert icon.convert('RGBA').getpixel((0, 0))[3] == 0
    qt_icon = QIcon(str(path))
    assert not qt_icon.isNull()
    for size in (16, 32, 48, 256):
        assert not qt_icon.pixmap(size, size).isNull()
