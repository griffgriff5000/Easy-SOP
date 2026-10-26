from pathlib import Path
from PySide6.QtCore import QSettings, QStandardPaths
from PySide6.QtWidgets import QWidget, QFormLayout, QSpinBox, QComboBox, QCheckBox, QLineEdit, QLabel, QVBoxLayout, QPushButton, QFileDialog

from ..windows import parse_hotkey


class SettingsPage(QWidget):
    def __init__(self, on_theme):
        super().__init__()
        self.settings = QSettings("SOPCaptureStudio", "SOPCaptureStudio")
        outer = QVBoxLayout(self)
        heading = QLabel("Settings")
        heading.setObjectName("heading")
        outer.addWidget(heading)
        form = QFormLayout()
        form.setVerticalSpacing(12)
        outer.addLayout(form)
        self.fields = {}
        self._spin(form, "delay", "Capture delay (ms)", 0, 5000, 400)
        self._combo(form, "timing", "Click timing", ["After click", "Recent pre-click frame"])
        self._combo(form, "buttons", "Mouse buttons", ["Left", "Left and right", "Left, right and middle"])
        self._text(form, "shortcut", "Manual capture shortcut", "Ctrl+Shift+F8")
        self._spin(form, "compression", "PNG lossless compression (0–9)", 0, 9, 6)
        self._check(form, "initial", "Capture initial screen", True)
        self._text(form, "marker_color", "Marker / highlight colour", "#ef4444")
        self._spin(form, "marker_size", "Marker radius (image pixels)", 5, 150, 24)
        self._check(form, "marker_numbers", "Show step numbers", True)
        self._text(form, "company", "Default company", "")
        self._text(form, "author", "Default author", "")
        self._text(form, "prefix", "SOP reference prefix", "SOP")
        self._text(form, "logo", "Default logo file (optional)", "")
        self._combo(form, "orientation", "PDF orientation", ["portrait", "landscape"])
        default = str(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)) / "SOP Capture Studio")
        self._text(form, "location", "Default project directory", default)
        self._combo(form, "theme", "Appearance", ["Light", "Dark"])
        self.fields["theme"].currentTextChanged.connect(lambda text: on_theme(text == "Dark"))
        outer.addWidget(QLabel("Privacy: selected window only • local processing • explicit recording only.\nScreenshots may contain visible sensitive information. Review and redact before export."))
        outer.addStretch()

    def value(self, name):
        widget = self.fields[name]
        if isinstance(widget, QSpinBox): return widget.value()
        if isinstance(widget, QCheckBox): return widget.isChecked()
        if isinstance(widget, QComboBox): return widget.currentText()
        return widget.text()

    def _text(self, form, name, label, default):
        widget = QLineEdit(str(self.settings.value(name, default)))
        widget.textChanged.connect(lambda value: self.settings.setValue(name, value))
        self.fields[name] = widget
        form.addRow(label, widget)

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
