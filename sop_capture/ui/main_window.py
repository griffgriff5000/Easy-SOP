"""Main desktop workflow. All project mutations happen on the Qt thread."""
from copy import deepcopy
from datetime import datetime
import logging
from pathlib import Path
import re
import tempfile
import threading
import time
import uuid

from PIL import Image, ImageColor
from PySide6.QtCore import QObject, Signal, Qt, QTimer, QSize, QUrl, QStandardPaths, QBuffer, QIODevice
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence, QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QStackedWidget, QFrame, QFileDialog,
    QMessageBox, QInputDialog, QLineEdit, QPlainTextEdit, QFormLayout,
    QScrollArea, QSplitter, QComboBox, QCheckBox, QDialog, QAbstractItemView,
    QButtonGroup, QSpinBox, QDoubleSpinBox, QColorDialog, QTabWidget, QToolButton, QMenu,
)

from ..capture import CaptureSession, CaptureOptions
from ..models import Project, Step, Annotation
from ..storage import ProjectStore, atomic_bytes
from ..document_export import export_pdf
from ..imaging import render_step, render_image
from ..windows import WindowsBackend, NativeInput, parse_hotkey
from .canvas import AnnotationCanvas, image_pixmap
from .settings import SettingsPage
from .theme import stylesheet
from .components import page_header, menu_button, form_page, scroll_panel, ThumbnailDelegate

log = logging.getLogger(__name__)


class Bridge(QObject):
    captured = Signal(object)
    notice = Signal(str)
    completed = Signal(object, object, object)



def button(text, callback, primary=False):
    widget = QPushButton(text)
    widget.clicked.connect(callback)
    if primary:
        widget.setObjectName("primary")
    return widget


def heading(layout, title, subtitle):
    page_header(layout, title, subtitle)


def scroll(widget):
    widget.setObjectName("scrollPage")
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(widget)
    return area


class MainWindow(QMainWindow):
    def __init__(self, template_library=None,recent_projects=None,annotation_library=None):
        super().__init__()
        self.setWindowTitle("SOP Capture Studio")
        self.resize(1320, 900)
        self.setMinimumSize(1000, 700)
        self.project = self.store = self.target = None
        self.template_library = template_library
        self.annotation_library_override=annotation_library
        from ..recent_projects import RecentProjects
        self.recent_projects=recent_projects if recent_projects is not None else RecentProjects(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))/'recent-projects.json')
        self.session = self.native_input = None
        self.history, self.future = [], []
        self.loading = False
        self.styling = False
        self.busy = False
        self.last_tick = time.monotonic()
        self.elapsed = 0.0
        self.bridge = Bridge(self)
        self.bridge.captured.connect(self._captured)
        self.bridge.notice.connect(self.notice)
        self.bridge.completed.connect(self._task_done)
        self.background_threads = set()
        try:
            self.backend = WindowsBackend()
        except Exception:
            self.backend = None
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(450)
        self.save_timer.timeout.connect(self._autosave)
        self.clock = QTimer(self)
        self.clock.setInterval(250)
        self.clock.timeout.connect(self._tick)
        self.clock.start()
        self.preview_dir = tempfile.TemporaryDirectory(prefix="sop-preview-")
        self._build()
        self.setStyleSheet(stylesheet(self.settings.value("theme") == "Dark"))
        self._actions()
        self._update_controls()

    def _build(self):
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(168)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(10, 16, 10, 12)
        brand = QLabel("SOP\nCapture Studio")
        brand.setStyleSheet("font-size: 18px; font-weight: 600; padding: 4px 0 20px;")
        side.addWidget(brand)
        self.pages = QStackedWidget()
        self.nav_group = QButtonGroup(self)
        self.nav_buttons = []
        self.home_nav=button('Home',lambda:self.show_page(5));self.home_nav.setCheckable(True);self.nav_group.addButton(self.home_nav);side.addWidget(self.home_nav)
        for index, text in enumerate(("Capture", "Step editor", "Document", "Settings", "Templates")):
            nav = button(text, lambda checked=False, i=index: self.show_page(i))
            nav.setCheckable(True)
            self.nav_group.addButton(nav)
            self.nav_buttons.append(nav)
            side.addWidget(nav)
        self.annotation_nav=button('Annotation library',lambda:self.show_page(6));self.annotation_nav.setCheckable(True);self.nav_group.addButton(self.annotation_nav);side.addWidget(self.annotation_nav)
        self.nav_buttons.extend([self.home_nav,self.annotation_nav])
        side.addStretch()
        local = QLabel("LOCAL BY DESIGN\nYour captures stay on this PC.")
        local.setWordWrap(True)
        local.setStyleSheet("font-size: 9pt; padding: 8px 0;")
        side.addWidget(local)
        side.addWidget(button("Help", self.show_help))
        side.addWidget(button("Open logs", self.open_logs))
        self.pages.addWidget(self._capture_page())
        self.pages.addWidget(self._editor_page())
        self.pages.addWidget(self._document_page())
        self.settings = SettingsPage(lambda dark: self.setStyleSheet(stylesheet(dark)))
        self.pages.addWidget(scroll(self.settings))
        from ..templates import TemplateLibrary
        from .templates_page import TemplatesPage
        if self.template_library is None:
            self.template_library = TemplateLibrary(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)) / "templates")
        self.templates_page = TemplatesPage(self.template_library, self.apply_template, self.preview_pdf,library_preview_callback=self.preview_template)
        self.pages.addWidget(self.templates_page)
        from .home_page import HomePage
        self.home_page=HomePage();self.pages.addWidget(self.home_page)
        self.home_page.new_requested.connect(self.new_project);self.home_page.browse_requested.connect(self.open_project)
        self.home_page.templates_requested.connect(lambda:self.show_page(4));self.home_page.annotations_requested.connect(lambda:self.show_page(6))
        self.home_page.open_requested.connect(self.open_project_path);self.home_page.remove_requested.connect(self.remove_recent_project);self.home_page.continue_requested.connect(lambda:self.show_page(1))
        from .annotation_library_page import AnnotationLibraryPage
        self.annotation_library_page=AnnotationLibraryPage(self._annotation_library());self.pages.addWidget(self.annotation_library_page)
        self.annotation_library_page.changed.connect(self.refresh_saved_annotations);self.annotation_library_page.changed.connect(self._refresh_home)
        self.annotation_library_page.use_requested.connect(self.use_library_annotation)
        layout.addWidget(sidebar)
        layout.addWidget(self.pages, 1)
        self.setCentralWidget(root)
        self.show_page(5)
        self.statusBar().showMessage("Ready. Create or open an SOP to begin.")
        self.floating = QDialog(self, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.floating.setWindowTitle("SOP capture controls")
        self.floating.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)
        box = QHBoxLayout(self.floating)
        self.float_status = QLabel("● Recording")
        self.float_pause = button("Pause", self.toggle_pause)
        self.float_stop = button("Stop", self.stop_capture)
        self.float_stop.setObjectName("danger")
        box.addWidget(self.float_status)
        box.addWidget(self.float_pause)
        box.addWidget(self.float_stop)
        self.floating.setFixedSize(430, 70)
        # Closing the floating controls stops recording rather than hiding its indicator.
        self.floating.rejected.connect(self.stop_capture)

    def _actions(self):
        import json
        from ..shortcuts import default_profile, validate_profile, normalize_capture_key
        self.shortcut_actions = []
        self.sequence_running = False
        self.shortcut_profile = default_profile()
        raw = self.settings.settings.value("shortcuts_profile", "")
        warning = None
        try:
            self.shortcut_profile = validate_profile(json.loads(raw) if raw else default_profile(), self.settings.value("shortcut"))
        except (ValueError, TypeError) as exc:
            warning = f"Shortcut profile reset: {exc}"
            try: reserved = normalize_capture_key(self.settings.value("shortcut"))
            except ValueError: reserved = ""
            for action, key in self.shortcut_profile["bindings"].items():
                if key == reserved: self.shortcut_profile["bindings"][action] = ""
        self.apply_shortcut_profile(self.shortcut_profile, persist=False)
        self.last_capture_shortcut = self.settings.value("shortcut")
        self.settings.fields["shortcut"].editingFinished.connect(self._capture_shortcut_changed)
        self._populate_action_menus()
        shortcut_button = button("Customise shortcuts...", self.show_shortcuts)
        self.settings.actions.addWidget(shortcut_button)
        self.settings.actions.addWidget(button("Annotation Studio", self.show_annotation_studio))
        self.settings.actions.addStretch()
        if warning: QTimer.singleShot(0, lambda: self.notice(warning))

    def apply_shortcut_profile(self, profile, persist=True):
        import json
        from ..shortcuts import ACTIONS, validate_profile
        profile = validate_profile(profile, self.settings.value("shortcut"))
        if persist:
            self.settings.settings.setValue("shortcuts_profile", json.dumps(profile))
            self.settings.settings.sync()
            if self.settings.settings.status() != self.settings.settings.Status.NoError:
                raise OSError("Could not save shortcut preferences.")
        for action in self.shortcut_actions:
            self.removeAction(action)
            action.deleteLater()
        self.shortcut_actions = []
        self.action_bindings = {}
        self.shortcut_profile = profile
        for identity, details in ACTIONS.items():
            action = QAction(details[0], self)
            action.setShortcut(QKeySequence(profile["bindings"][identity]))
            action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
            action.triggered.connect(lambda checked=False, key=identity: self.invoke_shortcut(key))
            self.addAction(action)
            self.shortcut_actions.append(action)
            self.action_bindings[identity] = action
        for sequence in profile["sequences"]:
            action = QAction(sequence["name"], self)
            action.setShortcut(QKeySequence(sequence["shortcut"]))
            action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
            action.triggered.connect(lambda checked=False, key=sequence["id"]: self.run_shortcut_sequence(key))
            self.addAction(action)
            self.shortcut_actions.append(action)
        if hasattr(self,"app_menus"):self._populate_action_menus()
        self._update_controls()

    def _populate_action_menus(self):
        if not hasattr(self,"app_menus"):
            self.app_menus={name:self.menuBar().addMenu("&"+name) for name in ("File","Edit","View","Settings","Help")}
        for menu in self.app_menus.values():menu.clear()
        groups={"File":["new","open","save",None,"preview_pdf","export_pdf","export_word"],
                "Edit":["undo","redo",None,"add_step","duplicate_step","delete_step",None,"move_up","move_down","group_steps","rename_section"],
                "View":["page_5","page_0","page_1","page_2","page_4","page_6","page_3",None,"annotation_studio"],
                "Settings":["page_3","shortcuts"]}
        for name,identities in groups.items():
            for identity in identities:
                if identity is None:self.app_menus[name].addSeparator()
                else:self.app_menus[name].addAction(self.action_bindings[identity])
        self.help_menu=self.app_menus["Help"];self.help_action=self.action_bindings["help"]
        self.help_menu.addAction(self.help_action);self.help_menu.addAction("Keyboard shortcuts",self.show_shortcuts)
        self.help_menu.addSeparator();self.help_menu.addAction("Open logs",self.open_logs);self.help_menu.addAction("About SOP Capture Studio",self.show_about)

    def _capture_shortcut_changed(self):
        from ..shortcuts import validate_profile
        value = self.settings.value("shortcut")
        try:
            parse_hotkey(value)
            validate_profile(self.shortcut_profile, value)
        except ValueError as exc:
            self.settings.fields["shortcut"].setText(self.last_capture_shortcut)
            self.notice(f"Manual capture shortcut unchanged: {exc}")
            return
        self.last_capture_shortcut = value

    def show_annotation_studio(self):
        if self.active or self.busy: return
        from ..designs import AnnotationLibrary, from_annotation
        from .annotation_studio import AnnotationStudio
        library = self._annotation_library()
        step = self.current_step()
        selected = self.canvas.selected if step is not None and self.canvas.step is step else None
        design = None
        bounds = None
        if selected is not None:
            annotation = step.annotations[selected]
            if annotation.kind=='magnifier':
                self.notice('Magnifiers use the screenshot. Adjust magnification in the Annotation panel.');return
            if annotation.kind in {"redact", "blur"}:
                self.notice("Select a shape to customise. Redaction and blur masks stay in the screenshot editor.")
                return
            try: design,bounds = from_annotation(annotation, self.canvas.original.size if self.canvas.original else None)
            except ValueError as exc: self.fail(exc);return
        studio = AnnotationStudio(library, design, bool(step and self.canvas.original is not None), self)
        result=studio.exec()
        self.refresh_saved_annotations()
        self.annotation_library_page.refresh()
        if result != QDialog.DialogCode.Accepted: return
        snapshot = deepcopy(studio.document.design)
        self.selected_saved_annotation=None
        self.canvas.design_template = snapshot
        self._sync_annotation_gallery()
        if selected is not None:
            previous = step.annotations[selected]
            if previous.kind == "design" and previous.design == snapshot and previous.points == bounds: return
            self.checkpoint()
            step.annotations[selected] = Annotation(kind="design", points=bounds, design=deepcopy(snapshot))
            self.canvas.refresh()
            self.edited()
            self.notice("Annotation updated. Reopen Annotation Studio to edit its layers.")
        else:
            self.tool_picker.setCurrentIndex(self.tool_picker.findData("design"))
            self.canvas.set_tool("design")
            self.notice("Drag on the screenshot to preview and place this design. Esc cancels placement.")

    def _annotation_library(self):
        from ..designs import AnnotationLibrary
        if self.annotation_library_override is not None:return self.annotation_library_override
        return AnnotationLibrary(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))/'annotations')

    def _update_library_save_button(self,*args):
        step=self.current_step();index=self.canvas.selected
        supported=bool(step and index is not None and index<len(step.annotations) and step.annotations[index].kind in {'design','arrow','line','circle','highlight','highlighter','text','callout'})
        self.save_annotation_library_button.setEnabled(supported and not self.active and not self.busy)

    def save_selected_annotation(self):
        step=self.current_step();index=self.canvas.selected
        if self.active or self.busy or not step or index is None or index>=len(step.annotations):return
        annotation=step.annotations[index]
        if annotation.kind not in {'design','arrow','line','circle','highlight','highlighter','text','callout'}:
            self.notice('Magnifier, redaction and blur are default screenshot tools, rather than reusable artwork.');return
        name,accepted=QInputDialog.getText(self,'Save annotation to library','Name for reuse across all projects:',text=annotation.text[:120] or 'My annotation')
        if not accepted or not name.strip():return
        try:
            from ..designs import from_annotation
            design,_=from_annotation(annotation,self.canvas.original.size if self.canvas.original else None)
            identity=self._annotation_library().save(name.strip(),design)
            self.refresh_saved_annotations()
            self.annotation_library_page.refresh(identity)
            self.notice(f'Saved "{name.strip()}" to the annotation library. Available in all projects.')
            return identity
        except (ValueError,OSError) as exc:self.fail(exc)

    def refresh_saved_annotations(self):
        from ..designs import render_design
        gallery=self.annotation_gallery;gallery.clear_custom()
        library=self._annotation_library()
        for identity,name in library.entries():
            try:
                _,design=library.load(identity)
                width,height=design['size'];ratio=min(96/width,48/height)
                preview=render_design(design,(max(1,round(width*ratio)),max(1,round(height*ratio))))
                gallery.add_custom(identity,name,QIcon(image_pixmap(preview)))
            except (ValueError,OSError):log.warning('A saved annotation preview could not be loaded',exc_info=True)
        self._sync_annotation_gallery()

    def _sync_annotation_gallery(self,*args):
        self.annotation_gallery.select(self.tool_picker.currentData(),getattr(self,'selected_saved_annotation',None))

    def _choose_annotation_tool(self,kind):
        if self.active or self.busy:return
        self.tool_picker.setCurrentIndex(self.tool_picker.findData(kind))
        self.canvas.set_tool(kind)
        self.editor_inspector.setCurrentIndex(1);self.inspector_toggle.setChecked(True)

    def _choose_saved_annotation(self,identity):
        if not identity or self.active or self.busy:return
        try:
            _,design=self._annotation_library().load(identity)
            self.canvas.design_template=deepcopy(design)
            self.selected_saved_annotation=identity
            self.tool_picker.setCurrentIndex(self.tool_picker.findData('design'))
            self.canvas.set_tool('design');self._sync_annotation_gallery()
            self.editor_inspector.setCurrentIndex(1);self.inspector_toggle.setChecked(True)
            self.notice('Drag on the screenshot to place this custom annotation. Esc cancels placement.')
        except (ValueError,OSError) as exc:
            self.refresh_saved_annotations();self.fail(exc)

    def show_shortcuts(self):
        if self.active or self.busy: return
        from .shortcuts_dialog import ShortcutsDialog
        ShortcutsDialog(self.shortcut_profile, lambda: self.settings.value("shortcut"), self.apply_shortcut_profile, self).exec()

    def invoke_shortcut(self, identity):
        from ..shortcuts import ACTIONS
        from PySide6.QtWidgets import QApplication
        if QApplication.activeModalWidget() is not None: return False
        context = ACTIONS[identity][3]
        allowed = context == "any" or (context == "recording" and self.active) or (
            context != "recording" and not self.active and not self.busy and
            (context == "idle" or (self.project is not None and (context != "step" or self.current_step() is not None))))
        if not allowed:
            self.notice("This action is unavailable in the current state.")
            return False
        if identity in {"move_up", "move_down"}:
            target = self.steps_list.currentRow()+(-1 if identity == "move_up" else 1)
            if not 0 <= target < len(self.project.steps): return False
        if identity == "delete_annotation" and self.canvas.selected is None: return False
        if identity == "remove_marker" and self.current_step().marker is None: return False
        if identity.startswith("tool_"):
            self.show_page(1)
            self.tool_picker.setCurrentIndex(self.tool_picker.findData(identity[5:]))
        elif identity.startswith("page_"):
            self.show_page(int(identity[5:]))
        elif identity in {"next_step", "previous_step"}:
            row = self.steps_list.currentRow()+(1 if identity == "next_step" else -1)
            if not 0 <= row < len(self.project.steps): return False
            self.steps_list.setCurrentRow(row)
        else:
            callbacks = {
                "new": self.new_project, "open": self.open_project, "save": self.flush_save,
                "undo": self.undo, "redo": self.redo, "add_step": self.add_step,
                "duplicate_step": self.duplicate_step, "delete_step": self.delete_step,
                "move_up": lambda: self.move_step(-1), "move_down": lambda: self.move_step(1),
                "group_steps": self.group_steps_dialog, "rename_section": self.rename_section_dialog,
                "review": self.show_review, "preview_pdf": self.preview_pdf,
                "export_pdf": self.export_dialog, "export_word": self.export_word_dialog,
                "replace_image": self.replace_image, "retake_image": self.retake_image,
                "save_png": self.save_annotated, "delete_annotation": self.canvas.delete_selected,
                "remove_marker": self.remove_marker, "capture_start": self.start_capture,
                "capture_pause": self.toggle_pause, "capture_stop": self.stop_capture,
                "help": self.show_help, "shortcuts": self.show_shortcuts, "annotation_studio": self.show_annotation_studio,
            }
            try: callbacks[identity]()
            except Exception as exc:
                self.fail(exc)
                return False
        return True

    def run_shortcut_sequence(self, identity):
        from ..shortcuts import run_sequence
        if self.sequence_running or self.active or self.busy: return False
        sequence = next((row for row in self.shortcut_profile["sequences"] if row["id"] == identity), None)
        if sequence is None: return False
        self.sequence_running = True
        try:
            result = run_sequence(sequence, self.invoke_shortcut)
            self.notice(f"{sequence['name']}: {'completed' if result else 'stopped; an action was unavailable'}")
            return result
        finally: self.sequence_running = False

    def show_help(self, topic="Getting started"):
        from .help_dialog import UserGuideDialog
        if not hasattr(self, "help_dialog"):
            self.help_dialog = UserGuideDialog(self)
        self.help_dialog.show_topic(topic, self.settings.value("shortcut"))
        self.help_dialog.show()
        self.help_dialog.raise_()
        self.help_dialog.activateWindow()

    def show_about(self):
        from .. import __version__
        QMessageBox.about(self, "About SOP Capture Studio", f"SOP Capture Studio {__version__}\n\nRecord a selected Windows application, edit illustrated steps and export a procedure PDF.\n\nLocal processing. No account or API key required.\n\nPress F1 for the user guide.")

    def _capture_page(self):
        page = QWidget()
        box = QVBoxLayout(page)
        box.setSpacing(14)
        heading(box, "Capture", "Choose an application window and record the steps of your process.")
        row = QHBoxLayout()
        self.new_button = button("＋  New SOP", self.new_project)
        self.open_button = button("Open SOP", self.open_project)
        self.screenshots_button = button("Screenshots folder", self.open_screenshots)
        for item in (self.new_button, self.open_button, self.screenshots_button): row.addWidget(item)
        row.addStretch()
        box.addLayout(row)
        self.project_label = QLabel("No project open")
        self.project_label.setObjectName("status")
        self.project_label.setWordWrap(True)
        box.addWidget(self.project_label)
        row = QHBoxLayout()
        row.addWidget(QLabel("Application window"))
        row.addStretch()
        self.refresh_button = button("Refresh windows", self.refresh_windows)
        self.preview_button = button("Preview selection", self.preview_target)
        row.addWidget(self.refresh_button)
        row.addWidget(self.preview_button)
        row.addWidget(menu_button("Options",[("Windows notification settings",lambda:QDesktopServices.openUrl(QUrl("ms-settings:notifications")))]))
        box.addLayout(row)
        split = QSplitter()
        self.windows_list = QListWidget()
        self.windows_list.currentItemChanged.connect(self._target_selected)
        self.window_preview = QLabel("Choose a window and select Preview.\nOnly that window is captured.")
        self.window_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.window_preview.setWordWrap(True)
        self.window_preview.setMinimumSize(330, 220)
        self.window_preview.setStyleSheet("background: #dfe8f0; color: #36556d; border-radius: 10px;")
        split.addWidget(self.windows_list)
        split.addWidget(self.window_preview)
        split.setSizes([400, 480])
        box.addWidget(split, 1)
        note = QLabel("Notifications: enable Windows Do Not Disturb manually before recording.\nThis app does not change notification settings. Visible sensitive data can appear in screenshots.")
        note.setWordWrap(True)
        note.setObjectName("caption")
        box.addWidget(note)
        controls = QHBoxLayout()
        self.start_button = button("●  Start capture", self.start_capture, True)
        self.pause_button = button("Pause", self.toggle_pause)
        self.stop_button = button("Stop capture", self.stop_capture)
        self.stop_button.setObjectName("danger")
        self.capture_status = QLabel("Ready   •   00:00   •   0 screenshots")
        controls.addWidget(self.start_button)
        controls.addWidget(self.pause_button)
        controls.addWidget(self.stop_button)
        controls.addWidget(self.capture_status, 1)
        box.addLayout(controls)
        return page

    def _editor_page(self):
        page = QWidget();box = QVBoxLayout(page);box.setSpacing(10)
        heading(box, "Step editor", "Arrange steps, explain the process and annotate screenshots.")
        actions = QHBoxLayout()
        actions.addWidget(button("Undo", self.undo));actions.addWidget(button("Redo", self.redo))
        actions.addWidget(button("Annotation Studio", self.show_annotation_studio))
        actions.addStretch()
        actions.addWidget(button("Review", self.show_review))
        self.preview_pdf_button = button("Preview", self.preview_pdf);actions.addWidget(self.preview_pdf_button)
        self.export_button = menu_button("Export", [("Export PDF...",self.export_dialog),("Export Word...",self.export_word_dialog),(None,None),("Choose template",lambda:self.show_page(4))])
        self.export_button.setObjectName("primary");actions.addWidget(self.export_button);box.addLayout(actions)
        splitter = QSplitter();self.editor_splitter = splitter
        steps = QWidget();steps_box = QVBoxLayout(steps);steps_box.setContentsMargins(0,0,0,0)
        step_actions = QHBoxLayout();step_actions.addWidget(button("Add step", self.add_step),1)
        step_actions.addWidget(menu_button("Actions",[("Duplicate step",self.duplicate_step),("Delete step",self.delete_step),(None,None),("Move up",lambda:self.move_step(-1)),("Move down",lambda:self.move_step(1)),(None,None),("Group steps...",self.group_steps_dialog),("Rename section...",self.rename_section_dialog)]))
        steps_box.addLayout(step_actions)
        self.steps_list = QListWidget();self.steps_list.setMinimumWidth(160);self.steps_list.setItemDelegate(ThumbnailDelegate(self.steps_list));self.steps_list.setIconSize(QSize(130,72));self.steps_list.setWordWrap(True)
        self.steps_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.steps_list.currentRowChanged.connect(self._select_step);self.steps_list.model().rowsMoved.connect(self._list_reordered)
        steps_box.addWidget(self.steps_list,1);splitter.addWidget(steps)
        self.editor_panel = QWidget();workspace = QVBoxLayout(self.editor_panel);workspace.setContentsMargins(0,0,0,0);workspace.setSpacing(8)
        tools = QHBoxLayout();self.tool_picker = QComboBox();self.tool_picker.setMaximumWidth(185)
        for label,tool in [("Select / edit","edit"),("Click marker","marker"),("Arrow","arrow"),("Straight line","line"),("Circle / ellipse","circle"),("Magnifier","magnifier"),("Outline box","highlight"),("Translucent highlight","highlighter"),("Custom design","design"),("Text callout","callout"),("Text label","text"),("Redaction","redact"),("Blur","blur")]:self.tool_picker.addItem(label,tool)
        self.canvas = AnnotationCanvas()
        self.canvas.changing.connect(self.checkpoint);self.canvas.changed.connect(self.edited)
        tools.addWidget(self.tool_picker)
        tools.addWidget(menu_button("Screenshot",[("Replace screenshot...",self.replace_image),("Retake selected window",self.retake_image),("Save annotated PNG...",self.save_annotated),(None,None),("Remove last annotation",self.remove_annotation)]))
        tools.addStretch()
        self.editor_zoom = QComboBox();self.editor_zoom.setAccessibleName("Screenshot zoom")
        for label,value in [("Fit",1),("125%",1.25),("150%",1.5),("200%",2)]:self.editor_zoom.addItem(label,value)
        self.editor_zoom.currentIndexChanged.connect(lambda:self.canvas.set_zoom(self.editor_zoom.currentData()))
        self.editor_zoom.activated.connect(lambda:self.canvas.set_zoom(self.editor_zoom.currentData()))
        tools.addWidget(self.editor_zoom)
        self.inspector_toggle = QToolButton();self.inspector_toggle.setText("Details");self.inspector_toggle.setCheckable(True);self.inspector_toggle.setChecked(True);tools.addWidget(self.inspector_toggle)
        workspace.addLayout(tools)
        panels = QSplitter();self.editor_workspace = panels;panels.addWidget(self.canvas)
        self.editor_inspector = QTabWidget();self.editor_inspector.setMinimumWidth(240);self.editor_inspector.setMaximumWidth(340)
        instruction_page = QWidget();instruction_page.setObjectName("scrollPage");instructions = QVBoxLayout(instruction_page);instructions.setSpacing(10)
        self.step_title = QLineEdit();self.step_title.setPlaceholderText("What should the reader do?")
        self.step_title.textChanged.connect(self._step_fields_changed)
        instructions.addWidget(QLabel("Step title"));instructions.addWidget(self.step_title)
        self.step_section = QLineEdit();self.step_section.setMaxLength(120);self.step_section.setPlaceholderText("Optional stage / section")
        self.step_section.textEdited.connect(self._step_fields_changed);instructions.addWidget(QLabel("Section"));instructions.addWidget(self.step_section)
        self.step_description = QPlainTextEdit();self.step_description.setPlaceholderText("Explain this step...");self.step_description.setMinimumHeight(160)
        self.step_description.textChanged.connect(self._step_fields_changed);instructions.addWidget(QLabel("Instructions"));instructions.addWidget(self.step_description,1)
        self.step_notes = QLineEdit();self.step_notes.setPlaceholderText("Optional notes or warnings");self.step_notes.textChanged.connect(self._step_fields_changed)
        instructions.addWidget(QLabel("Notes / warnings"));instructions.addWidget(self.step_notes)
        self.selected_template_label = QLabel("Template: Standard SOP");self.selected_template_label.setWordWrap(True);self.selected_template_label.setObjectName("caption");instructions.addWidget(self.selected_template_label)
        self.editor_inspector.addTab(scroll_panel(instruction_page),"Instructions")
        properties,self.annotation_form = form_page()
        from .annotation_gallery import AnnotationGallery
        self.annotation_gallery=AnnotationGallery([(self.tool_picker.itemText(i),self.tool_picker.itemData(i)) for i in range(self.tool_picker.count())])
        self.annotation_gallery.tool_chosen.connect(self._choose_annotation_tool)
        self.annotation_gallery.design_chosen.connect(self._choose_saved_annotation)
        self.annotation_gallery.refresh_requested.connect(self.refresh_saved_annotations)
        self.tool_picker.currentIndexChanged.connect(self._sync_annotation_gallery)
        self.annotation_form.addRow(self.annotation_gallery)
        self.refresh_saved_annotations()
        self.annotation_colour = button("Choose colour...",self.choose_annotation_colour)
        self.annotation_form.addRow("Colour",self.annotation_colour)
        self.annotation_width = QSpinBox();self.annotation_width.setRange(1,30);self.annotation_width.setSuffix(" px");self.annotation_form.addRow("Stroke",self.annotation_width)
        self.annotation_zoom=QDoubleSpinBox();self.annotation_zoom.setRange(1.25,5);self.annotation_zoom.setSingleStep(.25);self.annotation_zoom.setDecimals(2);self.annotation_zoom.setSuffix(' x');self.annotation_zoom.setValue(2)
        self.annotation_zoom.valueChanged.connect(lambda value:self._annotation_style_changed('zoom',value));self.annotation_form.addRow('Magnification',self.annotation_zoom)
        self.annotation_font_size = QSpinBox();self.annotation_font_size.setRange(8,144);self.annotation_font_size.setSuffix(" px");self.annotation_form.addRow("Text size",self.annotation_font_size)
        self.annotation_opacity = QSpinBox();self.annotation_opacity.setRange(0,100);self.annotation_opacity.setSuffix(" %");self.annotation_form.addRow("Opacity",self.annotation_opacity)
        self.arrow_style_picker = QComboBox();self.arrow_style_picker.setIconSize(QSize(128,36));self.arrow_style_picker.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);self.arrow_style_picker.setMinimumContentsLength(6)
        for label,value in [("Solid arrow","solid"),("Open arrow","open"),("Double-headed arrow","double")]:
            sample = Step(annotations=[Annotation(kind="arrow",points=[12,18,116,18],width=3,color="#2563eb",arrow_style=value)])
            icon = QIcon(image_pixmap(render_image(Image.new("RGB",(128,36),"white"),sample,1)));self.arrow_style_picker.addItem(icon,label,value)
        self.arrow_style_picker.currentIndexChanged.connect(lambda:self._annotation_style_changed("arrow_style",self.arrow_style_picker.currentData()))
        self.annotation_form.addRow("Arrow style",self.arrow_style_picker)
        self.annotation_text = QLineEdit("Text label");self.annotation_text.setMaxLength(5000);self.annotation_text.setPlaceholderText("Label text");self.annotation_form.addRow("Text",self.annotation_text)
        self.marker_row = QWidget();marker_layout = QVBoxLayout(self.marker_row);marker_layout.setContentsMargins(0,0,0,0)
        self.marker_check = QCheckBox("Show click marker");self.marker_check.toggled.connect(self._marker_toggled);marker_layout.addWidget(self.marker_check)
        marker_layout.addWidget(button("Remove marker",self.remove_marker));self.annotation_form.addRow(self.marker_row)
        self.delete_annotation_button = button("Delete selected",self.canvas.delete_selected);self.delete_annotation_button.setEnabled(False)
        self.canvas.selection_changed.connect(self.delete_annotation_button.setEnabled)
        self.canvas.selection_changed.connect(lambda selected:(self.editor_inspector.setCurrentIndex(1),self.inspector_toggle.setChecked(True)) if selected else None)
        self.annotation_form.addRow(self.delete_annotation_button)
        self.save_annotation_library_button=button('Save selected to library',self.save_selected_annotation)
        self.save_annotation_library_button.setToolTip('Save a named reusable copy for all projects. Existing project annotations stay independent.')
        self.save_annotation_library_button.setEnabled(False)
        self.canvas.selection_changed.connect(self._update_library_save_button)
        self.annotation_form.addRow(self.save_annotation_library_button)
        self.custom_design_help = QLabel("Open Annotation Studio to create a design or edit its layers.");self.custom_design_help.setWordWrap(True);self.annotation_form.addRow(self.custom_design_help)
        self.annotation_form.addRow(button("Open Annotation Studio",self.show_annotation_studio))
        self.editor_inspector.addTab(scroll_panel(properties),"Annotation")
        panels.addWidget(self.editor_inspector);panels.setSizes([600,280]);panels.setStretchFactor(0,1);panels.setCollapsible(0,False);panels.setCollapsible(1,False)
        self.inspector_toggle.toggled.connect(self.editor_inspector.setVisible)
        workspace.addWidget(panels,1)
        hint = QLabel("Drag to preview, release to place. Esc cancels. Middle-drag pans when zoomed.");hint.setObjectName("caption");hint.setWordWrap(True);workspace.addWidget(hint)
        splitter.addWidget(self.editor_panel);splitter.setSizes([200,900]);splitter.setStretchFactor(1,1);splitter.setCollapsible(0,False);splitter.setCollapsible(1,False);box.addWidget(splitter,1)
        def choose_tool():
            self.canvas.set_tool(self.tool_picker.currentData())
            self.editor_inspector.setCurrentIndex(1);self.inspector_toggle.setChecked(True)
        self.tool_picker.currentIndexChanged.connect(choose_tool)
        for widget,name in [(self.annotation_width,"width"),(self.annotation_font_size,"font_size"),(self.annotation_opacity,"opacity")]:widget.valueChanged.connect(lambda value,key=name:self._annotation_style_changed(key,value))
        self.annotation_text.textChanged.connect(lambda value:self._annotation_style_changed("text",value))
        self.canvas.style_changed.connect(self._sync_annotation_controls)
        self.canvas.set_tool("edit");self._sync_annotation_controls()
        return page

    def _document_page(self):
        page = QWidget();box = QVBoxLayout(page);box.setSpacing(10)
        heading(box,"Document","Edit your company document and SOP directly on the pages.")
        row=QHBoxLayout();row.addStretch();row.addWidget(button('Fill template fields',self.show_template_fields));row.addWidget(button("Review",self.show_review));row.addWidget(button("Choose template",lambda:self.show_page(4)));box.addLayout(row)
        self.document_tabs=QTabWidget();box.addWidget(self.document_tabs,1)
        self.document_fields={};self.document_field_tabs={}
        from .company_editor import CompanyInformationEditor
        from .builder_preview import BuilderPreview
        from .template_text_editor import TemplateTextEditor
        builder=QWidget();builder.setObjectName("scrollPage");builder_layout=QVBoxLayout(builder);builder_layout.setContentsMargins(8,8,8,8);builder_layout.setSpacing(8)
        self.builder_template_label=QLabel("Template: Standard SOP");self.builder_template_label.setObjectName("caption");builder_layout.addWidget(self.builder_template_label)
        from .word_editor import WordEditor
        self.builder_modes=QTabWidget();builder_layout.addWidget(self.builder_modes,1)
        self.word_editor=WordEditor(self._persist_document)
        self.word_editor.open_requested.connect(self.open_document_editor)
        self.word_editor.rebuild_requested.connect(self.rebuild_document)
        self.word_editor.problem.connect(self.notice)
        self.builder_modes.addTab(self.word_editor,"Edit document")
        workspace=QSplitter();self.builder_modes.addTab(workspace,"Source / preview")
        self.builder_modes.currentChanged.connect(lambda index:QTimer.singleShot(0,self._maybe_builder_preview))
        self.builder_preview=BuilderPreview(self._builder_document_key);self.builder_preview.refresh_requested.connect(self.refresh_builder_preview);self.builder_preview.activity_changed.connect(lambda running:self._update_controls())
        workspace.addWidget(self.builder_preview)
        self.builder_edit_tabs=QTabWidget();self.builder_edit_tabs.setMinimumWidth(290);self.builder_edit_tabs.setMaximumWidth(420)
        details=QWidget();details.setObjectName("scrollPage");details_layout=QVBoxLayout(details)
        details_layout.addWidget(QLabel("Document title"))
        title_field=QLineEdit();title_field.setPlaceholderText("Enter the SOP title");title_field.textChanged.connect(self._document_changed)
        details_layout.addWidget(title_field);self.document_fields["title"]=title_field;self.document_field_tabs["title"]=0
        instruction=QLabel("Fill the document fields here. Template text edits existing paragraphs and cells; Information adds content before the SOP. Refresh preview to see your changes in the document.");instruction.setWordWrap(True);instruction.setObjectName("caption");details_layout.addWidget(instruction)
        details_layout.addWidget(button("More document details",lambda:self.document_tabs.setCurrentIndex(1)));details_layout.addStretch()
        self.builder_fields_form=QFormLayout();self.builder_fields_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows);details_layout.insertLayout(2,self.builder_fields_form)
        self.builder_fields_area=scroll_panel(details);self.builder_edit_tabs.addTab(self.builder_fields_area,"Fields")
        self.company_editor=CompanyInformationEditor();self.company_editor.changed.connect(self._company_information_changed);self.company_editor.problem.connect(self.notice)
        self.builder_edit_tabs.addTab(self.company_editor,"Information")
        self.template_text_editor=TemplateTextEditor();self.template_text_editor.changed.connect(self._template_text_changed);self.template_text_editor.field_requested.connect(self._reveal_builder_field)
        self.builder_edit_tabs.addTab(self.template_text_editor,"Template text")
        self.template_fields_editor=TemplateTextEditor(fields_only=True)
        self.template_fields_editor.changed.connect(self._template_text_changed)
        self.template_fields_editor.field_requested.connect(self._reveal_builder_field)
        self.builder_edit_tabs.addTab(self.template_fields_editor,'Template fields')
        workspace.addWidget(self.builder_edit_tabs);workspace.setSizes([750,340]);workspace.setStretchFactor(0,1);workspace.setCollapsible(0,False);workspace.setCollapsible(1,False)
        summary_row=QHBoxLayout();self.company_steps_summary=QLabel("Captured steps are included in this document.");self.company_steps_summary.setWordWrap(True);self.company_steps_summary.setObjectName("caption");summary_row.addWidget(self.company_steps_summary,1);summary_row.addWidget(button("Edit captured steps",lambda:self.show_page(1)));builder_layout.addLayout(summary_row)
        self.document_tabs.addTab(builder,"Builder");self.document_tabs.currentChanged.connect(lambda index:QTimer.singleShot(0,self._maybe_builder_preview) if index==0 else None)
        for title,names in [("Details",[("company","Company"),("reference","Reference"),("version","Version"),("author","Author"),("status","Status"),("orientation","Orientation")]),
                            ("Procedure",[("purpose","Purpose"),("scope","Scope"),("prerequisites","Prerequisites")]),
                            ("Control",[("reviewer","Reviewer"),("approver","Approver"),("created","Created (ISO date/time)"),("revision_history","Revision history")])]:
            content,form=form_page();index=self.document_tabs.addTab(scroll_panel(content),title)
            for name,label in names:
                if name in {"status","orientation"}:
                    field=QComboBox();field.addItems(["Draft","Approved"] if name=="status" else ["portrait","landscape"]);field.currentTextChanged.connect(self._document_changed)
                elif name in {"purpose","scope","prerequisites","revision_history"}:
                    field=QPlainTextEdit();field.setMinimumHeight(110);field.setMaximumHeight(180);field.textChanged.connect(self._document_changed)
                else:
                    field=QLineEdit();field.textChanged.connect(self._document_changed)
                self.document_fields[name]=field;self.document_field_tabs[name]=index;form.addRow(label,field)
        content,form=form_page();self.branding_tab=self.document_tabs.addTab(scroll_panel(content),"Branding")
        logo=QWidget();logo_row=QVBoxLayout(logo);logo_row.setContentsMargins(0,0,0,0)
        self.logo_label=QLabel("No logo");self.logo_label.setWordWrap(True);logo_row.addWidget(self.logo_label)
        buttons=QHBoxLayout();buttons.addWidget(button("Choose logo...",self.choose_logo));buttons.addWidget(button("Remove",self.remove_logo));buttons.addStretch();logo_row.addLayout(buttons);form.addRow("Company logo",logo)
        self.marker_color=QLineEdit();self.marker_size=QSpinBox();self.marker_size.setRange(5,150);self.marker_numbers=QCheckBox("Show step numbers")
        form.addRow("Marker colour",self.marker_color);form.addRow("Marker radius",self.marker_size);form.addRow(self.marker_numbers);form.addRow(button("Apply marker style",self.apply_marker_style))
        self.builder_metadata_fields={}
        for name,canonical in self.document_fields.items():
            if name=="title":continue
            if isinstance(canonical,QComboBox):
                mirror=QComboBox();mirror.addItems([canonical.itemText(i) for i in range(canonical.count())]);mirror.currentTextChanged.connect(lambda value,n=name:self._builder_metadata_changed(n))
            elif isinstance(canonical,QPlainTextEdit):
                mirror=QPlainTextEdit();mirror.setMinimumHeight(70);mirror.setMaximumHeight(100);mirror.textChanged.connect(lambda n=name:self._builder_metadata_changed(n))
            else:
                mirror=QLineEdit();mirror.textChanged.connect(lambda value,n=name:self._builder_metadata_changed(n))
            self.builder_metadata_fields[name]=mirror;self.builder_fields_form.addRow(name.replace("_"," ").capitalize(),mirror)
            signal=canonical.currentTextChanged if isinstance(canonical,QComboBox) else canonical.textChanged
            signal.connect(lambda *args,n=name:self._sync_builder_metadata(n))
        note=QLabel("Approved is a document label, rather than an approval workflow. Last updated is maintained automatically when the project is saved.");note.setObjectName("caption");note.setWordWrap(True);box.addWidget(note)
        return page

    def reveal_document_field(self, name):
        self.show_page(2)
        self.builder_modes.setCurrentIndex(1)
        if name in self.document_field_tabs:self.document_tabs.setCurrentIndex(self.document_field_tabs[name])
        if name=="title":self.builder_edit_tabs.setCurrentIndex(0)
        if name=="logo":self.document_tabs.setCurrentIndex(self.branding_tab)
        widget=self.document_fields.get(name)
        if widget:widget.setFocus()

    def show_template_fields(self):
        self.show_page(2);self.document_tabs.setCurrentIndex(0);self.builder_modes.setCurrentIndex(1);self.builder_edit_tabs.setCurrentWidget(self.template_fields_editor)

    def show_page(self, index):
        self.pages.setCurrentIndex(index)
        self.nav_buttons[index].setChecked(True)
        if index==5:self._refresh_home()
        if index==6:self.annotation_library_page.refresh()
        if index==2:QTimer.singleShot(0,self._maybe_builder_preview)
        page = self.pages.widget(index)
        if isinstance(page, QScrollArea):
            page.verticalScrollBar().setValue(0)

    def _refresh_home(self):
        self.home_page.refresh(self.recent_projects.entries(),self.project,len(self.template_library.list()),len(self._annotation_library().entries()))

    def remove_recent_project(self,root):
        try:self.recent_projects.remove(root);self._refresh_home()
        except OSError as exc:self.fail(exc)

    def use_library_annotation(self,identity):
        if not self.current_step() or self.canvas.original is None:
            self.notice('Open a screenshot step to place this design.');return
        self.show_page(1);self._choose_saved_annotation(identity)

    def _builder_document_key(self):
        from .builder_preview import document_key
        return document_key(self.project,self.store.root) if self.project and self.store else ""

    def _maybe_builder_preview(self):
        if self.isVisible() and self.pages.currentIndex()==2 and self.document_tabs.currentIndex()==0 and self.project:
            if self.builder_modes.currentIndex()==0:
                from PySide6.QtWidgets import QApplication
                if QApplication.platformName() != 'offscreen' and self.word_editor.session is None:
                    self.open_document_editor()
            else:self.refresh_builder_preview()

    def _persist_document(self,data,source_key):
        from ..authored_document import store_document
        previous=deepcopy(self.project);history,future=list(self.history),list(self.future)
        try:
            self.checkpoint()
            self.project.document_file=store_document(self.store,data)
            self.project.document_source_key=source_key
            self.store.save(self.project)
        except Exception:
            self.project=previous;self.history,self.future=history,future
            raise
        self.builder_preview.invalidate()
        return self.project.document_file

    def open_document_editor(self,rebuild=False):
        if not self.project or self.active or self.busy or self.word_editor.session:return
        from ..authored_document import make_working_copy,source_fingerprint
        self.flush_save()
        temporary=tempfile.TemporaryDirectory(prefix='sop-edit-')
        snapshot=deepcopy(self.project);root=self.store.root
        reference=None if rebuild else snapshot.document_file
        key=source_fingerprint(snapshot) if rebuild or not reference else snapshot.document_source_key
        self.word_editor.status.setText('Preparing the editable document…')
        def prepared(path,error):
            if error:
                temporary.cleanup();self.word_editor.status.setText(f'Cannot prepare the document: {error}');return
            try:self.word_editor.open_document(path,temporary,reference,key)
            except Exception as exc:
                self.word_editor.status.setText(f'Direct editing unavailable: {exc}. Use Source / preview. Working copy: {path}')
                self.notice(str(exc))
        self.run_task(lambda:make_working_copy(snapshot,root,Path(temporary.name)/'document.docx',rebuild=rebuild),prepared)

    def rebuild_document(self):
        if not self.project or self.active or self.busy:return
        if QMessageBox.question(self,'Rebuild document',
                'Replace the edited document with a new version generated from the selected template, fields and captured steps? '
                'Manual document edits will be replaced. The previous version remains available through project Undo.',
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        try:
            self.word_editor.close_document()
            self.open_document_editor(rebuild=True)
        except Exception as exc:self.fail(exc)

    def refresh_builder_preview(self):
        if not self.project or self.active or self.busy:return
        try:self.flush_save()
        except Exception as exc:self.builder_preview.status.setText(str(exc));return
        self.builder_preview.request(self.project,self.store.root)

    def _sync_builder_metadata(self,name):
        canonical=self.document_fields[name];mirror=self.builder_metadata_fields[name]
        value=canonical.currentText() if isinstance(canonical,QComboBox) else canonical.toPlainText() if isinstance(canonical,QPlainTextEdit) else canonical.text()
        current=mirror.currentText() if isinstance(mirror,QComboBox) else mirror.toPlainText() if isinstance(mirror,QPlainTextEdit) else mirror.text()
        if value==current:return
        previous=mirror.blockSignals(True)
        try:
            if isinstance(mirror,QComboBox):mirror.setCurrentText(value)
            elif isinstance(mirror,QPlainTextEdit):mirror.setPlainText(value)
            else:mirror.setText(value)
        finally:mirror.blockSignals(previous)

    def _builder_metadata_changed(self,name):
        if self.loading or not self.project:return
        mirror=self.builder_metadata_fields[name];canonical=self.document_fields[name]
        if isinstance(mirror,QComboBox):canonical.setCurrentText(mirror.currentText())
        elif isinstance(mirror,QPlainTextEdit):canonical.setPlainText(mirror.toPlainText())
        else:canonical.setText(mirror.text())

    def _reveal_builder_field(self,name):
        if name=='__native__':
            self.show_page(2);self.document_tabs.setCurrentIndex(0);self.builder_modes.setCurrentIndex(0);return
        self.builder_modes.setCurrentIndex(1)
        name="title" if name=="sop_title" else name
        if name=="steps":self.show_page(1)
        elif name=="title" or name in self.builder_metadata_fields:
            self.show_page(2);self.document_tabs.setCurrentIndex(0);self.builder_edit_tabs.setCurrentIndex(0)
            widget=self.document_fields["title"] if name=="title" else self.builder_metadata_fields[name]
            widget.setFocus();self.builder_fields_area.ensureWidgetVisible(widget)
        else:self.reveal_document_field(name)

    def _template_text_changed(self,value):
        if self.loading or not self.project or value==self.project.template_text_edits:return
        self.checkpoint();self.project.template_text_edits=value;self.edited()
        self.template_text_editor.edits=deepcopy(value)
        self.template_fields_editor.edits=deepcopy(value)

    def notice(self, message):
        self.statusBar().showMessage(message)

    def fail(self, message):
        log.error("Operation failed: %s", message)
        self.notice(str(message))
        QMessageBox.warning(self, "SOP Capture Studio", str(message))

    def run_task(self, operation, completed):
        if self.busy: return
        self.busy = True
        self._update_controls()
        def run():
            try:
                value, error = operation(), None
            except Exception as exc:
                log.exception("Background operation failed")
                value, error = None, exc
            self.bridge.completed.emit(completed, value, error)
        thread = threading.Thread(target=run, daemon=True)
        self.background_threads.add(thread)
        thread.start()

    def _task_done(self, callback, value, error):
        self.busy = False
        self.background_threads = {t for t in self.background_threads if t.is_alive()}
        try:
            callback(value, error)
        except Exception as exc:
            self.fail(exc)
        self._update_controls()

    @property
    def active(self):
        return self.session is not None and self.session.state != "idle"

    def _update_controls(self):
        ready = bool(self.project) and not self.active and not self.busy
        self._update_library_save_button()
        self.new_button.setEnabled(not self.active and not self.busy)
        self.open_button.setEnabled(not self.active and not self.busy)
        self.start_button.setEnabled(ready and self.target is not None and self.backend is not None)
        self.start_button.setToolTip("Create/open a project and select a window to start")
        self.pause_button.setEnabled(self.active and not self.busy)
        self.stop_button.setEnabled(self.active and not self.busy)
        self.float_stop.setEnabled(not self.busy)
        self.float_pause.setEnabled(not self.busy)
        self.refresh_button.setEnabled(not self.active and not self.busy and self.backend is not None)
        self.preview_button.setEnabled(self.target is not None and not self.active and not self.busy)
        self.windows_list.setEnabled(not self.active and not self.busy)
        self.pages.widget(1).setEnabled(ready)
        self.pages.widget(2).setEnabled(ready)
        self.pages.widget(3).setEnabled(not self.active and not self.busy)
        self.pages.widget(4).setEnabled(not self.active and not self.busy)
        self.pages.widget(5).setEnabled(not self.active and not self.busy)
        self.pages.widget(6).setEnabled(not self.active and not self.busy)
        self.annotation_library_page.set_can_use(ready and self.current_step() is not None and self.canvas.original is not None)
        self.templates_page.apply_button.setEnabled(ready)
        self.templates_page.preview_button.setEnabled(not self.active and not self.busy and not self.builder_preview.running)
        self.screenshots_button.setEnabled(self.store is not None)
        self.editor_panel.setEnabled(ready and self.current_step() is not None)
        count=len(self.project.steps) if self.project else 0
        document_note='Rebuild applies later capture/source changes to your edited document.' if self.project and self.project.document_file else 'Included when the document is generated.'
        self.company_steps_summary.setText(f"Captured SOP: {count} step{'s' if count != 1 else ''}. {document_note}")
        if hasattr(self,"action_bindings"):
            from ..shortcuts import ACTIONS
            for identity,action in self.action_bindings.items():
                context=ACTIONS[identity][3]
                enabled=context=="any" or (context=="recording" and self.active and not self.busy) or (context not in {"any","recording"} and not self.active and not self.busy and (context=="idle" or (self.project is not None and (context!="step" or self.current_step() is not None))))
                if identity in {"preview_pdf","export_pdf","export_word"} and self.builder_preview.running:enabled=False
                action.setEnabled(bool(enabled))

    def set_project(self, project, store):
        if self.active or self.busy:
            raise RuntimeError("Finish capture or the current operation first")
        if self.store:
            self.flush_save()
        self.word_editor.close_document()
        if store is not self.store:
            store.acquire()
            if self.store: self.store.release()
        self.project, self.store = project, store
        self.history, self.future = [], []
        self.target = None
        self.windows_list.setCurrentRow(-1)
        self._refresh_project()
        self.flush_save()
        self._update_controls()
        try:self.recent_projects.record(self.project,self.store.root)
        except OSError:log.warning('Recent project history could not be saved',exc_info=True)
        self._refresh_home()

    def new_project(self):
        if self.active or self.busy: return
        try:profiles=self.template_library.list()
        except Exception as exc:self.fail(exc);return
        from .new_project_dialog import NewProjectDialog,project_folder_name
        current=self.project.template.get('id','standard') if self.project else 'standard'
        dialog=NewProjectDialog(profiles,self.settings.value('location'),current,self)
        if dialog.exec()!=QDialog.DialogCode.Accepted:dialog.deleteLater();return
        title,identity,parent=dialog.values();dialog.deleteLater()
        parent=Path(parent).expanduser()
        base=project_folder_name(title)
        project = Project(title=title.strip(), company=self.settings.value("company"), author=self.settings.value("author"),
                          reference=f"{self.settings.value('prefix')}-001", orientation=self.settings.value("orientation"))
        try:
            ImageColor.getrgb(self.settings.value("marker_color"))
            project.marker_color = self.settings.value("marker_color")
            project.marker_size = self.settings.value("marker_size")
            project.marker_numbers = self.settings.value("marker_numbers")
            parent.mkdir(parents=True,exist_ok=True)
            suffix=1
            while True:
                folder=Path(parent)/(base+(f' ({suffix})' if suffix>1 else ''))
                try:
                    folder.mkdir()
                    break
                except FileExistsError:suffix+=1
            project.template=self.template_library.snapshot(identity,folder)
            self.set_project(project, ProjectStore(folder))
            logo = self.settings.value("logo")
            if logo:
                self._set_logo(logo)
            self.refresh_windows()
            self.show_page(0)
            self.notice(f'New project created in {folder}. Its template copy is independent of other projects.')
        except Exception as exc:
            self.fail(exc)

    def open_project(self):
        if self.active or self.busy: return
        path, _ = QFileDialog.getOpenFileName(self, "Open SOP project", self.settings.value("location"), "SOP project (project.json project.backup.json)")
        if not path: return
        self.open_project_path(path)

    def open_project_path(self,path):
        if self.active or self.busy:return
        path=Path(path)
        store = ProjectStore(path.parent if path.is_file() else path)
        if self.store and store.root == self.store.root:
            try:self.recent_projects.record(self.project,self.store.root);self._refresh_home()
            except OSError:log.warning('Recent project history could not be saved',exc_info=True)
            self.show_page(1)
            return
        try:
            try:
                project = store.load(backup=Path(path).name == "project.backup.json")
            except ValueError:
                if not (store.root / "project.backup.json").exists(): raise
                if QMessageBox.question(self, "Recover project", "The project cannot be opened. Recover its last-known-good backup?") != QMessageBox.StandardButton.Yes:
                    return
                project = store.load(backup=True)
            try:
                self.set_project(project, store)
            except RuntimeError as exc:
                if "lock" not in str(exc): raise
                if QMessageBox.question(self, "Project lock", "This project is open elsewhere or has a stale lock. Only continue if no other instance is editing it. Remove the lock?") != QMessageBox.StandardButton.Yes:
                    return
                store.acquire(force=True)
                # set_project sees an already owned lock.
                store.release()
                self.set_project(project, store)
            self.show_page(1)
            self.notice("Project opened. Review screenshots before exporting.")
        except Exception as exc:
            self.fail(exc)

    def checkpoint(self):
        if self.project and not self.loading:
            self.history.append(deepcopy(self.project))
            self.history = self.history[-60:]
            self.future.clear()

    def edited(self):
        self.builder_preview.invalidate()
        if self.project and self.project.document_file:
            from ..authored_document import source_fingerprint
            if source_fingerprint(self.project)!=self.project.document_source_key:
                self.word_editor.status.setText('Source fields or captured steps changed. Your direct document edits are retained. '
                                                'Choose Rebuild from captured steps to replace the document with the updated source.')
        if self.loading or not self.project: return
        self.save_timer.start()
        self._refresh_list_labels()
        self._update_controls()

    def undo(self):
        if not self.history or self.active or self.busy: return
        try:self.word_editor.close_document()
        except Exception as exc:self.fail(exc);return
        self.future.append(deepcopy(self.project))
        self.project = self.history.pop()
        self._refresh_project()
        self.edited()

    def redo(self):
        if not self.future or self.active or self.busy: return
        try:self.word_editor.close_document()
        except Exception as exc:self.fail(exc);return
        if not self.future:return
        self.history.append(deepcopy(self.project))
        self.project = self.future.pop()
        self._refresh_project()
        self.edited()

    def flush_save(self):
        self.save_timer.stop()
        if self.project and self.store:
            self.word_editor.save_document()
            self.store.save(self.project)
            try:self.recent_projects.update_title(self.project,self.store.root)
            except OSError:log.warning('Recent project title could not be updated',exc_info=True)
            self.project_label.setText(f"{self.project.title}  ·  {len(self.project.steps)} steps\n{self.store.root}")
            self.notice("All changes saved locally")

    def _autosave(self):
        try:
            self.flush_save()
        except Exception as exc:
            self.fail(f"Changes could not be saved. Keep this window open and retry. {exc}")

    def current_step(self):
        if not self.project: return None
        index = self.steps_list.currentRow()
        return self.project.steps[index] if 0 <= index < len(self.project.steps) else None

    def _refresh_project(self):
        self._template_status()
        self.loading = True
        for name, widget in self.document_fields.items():
            value = getattr(self.project, name)
            if isinstance(widget, QComboBox): widget.setCurrentText(value)
            elif isinstance(widget, QPlainTextEdit): widget.setPlainText(value)
            else: widget.setText(value)
        self.company_editor.set_content(self.project.company_information)
        self.marker_color.setText(self.project.marker_color)
        self.marker_size.setValue(self.project.marker_size)
        self.marker_numbers.setChecked(self.project.marker_numbers)
        self.logo_label.setText(self.project.logo or "No logo")
        self.loading = False
        self._refresh_steps()

    def _template_status(self):
        name = self.project.template.get("name", "Standard SOP") if self.project else "Standard SOP"
        self.selected_template_label.setText("Template: "+name)
        self.builder_template_label.setText("Template: "+name+" | direct edits are saved with this project")
        self.builder_preview.reset()
        path=self.store.resolve(self.project.template["docx"]) if self.project and self.store and self.project.template.get("docx") else None
        self.template_text_editor.set_source(path,self.project.template_text_edits if self.project else {})
        self.template_fields_editor.project=self.project
        self.template_fields_editor.set_source(path,self.project.template_text_edits if self.project else {})
        QTimer.singleShot(0,self._maybe_builder_preview)
        self.templates_page.active_label.setText("Current SOP template: "+name+". Apply a library template to change it; saved SOPs keep their own snapshot.")

    def apply_template(self, identity):
        if not self.project or self.active or self.busy: raise ValueError("Open an SOP and finish the current operation first")
        if self.project.document_file:
            if QMessageBox.question(self,'Change document template','Applying this template will replace direct document edits when you next open the editor. Continue?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self.flush_save()
        self.word_editor.close_document()
        snapshot = self.template_library.snapshot(identity, self.store.root)
        previous_document=(self.project.document_file,self.project.document_source_key)
        previous = self.project.template
        previous_edits=deepcopy(self.project.template_text_edits)
        history, future = list(self.history), list(self.future)
        self.checkpoint()
        self.project.document_file=None;self.project.document_source_key=''
        self.project.template = snapshot
        if self.project.template_text_edits:
            from ..template_text import source_hash
            if not snapshot.get("docx") or source_hash(self.store.resolve(snapshot["docx"]))!=self.project.template_text_edits["source_hash"]:self.project.template_text_edits={}
        try:
            self.flush_save()
        except Exception:
            self.project.document_file,self.project.document_source_key=previous_document
            self.project.template = previous
            self.project.template_text_edits=previous_edits
            self.history, self.future = history, future
            self._template_status()
            raise
        self._template_status()
        self.notice("Template applied to this SOP. Preview the result before exporting.")

    def step_list_label(self, index):
        step = self.project.steps[index]
        prefix = step.section+"\n" if step.section and (index == 0 or self.project.steps[index-1].section != step.section) else ""
        return prefix+f"{index+1:02d}   {step.title}"

    def group_steps(self, name, first, last):
        name = name.strip()
        if not self.project or not 0 <= first <= last < len(self.project.steps): return
        if len(name) > 120 or "\n" in name or "\r" in name: raise ValueError("Invalid section name")
        self.checkpoint()
        selected = self.current_step()
        for step in self.project.steps[first:last+1]: step.section = name
        self._refresh_steps(selected.id if selected else None)
        self.edited()

    def rename_section(self, old, new):
        new = new.strip()
        if len(new) > 120 or "\n" in new or "\r" in new: raise ValueError("Invalid section name")
        self.checkpoint()
        for step in self.project.steps:
            if step.section == old: step.section = new
        self._refresh_steps()
        self.edited()

    def rename_section_dialog(self):
        step = self.current_step()
        if not step or not step.section or self.active or self.busy: return
        name, accepted = QInputDialog.getText(self, "Rename section", "New name for all steps in this section:", text=step.section)
        if accepted:
            if len(name.strip()) > 120 or "\n" in name or "\r" in name:
                self.notice("Section names must be one line, up to 120 characters.")
                return
            self.rename_section(step.section, name)

    def group_steps_dialog(self):
        if not self.project or not self.project.steps or self.active or self.busy: return
        dialog = QDialog(self)
        dialog.setWindowTitle("Group steps into a section")
        layout = QFormLayout(dialog)
        name = QLineEdit()
        name.setMaxLength(120)
        first, last = QSpinBox(), QSpinBox()
        for widget in (first, last): widget.setRange(1, len(self.project.steps))
        first.setValue(max(1, self.steps_list.currentRow()+1))
        last.setValue(first.value())
        first.valueChanged.connect(lambda value: last.setMinimum(value))
        layout.addRow("Section name (blank removes grouping)", name)
        layout.addRow("First step", first)
        layout.addRow("Last step", last)
        layout.addRow(button("Apply grouping", dialog.accept))
        if dialog.exec() and first.value() <= last.value():
            self.group_steps(name.text(), first.value()-1, last.value()-1)

    def show_review(self, for_export=False):
        if not self.project: return False
        from ..review import review_project
        issues = review_project(self.project, self.store.root)
        if for_export and not issues: return True
        dialog = QDialog(self)
        dialog.setWindowTitle("Review SOP before export")
        dialog.resize(650, 400)
        layout = QVBoxLayout(dialog)
        page_header(layout,"Review SOP","Check missing details before export. Screenshots may be omitted intentionally.")
        items = QListWidget()
        for issue in issues: items.addItem(issue.message)
        if not issues: items.addItem("No missing details found.")
        layout.addWidget(items)
        def fix():
            row = items.currentRow()
            if not 0 <= row < len(issues): return
            issue = issues[row]
            if issue.step_id:
                index = next((i for i, step in enumerate(self.project.steps) if step.id == issue.step_id), None)
                if index is not None:
                    self.show_page(1)
                    self.steps_list.setCurrentRow(index)
                    self.inspector_toggle.setChecked(True)
                    self.editor_inspector.setCurrentIndex(0)
                    (self.step_description if issue.field == "description" else self.step_title).setFocus()
            else:
                self.show_page(4 if issue.field == "template" else 1 if issue.field == "steps" else 2)
                if issue.field not in {"template","steps"}:self.reveal_document_field(issue.field)
            dialog.reject()
        actions=QHBoxLayout()
        fix_button=button("Fix selected item",fix);fix_button.setEnabled(bool(issues));actions.addWidget(fix_button);actions.addStretch()
        actions.addWidget(button("Back" if for_export else "Close",dialog.reject))
        if for_export:actions.addWidget(button("Export anyway",dialog.accept,True))
        layout.addLayout(actions)
        return bool(dialog.exec())

    def _refresh_steps(self, selected=None):
        previous = self.steps_list.currentRow()
        self.loading = True
        self.steps_list.clear()
        for index, step in enumerate(self.project.steps):
            item = QListWidgetItem(self.step_list_label(index))
            item.setData(Qt.ItemDataRole.UserRole, step.id)
            if step.image:
                try:
                    thumbnail = render_step(self.store.root, step, index+1, self.project)
                    thumbnail.thumbnail((130, 72))
                    item.setIcon(QIcon(image_pixmap(thumbnail)))
                except (OSError, ValueError):
                    item.setToolTip("Screenshot unavailable; replace it to recover this step")
            self.steps_list.addItem(item)
        if selected:
            previous = next((i for i, s in enumerate(self.project.steps) if s.id == selected), previous)
        index = min(max(0, previous), len(self.project.steps)-1)
        self.steps_list.setCurrentRow(index)
        self.loading = False
        self._select_step(index)

    def _refresh_list_labels(self):
        for index, step in enumerate(self.project.steps):
            item = self.steps_list.item(index)
            if item: item.setText(self.step_list_label(index))

    def _select_step(self, index):
        if self.loading: return
        self.loading = True
        step = self.current_step()
        self.step_title.setText(step.title if step else "")
        self.step_section.setText(step.section if step else "")
        self.step_description.setPlainText(step.description if step else "")
        self.step_notes.setText(step.notes if step else "")
        self.marker_check.setChecked(bool(step and step.marker_visible))
        self.canvas.set_step(self.store.root if self.store else None, self.project, step, index+1)
        self.loading = False
        self._update_controls()

    def _step_fields_changed(self):
        step = self.current_step()
        if self.loading or not step: return
        self.checkpoint()
        step.title = self.step_title.text()
        step.section = self.step_section.text().strip()
        step.description = self.step_description.toPlainText()
        step.notes = self.step_notes.text()
        self.edited()

    def _company_information_changed(self,value):
        if self.loading or not self.project: return
        if value==self.project.company_information: return
        self.checkpoint()
        self.project.company_information=value
        self.edited()

    def _document_changed(self):
        if self.loading or not self.project: return
        self.checkpoint()
        for name, widget in self.document_fields.items():
            value = widget.currentText() if isinstance(widget, QComboBox) else widget.toPlainText() if isinstance(widget, QPlainTextEdit) else widget.text()
            setattr(self.project, name, value)
        self.edited()

    def add_step(self):
        if not self.project or self.active or self.busy: return
        self.checkpoint()
        step = Step(title="New step")
        selected = self.current_step()
        step.section = selected.section if selected else ""
        position = self.project.steps.index(selected)+1 if selected else len(self.project.steps)
        self.project.steps.insert(position, step)
        self._refresh_steps(step.id)
        self.edited()

    def delete_step(self):
        step = self.current_step()
        if not step: return
        self.checkpoint()
        self.project.steps.remove(step)
        self._refresh_steps()
        self.edited()

    def duplicate_step(self):
        source = self.current_step()
        if not source or self.active or self.busy: return
        self.checkpoint()
        duplicate = deepcopy(source)
        duplicate.id = uuid.uuid4().hex
        self.project.steps.insert(self.project.steps.index(source)+1, duplicate)
        self._refresh_steps(duplicate.id)
        self.edited()

    def move_step(self, delta):
        index = self.steps_list.currentRow()
        if not self.project or not 0 <= index+delta < len(self.project.steps): return
        order = [s.id for s in self.project.steps]
        order[index], order[index+delta] = order[index+delta], order[index]
        self.reorder_steps(order)
        self.steps_list.setCurrentRow(index+delta)

    def _list_reordered(self, *args):
        if not self.loading:
            self.reorder_steps([self.steps_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.steps_list.count())])

    def reorder_steps(self, order):
        if not self.project or len(order) != len(self.project.steps) or set(order) != {s.id for s in self.project.steps}:
            raise ValueError("Step order must include each step once")
        self.checkpoint()
        steps = {s.id: s for s in self.project.steps}
        selected = self.current_step()
        self.project.steps = [steps[identity] for identity in order]
        self._refresh_steps(selected.id if selected else None)
        self.edited()

    def _marker_toggled(self, checked):
        step = self.current_step()
        if self.loading or not step: return
        self.checkpoint()
        step.marker_visible = checked
        self.canvas.refresh()
        self.edited()

    def _sync_annotation_controls(self):
        style = self.canvas.annotation_style()
        self.styling = True
        self.annotation_width.setValue(style["width"])
        self.annotation_zoom.setValue(style["zoom"])
        self.annotation_font_size.setValue(style["font_size"])
        self.annotation_opacity.setValue(style["opacity"])
        self.arrow_style_picker.setCurrentIndex(self.arrow_style_picker.findData(style["arrow_style"]))
        if self.annotation_text.text() != style["text"]:
            self.annotation_text.setText(style["text"])
        colour = QColor(style["color"])
        foreground = "#122f44" if colour.lightness() > 135 else "white"
        self.annotation_colour.setStyleSheet(f"background: {colour.name()}; color: {foreground};")
        kind = self.canvas.step.annotations[self.canvas.selected].kind if self.canvas.selected is not None else self.canvas.tool
        self.arrow_style_picker.setVisible(kind == "arrow")
        self.annotation_colour.setEnabled(kind in {"arrow", "line", "circle", "highlight", "highlighter", "text", "callout", "magnifier"})
        self.annotation_width.setEnabled(kind in {"arrow", "line", "circle", "highlight", "callout", "magnifier"})
        self.annotation_font_size.setEnabled(kind in {"text", "callout"})
        self.annotation_opacity.setEnabled(kind == "highlighter")
        self.annotation_text.setVisible(kind in {"text", "callout"})
        for widget,visible in [(self.annotation_colour,kind in {"arrow","line","circle","highlight","highlighter","text","callout","magnifier"}),
                               (self.annotation_width,kind in {"arrow","line","circle","highlight","callout","magnifier"}),
                               (self.annotation_font_size,kind in {"text","callout"}), (self.annotation_opacity,kind=="highlighter"),
                               (self.arrow_style_picker,kind=="arrow"), (self.annotation_text,kind in {"text","callout"}),
                               (self.annotation_zoom,kind=="magnifier"), (self.marker_row,kind=="marker"), (self.custom_design_help,kind=="design")]:
            self.annotation_form.setRowVisible(widget,visible)
        self.styling = False

    def _annotation_style_changed(self, name, value):
        if not self.styling:
            self.canvas.set_annotation_style(**{name: value})

    def choose_annotation_colour(self):
        colour = QColorDialog.getColor(QColor(self.canvas.annotation_style()["color"]), self, "Annotation colour")
        if colour.isValid():
            self.canvas.set_annotation_style(color=colour.name())

    def remove_marker(self):
        step = self.current_step()
        if not step: return
        self.checkpoint()
        step.marker = None
        self.canvas.refresh()
        self.edited()

    def remove_annotation(self):
        step = self.current_step()
        if step and step.annotations:
            self.checkpoint()
            step.annotations.pop()
            self.canvas.refresh()
            self.edited()

    def apply_marker_style(self):
        if not self.project: return
        try:
            ImageColor.getrgb(self.marker_color.text())
        except ValueError:
            self.fail("Enter a valid colour such as #ef4444")
            return
        self.checkpoint()
        self.project.marker_color = self.marker_color.text()
        self.project.marker_size = self.marker_size.value()
        self.project.marker_numbers = self.marker_numbers.isChecked()
        self._refresh_steps()
        self.edited()

    def replace_image(self):
        step = self.current_step()
        if not step: return
        path, _ = QFileDialog.getOpenFileName(self, "Replace screenshot", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if not path: return
        try:
            with Image.open(path) as image:
                self._replace_step_image(step, image)
        except Exception as exc:
            self.fail(exc)

    def _replace_step_image(self, step, image):
        relative = self.store.add_image(image, step.id, self.settings.value("compression"))
        self.checkpoint()
        step.image, step.marker, step.annotations = relative, None, []
        self._refresh_steps(step.id)
        self.edited()

    def _set_logo(self, path):
        with Image.open(path) as image:
            relative = self.store.add_image(image, "logo")
        self.checkpoint()
        self.project.logo = relative
        self.logo_label.setText(relative)
        self.edited()

    def choose_logo(self):
        if not self.project: return
        path, _ = QFileDialog.getOpenFileName(self, "Company logo", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            try: self._set_logo(path)
            except Exception as exc: self.fail(exc)

    def remove_logo(self):
        if self.project:
            self.checkpoint()
            self.project.logo = None
            self.logo_label.setText("No logo")
            self.edited()

    def save_annotated(self):
        step = self.current_step()
        if not step or not step.image: return
        try:
            number = self.project.steps.index(step)+1
            path = self.store.root / "Annotated" / f"{step.id}.png"
            from io import BytesIO
            data = BytesIO()
            render_step(self.store.root, step, number, self.project).save(data, "PNG")
            atomic_bytes(path, data.getvalue())
            self.notice(f"Annotated image saved: {path.name}")
        except Exception as exc: self.fail(exc)

    def refresh_windows(self):
        if not self.backend: return
        self.target = None
        self.windows_list.clear()
        try:
            for target in self.backend.list_windows():
                item = QListWidgetItem(f"{target.application}\n{target.title}")
                item.setData(Qt.ItemDataRole.UserRole, target)
                self.windows_list.addItem(item)
            self.notice("Choose the window to document")
        except Exception as exc: self.fail(exc)
        self._update_controls()

    def _target_selected(self, item, previous):
        self.target = item.data(Qt.ItemDataRole.UserRole) if item else None
        self.window_preview.setPixmap(QIcon().pixmap(1, 1))
        self.window_preview.setText("Select Preview to check this application's capture support.")
        self._update_controls()

    def preview_target(self):
        if not self.target or self.active: return
        target = self.target
        def finished(result, error):
            if error:
                self.window_preview.setText(str(error))
                self.notice(str(error))
            elif self.target == target:
                image, _ = result
                pixmap = image_pixmap(image)
                self.window_preview.setPixmap(pixmap.scaled(self.window_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.run_task(lambda: self.backend.capture(target, foreground=False), finished)

    def start_capture(self):
        if not self.project or not self.target or self.active or self.busy: return
        try:
            self.flush_save()
            parse_hotkey(self.settings.value("shortcut"))
            options = CaptureOptions(delay_ms=self.settings.value("delay"), before_click=self.settings.value("timing") != "After click",
                                     buttons=("left", "right", "middle")[:self.settings.fields["buttons"].currentIndex()+1])
            self.session = CaptureSession(self.backend, self.bridge.captured.emit, self.bridge.notice.emit)
            self.session.start(self.target, options)
            self.native_input = NativeInput(self.session.trigger, self.session.manual, options.before_click, self.session.input_context)
            self.native_input.start(self.settings.value("shortcut"))
            self.elapsed = 0
            self.last_tick = time.monotonic()
            self.floating.show()
            self.backend.exclude(int(self.floating.winId()))
            self.showMinimized()
            self.backend.activate(self.target)
            if self.settings.value("initial"):
                session = self.session
                QTimer.singleShot(600, lambda: self._initial_capture(session))
            self.notice("Recording selected window. Use the floating controls to pause or stop.")
        except Exception as exc:
            if self.native_input:
                self.native_input.stop()
            if self.session:
                self.session.stop()
            self.session = self.native_input = None
            self.floating.hide()
            self.fail(exc)
        self._update_controls()

    def _initial_capture(self, originating_session):
        if self.session is originating_session and self.active and self.session.state == "recording":
            self.session.manual()

    def toggle_pause(self):
        if not self.active or self.busy: return
        if self.session.state == "recording":
            self.session.pause()
        else:
            self.session.resume()
            self.backend.activate(self.target)
        self._tick()

    def stop_capture(self):
        if not self.active or self.busy: return
        session, native = self.session, self.native_input
        self.notice("Finishing pending screenshots…")
        def stop():
            try:
                if native: native.stop()
            finally:
                session.stop()
        def finished(value, error):
            if error:
                self.fail(error)
                return
            self.floating.hide()
            self.session = self.native_input = None
            self.flush_save()
            self._refresh_steps()
            self.showNormal()
            self.raise_()
            self.activateWindow()
            self.show_page(1)
            self.notice("Capture saved. Add titles and instructions, then preview your PDF.")
        self.run_task(stop, finished)

    def _captured(self, result):
        try:
            step = Step(title=f"Step {len(self.project.steps)+1}", marker=result.marker, button=result.button,
                        timestamp=result.timestamp, capture_bounds=list(result.bounds), frame_age_ms=result.frame_age_ms)
            step.image = self.store.add_image(result.image, step.id, self.settings.value("compression"))
            self.project.steps.append(step)
            self.flush_save()
            self._refresh_steps(step.id)
        except Exception as exc:
            if self.session: self.session.pause()
            self.fail(f"Capture paused because a screenshot could not be saved: {exc}")

    def _tick(self):
        current = time.monotonic()
        if self.active and self.session.state == "recording":
            self.elapsed += current - self.last_tick
        self.last_tick = current
        state = self.session.state.title() if self.active else "Ready"
        count = sum(bool(s.image) for s in self.project.steps) if self.project else 0
        self.capture_status.setText(f"{state}   ·   {int(self.elapsed)//60:02d}:{int(self.elapsed)%60:02d}   ·   {count} screenshots")
        self.float_status.setText(f"● {state}  {int(self.elapsed)//60:02d}:{int(self.elapsed)%60:02d}")
        label = "Resume" if self.active and self.session.state == "paused" else "Pause"
        self.pause_button.setText(label)
        self.float_pause.setText(label)

    def retake_image(self):
        step = self.current_step()
        if not step or not self.target or self.active or self.busy:
            self.notice("Select a target on the Capture page before retaking")
            return
        self.showMinimized()
        try:
            self.backend.activate(self.target)
        except Exception as exc:
            self.showNormal()
            self.fail(exc)
            return
        target = self.target
        def capture():
            time.sleep(.5)
            return self.backend.capture(target)
        def finished(value, error):
            self.showNormal()
            if error: self.fail(error)
            else: self._replace_step_image(step, value[0])
        self.run_task(capture, finished)

    def export_to(self, path):
        if not self.project: raise ValueError("Open a project first")
        self.flush_save()
        return export_pdf(self.project, self.store.root, path)

    def export_word_dialog(self):
        if self.builder_preview.running:
            self.notice("Wait for the document preview to finish before starting another export.");return
        if not self.project or self.busy or self.active: return
        if not self.show_review(for_export=True): return
        safe = re.sub(r'[^\w .-]', "_", self.project.title)[:100] or "Procedure"
        path, _ = QFileDialog.getSaveFileName(self, "Export editable Word document", str(self.store.root / "Exports" / f"{safe}.docx"), "Word document (*.docx)")
        if not path: return
        chosen = Path(path)
        output = chosen.with_suffix(".docx")
        if output != chosen and output.exists() and QMessageBox.question(self, "Replace Word document?", f"{output.name} already exists. Replace it?") != QMessageBox.StandardButton.Yes: return
        try: self.flush_save()
        except Exception as exc:
            self.fail(exc)
            return
        project, root = deepcopy(self.project), self.store.root
        from ..word_export import export_docx
        def finished(value, error):
            if error: self.fail(error)
            else:
                self.notice(f"Word document exported: {value}")
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(value.parent)))
        self.run_task(lambda: export_docx(project, root, output), finished)

    def export_dialog(self):
        if self.builder_preview.running:
            self.notice("Wait for the document preview to finish before starting another export.");return
        if not self.project or self.busy: return
        if not self.show_review(for_export=True): return
        safe = re.sub(r'[^\w .-]', "_", self.project.title)[:100] or "Procedure"
        path, _ = QFileDialog.getSaveFileName(self, "Export procedure PDF", str(self.store.root / "Exports" / f"{safe}.pdf"), "PDF (*.pdf)")
        if not path: return  # QFileDialog confirms replacement of existing files.
        chosen = Path(path)
        output = chosen.with_suffix(".pdf")
        if output != chosen and output.exists():
            if QMessageBox.question(self, "Replace PDF?", f"{output.name} already exists. Replace it?") != QMessageBox.StandardButton.Yes:
                return
        path = str(output)
        try: self.flush_save()
        except Exception as exc:
            self.fail(exc)
            return
        project, root = deepcopy(self.project), self.store.root
        def finished(value, error):
            if error: self.fail(error)
            else:
                self.notice(f"PDF exported: {value}")
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(value.parent)))
        self.run_task(lambda: export_pdf(project, root, path), finished)

    def preview_pdf(self):
        if self.builder_preview.running:
            self.notice("Wait for the document preview to finish before starting another export.");return
        if not self.project or self.busy: return
        try: self.flush_save()
        except Exception as exc:
            self.fail(exc)
            return
        project, root = deepcopy(self.project), self.store.root
        path = Path(self.preview_dir.name) / f"preview-{time.monotonic_ns()}.pdf"
        def finished(value, error):
            if error:
                self.fail(error)
                return
            self._show_pdf_preview(value)
        self.run_task(lambda: export_pdf(project, root, path), finished)

    def preview_template(self,identity):
        if self.active or self.busy or self.builder_preview.running:return
        root=Path(self.preview_dir.name)/('template-'+uuid.uuid4().hex)
        def prepare():
            profile=self.template_library.snapshot(identity,root)
            project=Project(title='Template preview',reference='PREVIEW-001',author='Example author',template=profile,
                            steps=[Step(title='Open the application',description='Example instruction shown in the selected company style.'),Step(title='Confirm the details',description='Review the information before continuing.')])
            project.steps[0].image=ProjectStore(root).add_image(Image.new('RGB',(900,500),'#e6eff6'),project.steps[0].id)
            return export_pdf(project,root,root/'preview.pdf')
        def finished(path,error):
            if error:self.fail(error)
            else:self._show_pdf_preview(path)
        self.run_task(prepare,finished)

    def _show_pdf_preview(self,path):
        from PySide6.QtPdf import QPdfDocument
        from PySide6.QtPdfWidgets import QPdfView
        dialog = QDialog(self)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.setWindowTitle("PDF preview — review sensitive information before export")
        dialog.resize(950, 850)
        layout = QVBoxLayout(dialog)
        page_header(layout,"PDF preview","Review the document and any sensitive information before exporting.")
        view = QPdfView(dialog)
        document = QPdfDocument(dialog)
        # Qt PDF's renderer can retain a file handle after close(). Keep the
        # preview's source in a parent-owned memory buffer instead.
        source = QBuffer(dialog)
        source.setData(path.read_bytes())
        source.open(QIODevice.OpenModeFlag.ReadOnly)
        document.load(source)
        dialog.finished.connect(document.close)
        view.setDocument(document)
        view.setPageMode(QPdfView.PageMode.MultiPage)
        view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        layout.addWidget(view)
        footer=QHBoxLayout();footer.addStretch();footer.addWidget(button("Close preview",dialog.close));layout.addLayout(footer)
        dialog.show()

    def open_screenshots(self):
        if self.store:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.store.root / "Screenshots")))

    def open_logs(self):
        path = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)) / "logs"
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def closeEvent(self, event):
        if self.active:
            self.stop_capture()
            self.notice("Capture is finishing. Close the app again after it has stopped.")
            event.ignore()
            return
        if self.builder_preview.running:
            self.notice("Document preview is finishing. Close the app again when it is ready.");event.ignore();return
        if self.busy:
            self.notice("Wait for the current operation to finish before closing.")
            event.ignore()
            return
        try:
            self.flush_save()
            self.word_editor.close_document()
            self.builder_preview.clear_document()
            # Windows holds each preview file open until its document closes.
            from PySide6.QtPdf import QPdfDocument
            for document in self.findChildren(QPdfDocument):
                document.close()
            for dialog in self.findChildren(QDialog):
                if dialog is not self.floating:
                    dialog.close()
            self.floating.hide()
            self.preview_dir.cleanup()
            if self.backend: self.backend.close()
            if self.store: self.store.release()
        except Exception as exc:
            self.fail(exc)
            event.ignore()
            return
        event.accept()
