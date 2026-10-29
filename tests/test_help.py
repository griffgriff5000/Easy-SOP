import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from sop_capture.ui.main_window import MainWindow


def test_f1_opens_offline_guide_without_project_and_navigates():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    app.processEvents()
    QTest.keyClick(window, Qt.Key.Key_F1)
    app.processEvents()
    guide = window.help_dialog
    assert guide.isVisible()
    assert "New project" in guide.browser.toPlainText()
    assert "Recent projects" in guide.browser.toPlainText()
    guide.show_topic("Annotations")
    assert "Arrow style" in guide.browser.toPlainText()
    assert "Esc" in guide.browser.toPlainText()
    window.show_help()
    assert window.help_dialog is guide
    window.close()


def test_shortcut_help_uses_current_capture_shortcut():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    # Change only the in-memory widget; do not overwrite the user's settings.
    widget = window.settings.fields["shortcut"]
    widget.blockSignals(True)
    widget.setText("Ctrl+Alt+F9")
    widget.blockSignals(False)
    window.show_help("Keyboard shortcuts")
    assert "Ctrl+Alt+F9" in window.help_dialog.browser.toPlainText()
    window.close()
