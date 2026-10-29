from pathlib import Path
from PySide6.QtCore import QSettings, QStandardPaths
from PySide6.QtWidgets import QWidget, QFormLayout, QSpinBox, QComboBox, QCheckBox, QLineEdit, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QTabWidget

from ..windows import parse_hotkey
from .components import page_header, form_page, scroll_panel


class SettingsPage(QWidget):
    def __init__(self, on_theme):
        super().__init__()
        self.settings = QSettings("SOPCaptureStudio", "SOPCaptureStudio")
        outer = QVBoxLayout(self)
        page_header(outer,"Settings","Capture preferences, document defaults and appearance.")
        self.actions = QHBoxLayout();outer.addLayout(self.actions)
        self.categories = QTabWidget();outer.addWidget(self.categories,1)
        self.category_indices = {}
        forms = {}
        for name in ("Capture","Annotations","Files and defaults","Appearance"):
            page,category_form = form_page();forms[name] = category_form
            self.category_indices[name] = self.categories.addTab(scroll_panel(page),name)
        form = forms["Capture"]
        self.fields = {}
        self._spin(form, "delay", "Capture delay (ms)", 0, 5000, 400)
        self._combo(form, "timing", "Click timing", ["After click", "Recent pre-click frame"])
        self._combo(form, "buttons", "Mouse buttons", ["Left", "Left and right", "Left, right and middle"])
        self._text(form, "shortcut", "Manual capture shortcut", "Ctrl+Shift+F8")
        self._spin(form, "compression", "PNG lossless compression (0–9)", 0, 9, 6)
        self._check(form, "initial", "Capture initial screen", True)
        form = forms["Annotations"]
        self._text(form, "marker_color", "Marker / highlight colour", "#ef4444")
        self._spin(form, "marker_size", "Marker radius (image pixels)", 5, 150, 24)
        self._check(form, "marker_numbers", "Show step numbers", True)
        form = forms["Files and defaults"]
        self._text(form, "company", "Default company", "")
        self._text(form, "author", "Default author", "")
        self._text(form, "prefix", "SOP reference prefix", "SOP")
        self._text(form, "logo", "Default logo file (optional)", "")
        self._combo(form, "orientation", "PDF orientation", ["portrait", "landscape"])
        default = str(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)) / "SOP Capture Studio")
        self._text(form, "location", "Default project directory", default, browse=True)
        form = forms["Appearance"]
        self._combo(form, "theme", "Appearance", ["Light", "Dark"])
        self.fields["theme"].currentTextChanged.connect(lambda text: on_theme(text == "Dark"))
        outer.addWidget(QLabel("Privacy: selected window only • local processing • explicit recording only.\nScreenshots may contain visible sensitive information. Review and redact before export."))


    def show_category(self, name):
        self.categories.setCurrentIndex(self.category_indices[name])

    def value(self, name):
        widget = self.fields[name]
        if isinstance(widget, QSpinBox): return widget.value()
        if isinstance(widget, QCheckBox): return widget.isChecked()
        if isinstance(widget, QComboBox): return widget.currentText()
        return widget.text()

    def _text(self, form, name, label, default, browse=False):
        widget = QLineEdit(str(self.settings.value(name, default)))
        widget.textChanged.connect(lambda value: self.settings.setValue(name, value))
        self.fields[name] = widget
        if browse:
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(widget, 1)
            choose = QPushButton("Browse…")
            choose.setToolTip("Choose the default project folder in File Explorer")
            choose.clicked.connect(self.browse_project_directory)
            layout.addWidget(choose)
            form.addRow(label, row)
        else:
            form.addRow(label, widget)

    def browse_project_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Choose default project directory", self.value("location"))
        if directory:
            self.fields["location"].setText(str(Path(directory)))

    def _spin(self, form, name, label, low, high, default):
        widget = QSpinBox()
        widget.setRange(low, high)
        widget.setValue(int(self.settings.value(name, default)))
        widget.valueChanged.connect(lambda value: self.settings.setValue(name, value))
        self.fields[name] = widget
        form.addRow(label, widget)

    def _combo(self, form, name, label, choices):
        widget = QComboBox()
        widget.addItems(choices)
        widget.setCurrentText(str(self.settings.value(name, choices[0])))
        widget.currentTextChanged.connect(lambda value: self.settings.setValue(name, value))
        self.fields[name] = widget
        form.addRow(label, widget)

    def _check(self, form, name, label, default):
        widget = QCheckBox()
        value = self.settings.value(name, default)
        widget.setChecked(value is True or str(value).lower() == "true")
        widget.toggled.connect(lambda value: self.settings.setValue(name, value))
        self.fields[name] = widget
        form.addRow(label, widget)
