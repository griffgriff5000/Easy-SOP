import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from PySide6.QtWidgets import QApplication
from sop_capture.shortcuts import validate_profile, default_profile, run_sequence

@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])

def test_defaults_and_normalization():
    profile = default_profile()
    profile["bindings"]["add_step"] = "ctrl+shift+k"
    assert validate_profile(profile)["bindings"]["add_step"] == "Ctrl+Shift+K"

def test_conflicts_and_native_capture_key():
    profile = default_profile()
    profile["bindings"]["add_step"] = "Ctrl+N"
    with pytest.raises(ValueError, match="already"):
        validate_profile(profile)
    profile["bindings"]["add_step"] = "Ctrl+Shift+F8"
    with pytest.raises(ValueError, match="capture"):
        validate_profile(profile)

def test_sequences_validate_and_execute_in_order():
    profile = default_profile()
    profile["sequences"] = [{"id":"quick", "name":"Quick step", "shortcut":"Ctrl+Alt+K", "actions":["add_step", "tool_callout"]}]
    validated = validate_profile(profile)
    calls = []
    run_sequence(validated["sequences"][0], lambda action: calls.append(action) or True)
    assert calls == ["add_step", "tool_callout"]
    calls.clear()
    run_sequence(validated["sequences"][0], lambda action: calls.append(action) and False)
    assert calls == ["add_step"]
    profile["sequences"][0]["actions"] = ["export_pdf"]
    with pytest.raises(ValueError): validate_profile(profile)

@pytest.mark.parametrize("key", ["A", "Ctrl+C", "Ctrl+K, Ctrl+L", "not a key"])
def test_invalid_or_text_editing_keys(key):
    profile = default_profile(); profile["bindings"]["add_step"] = key
    with pytest.raises(ValueError): validate_profile(profile)

def test_unknown_actions_and_schema_rejected():
    profile=default_profile(); profile["bindings"]["shell"]="Ctrl+Alt+S"
    with pytest.raises(ValueError): validate_profile(profile)
    with pytest.raises(ValueError): validate_profile({"version":99})

def test_controller_rebinds_persists_and_runs_sequence(tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings, Qt
    from PySide6.QtTest import QTest
    from sop_capture.models import Project, Step
    from sop_capture.storage import ProjectStore
    from sop_capture.ui.main_window import MainWindow
    from sop_capture.ui import settings
    local = QSettings(str(tmp_path/'preferences.ini'), QSettings.Format.IniFormat)
    monkeypatch.setattr(settings, 'QSettings', lambda *args: local)
    window = MainWindow()
    window.set_project(Project(steps=[Step(title='Original')]), ProjectStore(tmp_path/'project'))
    profile = default_profile()
    profile['bindings']['add_step'] = 'Ctrl+Alt+K'
    profile['bindings']['help'] = 'Ctrl+Alt+H'
    profile['sequences'] = [{'id':'quick','name':'Add callout step','shortcut':'Ctrl+Alt+J','actions':['add_step','tool_callout']}]
    window.apply_shortcut_profile(profile)
    window.show();window.activateWindow();QApplication.processEvents()
    QTest.keyClick(window, Qt.Key.Key_K, Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.AltModifier)
    QApplication.processEvents()
    assert len(window.project.steps) == 2
    assert window.run_shortcut_sequence('quick')
    assert len(window.project.steps) == 3
    assert window.canvas.tool == 'callout'
    assert window.help_action.shortcut().toString() == 'Ctrl+Alt+H'
    window.busy=True
    assert not window.run_shortcut_sequence('quick')
    window.busy=False
    window.close()
    reopened=MainWindow()
    assert reopened.shortcut_profile == validate_profile(profile)
    assert not reopened.invoke_shortcut('duplicate_step')
    reopened.close()


def test_dialog_collects_edits_and_stages_changes(tmp_path):
    from sop_capture.ui.shortcuts_dialog import ShortcutsDialog, SequenceDialog
    profile=default_profile();saved=[]
    dialog=ShortcutsDialog(profile,lambda:'Ctrl+Shift+F8',saved.append)
    dialog.editors['add_step'].setKeySequence('Ctrl+Alt+K')
    assert profile['bindings']['add_step'] == ''
    assert dialog.apply()
    assert saved[0]['bindings']['add_step'] == 'Ctrl+Alt+K'
    sequence=SequenceDialog()
    sequence.name.setText('Add callout')
    sequence.add_action('add_step');sequence.add_action('tool_callout')
    sequence.move(-1)
    assert sequence.value()['actions'] == ['tool_callout','add_step']
    sequence.close();dialog.close()

@pytest.mark.parametrize('native, app_key', [('Win+K','Meta+K'),('Control+K','Ctrl+K')])
def test_native_capture_aliases_conflict(native, app_key):
    profile=default_profile();profile['bindings']['add_step']=app_key
    with pytest.raises(ValueError,match='capture'): validate_profile(profile,native)


def test_changing_native_capture_key_rejects_app_conflict(tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings
    from sop_capture.ui import settings
    from sop_capture.ui.main_window import MainWindow
    local=QSettings(str(tmp_path/'preferences.ini'),QSettings.Format.IniFormat)
    monkeypatch.setattr(settings,'QSettings',lambda *args:local)
    window=MainWindow()
    original=window.settings.value('shortcut')
    window.settings.fields['shortcut'].setText('Control+N')
    window._capture_shortcut_changed()
    assert window.settings.value('shortcut') == original
    assert local.value('shortcut') == original
    window.close()

def test_profile_file_roundtrip_stages_import(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    from sop_capture.ui.shortcuts_dialog import ShortcutsDialog
    saved=[]
    dialog=ShortcutsDialog(default_profile(),lambda:'Ctrl+Shift+F8',saved.append)
    output=tmp_path/'shortcuts.json'
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(output),''))
    dialog.editors['add_step'].setKeySequence('Ctrl+Alt+K')
    dialog.export_profile()
    assert output.is_file()
    dialog.editors['add_step'].clear()
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *args:(str(output),''))
    dialog.import_profile()
    assert dialog.collect()['bindings']['add_step']=='Ctrl+Alt+K'
    assert not saved
    dialog.close()


def test_invalid_saved_profile_falls_back_without_overwriting(tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings
    from sop_capture.ui import settings
    from sop_capture.ui.main_window import MainWindow
    local=QSettings(str(tmp_path/'preferences.ini'),QSettings.Format.IniFormat)
    local.setValue('shortcuts_profile','broken json')
    monkeypatch.setattr(settings,'QSettings',lambda *args:local)
    window=MainWindow()
    assert window.shortcut_profile==default_profile()
    assert local.value('shortcuts_profile')=='broken json'
    window.close()
