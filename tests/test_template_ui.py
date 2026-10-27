import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from sop_capture.models import Project
from sop_capture.storage import ProjectStore
from sop_capture.templates import TemplateLibrary
from sop_capture.ui.main_window import MainWindow
import pytest


def test_custom_template_save_select_and_reopen(tmp_path):
    app = QApplication.instance() or QApplication([])
    library = TemplateLibrary(tmp_path / "library")
    window = MainWindow(template_library=library)
    window.set_project(Project(title="Corporate SOP"), ProjectStore(tmp_path / "project"))
    page = window.templates_page
    page.new_custom()
    page.name.setText("Site procedure")
    page.fields["footer"].setText("Company controlled copy")
    profile = page.save_changes()
    assert profile["name"] == "Site procedure"
    window.apply_template(profile["id"])
    window.flush_save()
    assert window.store.load().template["name"] == "Site procedure"
    assert "Site procedure" in page.active_label.text()
    window.undo()
    assert window.project.template == {}
    window.redo()
    assert window.project.template["settings"]["footer"] == "Company controlled copy"
    assert window.export_to(tmp_path / "corporate.pdf").exists()
    window.close()


def test_failed_apply_preserves_template_and_undo_state(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    library = TemplateLibrary(tmp_path / "library")
    profile = library.save("New layout", {})
    window = MainWindow(template_library=library)
    window.set_project(Project(), ProjectStore(tmp_path / "project"))
    before_history, before_future = list(window.history), list(window.future)
    def fail(project): raise OSError("Disk unavailable")
    with monkeypatch.context() as patch:
        patch.setattr(window.store, "save", fail)
        with pytest.raises(OSError): window.apply_template(profile["id"])
    assert window.project.template == {}
    assert window.history == before_history and window.future == before_future
    window.close()


def test_new_template_respects_unsaved_changes(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    app = QApplication.instance() or QApplication([])
    window = MainWindow(template_library=TemplateLibrary(tmp_path / "library"))
    page = window.templates_page
    page.name.setText("Unsaved company layout")
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.No)
    page.new_custom()
    assert page.name.text() == "Unsaved company layout"
    window.close()
