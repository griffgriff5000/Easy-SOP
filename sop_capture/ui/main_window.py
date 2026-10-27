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
    QButtonGroup, QSpinBox, QColorDialog,
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
    eyebrow = QLabel("SOP CAPTURE STUDIO")
    eyebrow.setObjectName("eyebrow")
    layout.addWidget(eyebrow)
    label = QLabel(title)
    label.setObjectName("heading")
    layout.addWidget(label)
    sub = QLabel(subtitle)
    sub.setObjectName("subheading")
    sub.setWordWrap(True)
    layout.addWidget(sub)


def scroll(widget):
    widget.setObjectName("scrollPage")
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(widget)
    return area


class MainWindow(QMainWindow):
    def __init__(self, template_library=None):
        super().__init__()
        self.setWindowTitle("SOP Capture Studio")
        self.resize(1320, 900)
        self.setMinimumSize(1000, 700)
        self.project = self.store = self.target = None
        self.template_library = template_library
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
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(24)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(16, 24, 16, 20)
        brand = QLabel("SOP\nCapture Studio")
        brand.setStyleSheet("font-size: 23px; font-weight: 700; padding: 12px 0 30px;")
        side.addWidget(brand)
        self.pages = QStackedWidget()
        self.nav_group = QButtonGroup(self)
        self.nav_buttons = []
        for index, text in enumerate(("01   Capture", "02   Step editor", "03   Document", "04   Settings", "05   Templates")):
            nav = button(text, lambda checked=False, i=index: self.show_page(i))
            nav.setCheckable(True)
            self.nav_group.addButton(nav)
            self.nav_buttons.append(nav)
            side.addWidget(nav)
        side.addStretch()
        local = QLabel("LOCAL BY DESIGN\nYour captures stay on this PC.")
        local.setWordWrap(True)
        local.setStyleSheet("font-size: 10px; padding: 12px 0;")
        side.addWidget(local)
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
        self.templates_page = TemplatesPage(self.template_library, self.apply_template, self.preview_pdf)
        self.pages.addWidget(self.templates_page)
        layout.addWidget(sidebar)
        layout.addWidget(self.pages, 1)
        self.setCentralWidget(root)
        self.show_page(0)
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
        for label, shortcut, callback in (("New SOP", "Ctrl+N", self.new_project), ("Open SOP", "Ctrl+O", self.open_project),
                                          ("Save", "Ctrl+S", self._autosave), ("Undo", "Ctrl+Z", self.undo), ("Redo", "Ctrl+Y", self.redo)):
            action = QAction(label, self)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(callback)
            self.addAction(action)
        help_menu = self.menuBar().addMenu("&Help")
        self.help_action = QAction("User guide", self)
        self.help_action.setShortcut(QKeySequence("F1"))
        self.help_action.triggered.connect(lambda: self.show_help())
        help_menu.addAction(self.help_action)
        shortcuts = help_menu.addAction("Keyboard shortcuts")
        shortcuts.triggered.connect(lambda: self.show_help("Keyboard shortcuts"))
        help_menu.addSeparator()
        help_menu.addAction("Open logs", self.open_logs)
        help_menu.addSeparator()
        help_menu.addAction("About SOP Capture Studio", self.show_about)

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
        heading(box, "Make a process easy to follow.", "Select one application, record its steps, then turn them into a clear procedure.")
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
        row.addWidget(QLabel("APPLICATION WINDOW"))
        row.addStretch()
        self.refresh_button = button("Refresh windows", self.refresh_windows)
        self.preview_button = button("Preview selection", self.preview_target)
        row.addWidget(self.refresh_button)
        row.addWidget(self.preview_button)
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
        box.addWidget(note)
        box.addWidget(button("Open Windows notification settings", lambda: QDesktopServices.openUrl(QUrl("ms-settings:notifications"))))
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
        page = QWidget()
        box = QVBoxLayout(page)
        heading(box, "Every step, clearly explained.", "Duplicate a step to reuse its screenshot. Use Edit annotations to drag shapes or resize their handles.")
        actions = QHBoxLayout()
        for text, callback in (("Add step", self.add_step), ("Duplicate step", self.duplicate_step), ("Delete", self.delete_step), ("Move up", lambda: self.move_step(-1)),
                               ("Move down", lambda: self.move_step(1)), ("Undo", self.undo), ("Redo", self.redo)):
            actions.addWidget(button(text, callback))
        actions.addStretch()
        self.preview_pdf_button = button("Preview PDF", self.preview_pdf)
        self.export_button = button("Export PDF", self.export_dialog, True)
        actions.addWidget(self.preview_pdf_button)
        actions.addWidget(self.export_button)
        box.addLayout(actions)
        export_row = QHBoxLayout()
        self.selected_template_label = QLabel("Template: Standard SOP")
        export_row.addWidget(self.selected_template_label, 1)
        export_row.addWidget(button("Choose template…", lambda: self.show_page(4)))
        export_row.addWidget(button("Export Word…", self.export_word_dialog))
        box.addLayout(export_row)
        splitter = QSplitter()
        self.steps_list = QListWidget()
        self.steps_list.setIconSize(QSize(130, 72))
        self.steps_list.setWordWrap(True)
        self.steps_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.steps_list.currentRowChanged.connect(self._select_step)
        self.steps_list.model().rowsMoved.connect(self._list_reordered)
        splitter.addWidget(self.steps_list)
        self.editor_panel = QWidget()
        right = QVBoxLayout(self.editor_panel)
        right.setContentsMargins(12, 0, 0, 0)
        self.step_title = QLineEdit()
        self.step_title.setPlaceholderText("Step title — what should the reader do?")
        self.step_title.textChanged.connect(self._step_fields_changed)
        right.addWidget(self.step_title)
        self.step_description = QPlainTextEdit()
        self.step_description.setPlaceholderText("Instructions for this step…")
        self.step_description.setMaximumHeight(120)
        self.step_description.textChanged.connect(self._step_fields_changed)
        right.addWidget(self.step_description)
        tools = QHBoxLayout()
        self.tool_picker = QComboBox()
        for label, tool in (("Move click marker", "marker"), ("Edit annotations", "edit"), ("Arrow", "arrow"), ("Straight line", "line"),
                            ("Circle / ellipse", "circle"), ("Outline box", "highlight"), ("Translucent highlight", "highlighter"),
                            ("Text label", "text"), ("Solid redaction", "redact"), ("Blur", "blur")):
            self.tool_picker.addItem(label, tool)
        self.canvas = AnnotationCanvas()
        self.tool_picker.currentIndexChanged.connect(lambda: self.canvas.set_tool(self.tool_picker.currentData()))
        self.canvas.changing.connect(self.checkpoint)
        self.canvas.changed.connect(self.edited)
        tools.addWidget(self.tool_picker)
        self.delete_annotation_button = button("Delete selected", self.canvas.delete_selected)
        self.delete_annotation_button.setEnabled(False)
        self.delete_annotation_button.setToolTip("Choose Edit annotations, then click a shape to select it")
        self.canvas.selection_changed.connect(self.delete_annotation_button.setEnabled)
        tools.addWidget(self.delete_annotation_button)
        tools.addWidget(button("Remove last annotation", self.remove_annotation))
        self.marker_check = QCheckBox("Click marker")
        self.marker_check.toggled.connect(self._marker_toggled)
        tools.addWidget(self.marker_check)
        tools.addWidget(button("Remove marker", self.remove_marker))
        right.addLayout(tools)
        self.arrow_style_picker = QComboBox()
        self.arrow_style_picker.setIconSize(QSize(128, 36))
        self.arrow_style_picker.setToolTip("Arrow style — choose the example you want to draw")
        self.arrow_style_picker.setMaximumWidth(340)
        for label, value in (("Solid arrow", "solid"), ("Open arrow", "open"), ("Double-headed arrow", "double")):
            sample = Step(annotations=[Annotation(kind="arrow", points=[12, 18, 116, 18], width=3, color="#2563eb", arrow_style=value)])
            icon = QIcon(image_pixmap(render_image(Image.new("RGB", (128, 36), "white"), sample, 1)))
            self.arrow_style_picker.addItem(icon, label, value)
        self.arrow_style_picker.currentIndexChanged.connect(lambda: self._annotation_style_changed("arrow_style", self.arrow_style_picker.currentData()))
        right.addWidget(self.arrow_style_picker)
        styling = QHBoxLayout()
        self.annotation_colour = button("Colour…", self.choose_annotation_colour)
        styling.addWidget(self.annotation_colour)
        self.annotation_width = QSpinBox()
        self.annotation_width.setRange(1, 30)
        self.annotation_width.setSuffix(" px")
        self.annotation_width.setToolTip("Line thickness in screenshot pixels")
        styling.addWidget(QLabel("Stroke"))
        styling.addWidget(self.annotation_width)
        self.annotation_font_size = QSpinBox()
        self.annotation_font_size.setRange(8, 144)
        self.annotation_font_size.setSuffix(" px")
        styling.addWidget(QLabel("Text size"))
        styling.addWidget(self.annotation_font_size)
        self.annotation_opacity = QSpinBox()
        self.annotation_opacity.setRange(0, 100)
        self.annotation_opacity.setSuffix(" %")
        styling.addWidget(QLabel("Highlight opacity"))
        styling.addWidget(self.annotation_opacity)
        styling.addStretch()
        right.addLayout(styling)
        self.annotation_text = QLineEdit("Text label")
        self.annotation_text.setMaxLength(5000)
        self.annotation_text.setPlaceholderText("Type your label, then drag a box on the screenshot")
        self.annotation_text.setToolTip("Text wraps inside the box. Resize the box or reduce text size if it is clipped.")
        right.addWidget(self.annotation_text)
        for widget, name in ((self.annotation_width, "width"), (self.annotation_font_size, "font_size"), (self.annotation_opacity, "opacity")):
            widget.valueChanged.connect(lambda value, key=name: self._annotation_style_changed(key, value))
        self.annotation_text.textChanged.connect(lambda value: self._annotation_style_changed("text", value))
        self.canvas.style_changed.connect(self._sync_annotation_controls)
        self._sync_annotation_controls()
        preview_help = QLabel("Drag to preview · Release to place · Esc to cancel · Edit annotations to change existing shapes")
        preview_help.setWordWrap(True)
        preview_help.setObjectName("subheading")
        right.addWidget(preview_help)
        right.addWidget(self.canvas, 1)
        files = QHBoxLayout()
        files.addWidget(button("Replace screenshot…", self.replace_image))
        files.addWidget(button("Retake selected window", self.retake_image))
        files.addWidget(button("Save annotated PNG", self.save_annotated))
        files.addStretch()
        right.addLayout(files)
        self.step_notes = QLineEdit()
        self.step_notes.setPlaceholderText("Optional notes or warnings")
        self.step_notes.textChanged.connect(self._step_fields_changed)
        right.addWidget(self.step_notes)
        splitter.addWidget(self.editor_panel)
        splitter.setSizes([250, 800])
        box.addWidget(splitter, 1)
        return page

    def _document_page(self):
        page = QWidget()
        box = QVBoxLayout(page)
        heading(box, "Give your procedure a context.", "Document details appear on the cover and throughout the exported PDF.")
        form = QFormLayout()
        form.setVerticalSpacing(12)
        self.document_fields = {}
        for name, label in (("title", "SOP title"), ("company", "Company"), ("reference", "Reference"), ("version", "Version"),
                            ("author", "Author"), ("reviewer", "Reviewer"), ("approver", "Approver"), ("created", "Created (ISO date/time)")):
            field = QLineEdit()
            field.textChanged.connect(self._document_changed)
            self.document_fields[name] = field
            form.addRow(label, field)
        for name, label, values in (("status", "Status label", ["Draft", "Approved"]), ("orientation", "PDF orientation", ["portrait", "landscape"])):
            field = QComboBox()
            field.addItems(values)
            field.currentTextChanged.connect(self._document_changed)
            self.document_fields[name] = field
            form.addRow(label, field)
        for name, label in (("purpose", "Purpose"), ("scope", "Scope"), ("prerequisites", "Prerequisites"), ("revision_history", "Revision history")):
            field = QPlainTextEdit()
            field.setMinimumHeight(70)
            field.setMaximumHeight(110)
            field.textChanged.connect(self._document_changed)
            self.document_fields[name] = field
            form.addRow(label, field)
        box.addLayout(form)
        row = QHBoxLayout()
        row.addWidget(button("Choose company logo…", self.choose_logo))
        row.addWidget(button("Remove logo", self.remove_logo))
        self.logo_label = QLabel("No logo")
        row.addWidget(self.logo_label, 1)
        box.addLayout(row)
        annotation = QHBoxLayout()
        self.marker_color = QLineEdit()
        self.marker_color.setMaximumWidth(120)
        self.marker_size = QSpinBox()
        self.marker_size.setRange(5, 150)
        self.marker_numbers = QCheckBox("Show step numbers")
        annotation.addWidget(QLabel("Marker colour"))
        annotation.addWidget(self.marker_color)
        annotation.addWidget(QLabel("Radius"))
        annotation.addWidget(self.marker_size)
        annotation.addWidget(self.marker_numbers)
        annotation.addWidget(button("Apply marker style", self.apply_marker_style))
        box.addLayout(annotation)
        box.addWidget(QLabel("Approved is a document label; it does not implement an approval workflow.\nLast updated is maintained automatically when the project is saved."))
        box.addStretch()
        return scroll(page)

    def show_page(self, index):
        self.pages.setCurrentIndex(index)
        self.nav_buttons[index].setChecked(True)
        page = self.pages.widget(index)
        if isinstance(page, QScrollArea):
            page.verticalScrollBar().setValue(0)

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
        self.templates_page.apply_button.setEnabled(ready)
        self.templates_page.preview_button.setEnabled(ready)
        self.screenshots_button.setEnabled(self.store is not None)
        self.editor_panel.setEnabled(ready and self.current_step() is not None)

    def set_project(self, project, store):
        if self.active or self.busy:
            raise RuntimeError("Finish capture or the current operation first")
        if self.store:
            self.flush_save()
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

    def new_project(self):
        if self.active or self.busy: return
        title, accepted = QInputDialog.getText(self, "New SOP", "Procedure title:")
        if not accepted or not title.strip(): return
        parent = QFileDialog.getExistingDirectory(self, "Choose project parent directory", self.settings.value("location"))
        if not parent: return
        safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip(" .")[:100] or "Procedure"
        folder = Path(parent) / f"SOP - {safe}"
        suffix = 2
        while folder.exists():
            folder = Path(parent) / f"SOP - {safe} ({suffix})"
            suffix += 1
        project = Project(title=title.strip(), company=self.settings.value("company"), author=self.settings.value("author"),
                          reference=f"{self.settings.value('prefix')}-001", orientation=self.settings.value("orientation"))
        try:
            ImageColor.getrgb(self.settings.value("marker_color"))
            project.marker_color = self.settings.value("marker_color")
            project.marker_size = self.settings.value("marker_size")
            project.marker_numbers = self.settings.value("marker_numbers")
            self.set_project(project, ProjectStore(folder))
            logo = self.settings.value("logo")
            if logo:
                self._set_logo(logo)
            self.refresh_windows()
            self.show_page(0)
        except Exception as exc:
            self.fail(exc)

    def open_project(self):
        if self.active or self.busy: return
        path, _ = QFileDialog.getOpenFileName(self, "Open SOP project", self.settings.value("location"), "SOP project (project.json project.backup.json)")
        if not path: return
        store = ProjectStore(Path(path).parent)
        if self.store and store.root == self.store.root:
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
        if self.loading or not self.project: return
        self.save_timer.start()
        self._refresh_list_labels()
        self._update_controls()

    def undo(self):
        if not self.history or self.active or self.busy: return
        self.future.append(deepcopy(self.project))
        self.project = self.history.pop()
        self._refresh_project()
        self.edited()

    def redo(self):
        if not self.future or self.active or self.busy: return
        self.history.append(deepcopy(self.project))
        self.project = self.future.pop()
        self._refresh_project()
        self.edited()

    def flush_save(self):
        self.save_timer.stop()
        if self.project and self.store:
            self.store.save(self.project)
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
        self.marker_color.setText(self.project.marker_color)
        self.marker_size.setValue(self.project.marker_size)
        self.marker_numbers.setChecked(self.project.marker_numbers)
        self.logo_label.setText(self.project.logo or "No logo")
        self.loading = False
        self._refresh_steps()

    def _template_status(self):
        name = self.project.template.get("name", "Standard SOP") if self.project else "Standard SOP"
        self.selected_template_label.setText("Template: "+name)
        self.templates_page.active_label.setText("Current SOP template: "+name+". Apply a library template to change it; saved SOPs keep their own snapshot.")

    def apply_template(self, identity):
        if not self.project or self.active or self.busy: raise ValueError("Open an SOP and finish the current operation first")
        snapshot = self.template_library.snapshot(identity, self.store.root)
        previous = self.project.template
        history, future = list(self.history), list(self.future)
        self.checkpoint()
        self.project.template = snapshot
        try:
            self.flush_save()
        except Exception:
            self.project.template = previous
            self.history, self.future = history, future
            self._template_status()
            raise
        self._template_status()
        self.notice("Template applied to this SOP. Preview the result before exporting.")

    def _refresh_steps(self, selected=None):
        previous = self.steps_list.currentRow()
        self.loading = True
        self.steps_list.clear()
        for index, step in enumerate(self.project.steps):
            item = QListWidgetItem(f"{index+1:02d}   {step.title}")
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
            if item: item.setText(f"{index+1:02d}   {step.title}")

    def _select_step(self, index):
        if self.loading: return
        self.loading = True
        step = self.current_step()
        self.step_title.setText(step.title if step else "")
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
        step.description = self.step_description.toPlainText()
        step.notes = self.step_notes.text()
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
        self.annotation_colour.setEnabled(kind in {"arrow", "line", "circle", "highlight", "highlighter", "text"})
        self.annotation_width.setEnabled(kind in {"arrow", "line", "circle", "highlight"})
        self.annotation_font_size.setEnabled(kind == "text")
        self.annotation_opacity.setEnabled(kind == "highlighter")
        self.annotation_text.setVisible(kind == "text")
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
        if not self.project or self.busy or self.active: return
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
        if not self.project or self.busy: return
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
            from PySide6.QtPdf import QPdfDocument
            from PySide6.QtPdfWidgets import QPdfView
            dialog = QDialog(self)
            dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            dialog.setWindowTitle("PDF preview — review sensitive information before export")
            dialog.resize(950, 850)
            layout = QVBoxLayout(dialog)
            view = QPdfView(dialog)
            document = QPdfDocument(dialog)
            # Qt PDF's renderer can retain a file handle after close(). Keep the
            # preview's source in a parent-owned memory buffer instead.
            source = QBuffer(dialog)
            source.setData(value.read_bytes())
            source.open(QIODevice.OpenModeFlag.ReadOnly)
            document.load(source)
            dialog.finished.connect(document.close)
            view.setDocument(document)
            view.setPageMode(QPdfView.PageMode.MultiPage)
            view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
            layout.addWidget(view)
            layout.addWidget(button("Close preview", dialog.close))
            dialog.show()
        self.run_task(lambda: export_pdf(project, root, path), finished)

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
        if self.busy:
            self.notice("Wait for the current operation to finish before closing.")
            event.ignore()
            return
        try:
            self.flush_save()
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
