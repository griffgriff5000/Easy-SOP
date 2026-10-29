"""Template catalogue, custom PDF appearance and imported Word style mapping."""
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QSplitter, QFormLayout, QLineEdit, QComboBox, QSpinBox, QCheckBox, QScrollArea, QFileDialog, QMessageBox, QInputDialog, QColorDialog, QGroupBox, QTabWidget)
from .components import page_header, menu_button, form_page, scroll_panel
from ..templates import appearance
from ..word_export import inspect_docx, create_example


class TemplatesPage(QWidget):
    def __init__(self, library, apply_callback, preview_callback,library_preview_callback=None):
        super().__init__()
        self.library, self.apply_callback, self.preview_callback = library, apply_callback, preview_callback
        self.library_preview_callback=library_preview_callback
        self.loading, self.dirty = True, False
        self.current_id = None
        self.source_docx = None
        layout = QVBoxLayout(self);layout.setSpacing(10)
        page_header(layout,"Templates","Choose a company layout or customise the standard SOP.")
        self.active_label = QLabel("Current SOP: Standard SOP");self.active_label.setObjectName("caption");self.active_label.setWordWrap(True)
        row = QHBoxLayout()
        row.addWidget(menu_button("New template",[("Custom template",self.new_custom),("Import Word template...",self.import_word),("Save example Word template...",self.example)]))
        self.save_button=self._button("Save",self.save_changes);row.addWidget(self.save_button)
        manage=menu_button("More",[("Save as new template",lambda:self.save_changes(as_new=True)),("Delete from library",self.delete_selected)])
        self.save_as_button,self.delete_button=manage.menu().actions();row.addWidget(manage);row.addStretch()
        self.preview_button=self._button("Preview template",self.preview_selected);row.addWidget(self.preview_button)
        self.apply_button=self._button("Apply template",self.apply_selected);self.apply_button.setObjectName("primary");row.addWidget(self.apply_button)
        layout.addLayout(row);layout.addWidget(self.active_label)
        splitter=QSplitter();self.catalogue=QListWidget();self.catalogue.setMinimumWidth(180);self.catalogue.setWordWrap(True);self.catalogue.currentItemChanged.connect(self._selected);splitter.addWidget(self.catalogue)
        self.template_tabs=QTabWidget()
        details,form=form_page();self.template_tabs.addTab(scroll_panel(details),"Details")
        self.name=QLineEdit();self.name.setMaxLength(120);self.name.textChanged.connect(self._edited);form.addRow("Template name",self.name)
        self.info=QLabel();self.info.setWordWrap(True);self.info.setObjectName("caption");form.addRow(self.info)
        self.logo=QLineEdit();self.logo.textChanged.connect(self._edited)
        logo_row=QHBoxLayout();logo_row.addWidget(self.logo,1);logo_row.addWidget(self._button("Browse...",self.choose_logo));logo_row.addWidget(self._button("Clear",self.logo.clear));form.addRow("Default logo",logo_row)
        self.fields={};self._text(form,"company","Default company")
        self._spin(form,"image_width_percent","Screenshot width (%)",30,100);self._check(form,"page_per_step","One step per page")
        self.pdf_group,pdf=form_page();self.template_tabs.addTab(scroll_panel(self.pdf_group),"Appearance")
        self._combo(pdf,"font","Font family",["Vera","Helvetica","Times-Roman","Courier"])
        for key,label,lo,hi in [("body_size","Body text (pt)",7,18),("heading_size","Step headings (pt)",10,30),("title_size","Cover title (pt)",18,44)]:self._spin(pdf,key,label,lo,hi)
        self._color(pdf,"heading_color","Heading colour");self._color(pdf,"text_color","Text colour")
        self._spin(pdf,"margin_mm","Page margin (mm)",10,35);self._combo(pdf,"orientation","Orientation",["project","portrait","landscape"]);self._check(pdf,"cover","Include cover page")
        self._text(pdf,"header","Header");self._text(pdf,"footer","Footer")
        note=QLabel("Header/footer fields: {title}, {reference}, {version}, {company}.");note.setWordWrap(True);note.setObjectName("caption");pdf.addRow(note)
        self.word_group,word=form_page();self.template_tabs.addTab(scroll_panel(self.word_group),"Word styles")
        for key,label in [("title_style","Document title style"),("heading_style","Step title style"),("body_style","Instructions style"),("caption_style","Screenshot caption style")]:self._combo(word,key,label,[])
        note=QLabel("Word templates retain their fonts, margins, logos, headers and footers. Fonts must be installed on this PC. Word-template PDF export requires desktop Microsoft Word; DOCX export does not.")
        note.setWordWrap(True);note.setObjectName("caption");word.addRow(note)
        splitter.addWidget(self.template_tabs);splitter.setSizes([220,800]);splitter.setStretchFactor(1,1);splitter.setCollapsible(0,False);splitter.setCollapsible(1,False);layout.addWidget(splitter,1)
        self.refresh()

    @staticmethod
    def _button(text, callback):
        button = QPushButton(text)
        button.clicked.connect(callback)
        return button

    def _edited(self, *args):
        if not self.loading: self.dirty = True

    def _text(self, form, key, label):
        widget = QLineEdit()
        widget.setMaxLength(500)
        widget.textChanged.connect(self._edited)
        self.fields[key] = widget
        form.addRow(label, widget)

    def _spin(self, form, key, label, low, high):
        widget = QSpinBox()
        widget.setRange(low, high)
        widget.valueChanged.connect(self._edited)
        self.fields[key] = widget
        form.addRow(label, widget)

    def _combo(self, form, key, label, values):
        widget = QComboBox()
        widget.addItems(values)
        widget.currentTextChanged.connect(self._edited)
        self.fields[key] = widget
        form.addRow(label, widget)

    def _check(self, form, key, label):
        widget = QCheckBox()
        widget.toggled.connect(self._edited)
        self.fields[key] = widget
        form.addRow(label, widget)

    def _color(self, form, key, label):
        widget = QLineEdit()
        widget.textChanged.connect(self._edited)
        self.fields[key] = widget
        row = QHBoxLayout()
        row.addWidget(widget)
        row.addWidget(self._button("Choose…", lambda: self.choose_colour(key)))
        form.addRow(label, row)

    def choose_colour(self, key):
        colour = QColorDialog.getColor(QColor(self.fields[key].text()), self, "Template colour")
        if colour.isValid(): self.fields[key].setText(colour.name())

    def values(self):
        settings = appearance()
        for key, field in self.fields.items():
            settings[key] = field.value() if isinstance(field, QSpinBox) else field.isChecked() if isinstance(field, QCheckBox) else field.currentText() if isinstance(field, QComboBox) else field.text()
        return appearance(settings)

    def refresh(self, identity="standard"):
        self.catalogue.blockSignals(True)
        self.catalogue.clear()
        profiles = self.library.list()
        for profile in profiles:
            item = QListWidgetItem(profile["name"]+ ("\nWord template" if profile["kind"] == "docx" else "\nPDF layout"))
            item.setData(Qt.ItemDataRole.UserRole, profile["id"])
            self.catalogue.addItem(item)
        index = next((i for i, p in enumerate(profiles) if p["id"] == identity), 0)
        self.catalogue.setCurrentRow(index)
        self.catalogue.blockSignals(False)
        self.load_profile(profiles[index])

    def _selected(self, item, previous):
        if not item: return
        if not self.confirm_discard():
            self.catalogue.blockSignals(True)
            self.catalogue.setCurrentItem(previous)
            self.catalogue.blockSignals(False)
            return
        try: self.load_profile(self.library.load(item.data(Qt.ItemDataRole.UserRole)))
        except Exception as exc: QMessageBox.warning(self, "Template unavailable", str(exc))

    def load_profile(self, profile):
        self.loading = True
        self.current_id = profile["id"]
        self.prepared=profile.get('prepared',False)
        self.source_docx = self.library.asset(profile, "docx") if profile["kind"] == "docx" else None
        logo = self.library.asset(profile, "logo") if profile.get("logo") else None
        self.name.setText(profile["name"])
        self.logo.setText(str(logo) if logo else "")
        settings = appearance(profile["settings"])
        styles = inspect_docx(self.source_docx)["styles"] if self.source_docx else ["Heading 2", "Normal", "Caption"]
        for key in ("title_style", "heading_style", "body_style", "caption_style"):
            self.fields[key].clear()
            self.fields[key].addItems(styles)
        for key, field in self.fields.items():
            value = settings[key]
            if isinstance(field, QSpinBox): field.setValue(int(value))
            elif isinstance(field, QCheckBox): field.setChecked(value)
            elif isinstance(field, QComboBox): field.setCurrentText(value)
            else: field.setText(value)
        self.pdf_group.setVisible(not bool(self.source_docx))
        self.word_group.setVisible(bool(self.source_docx))
        self.template_tabs.setTabVisible(1,not bool(self.source_docx))
        self.template_tabs.setTabVisible(2,bool(self.source_docx))
        self.info.setText("Word layout. Known fields: {{title}}, {{company}}, {{reference}}, {{author}}, {{purpose}}, {{scope}}, {{steps}}, {{logo}} and other document metadata. Place {{steps}} alone in a body paragraph." if self.source_docx else "Adjust the standard SOP appearance, enter a new name and save it to your library.")
        if self.prepared:self.info.setText('Company template prepared automatically. Covers, tables, section layout and styles are retained; recognised guidance and style examples are removed. Fill company values under Document > Builder > Source / preview > Template fields.')
        self.save_button.setEnabled(self.current_id != "standard")
        self.delete_button.setEnabled(self.current_id not in {None, "standard"})
        self.loading, self.dirty = False, False

    def new_custom(self):
        if not self.confirm_discard(): return
        from ..templates import standard_profile
        self.load_profile(standard_profile())
        self.current_id = None
        self.name.setText("My SOP template")
        self.save_button.setEnabled(True)
        self.template_tabs.setCurrentIndex(0)
        self.name.selectAll()
        self.name.setFocus()

    def choose_logo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Template logo", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path: self.logo.setText(path)

    def save_changes(self, checked=False, as_new=False):
        try:
            identity = None if as_new or self.current_id == "standard" else self.current_id
            profile = self.library.save(self.name.text(), self.values(), identity=identity, source_docx=self.source_docx, logo=self.logo.text() or None,prepared=self.prepared)
            self.refresh(profile["id"])
            return profile
        except Exception as exc:
            QMessageBox.warning(self, "Cannot save template", str(exc))

    def import_path(self, path, name):
        profile = self.library.save(name, {}, source_docx=path,prepare_word=True)
        self.refresh(profile["id"])
        return profile

    def import_word(self):
        if not self.confirm_discard(): return
        path, _ = QFileDialog.getOpenFileName(self, "Upload Word template", "", "Word documents (*.docx)")
        if not path: return
        try:
            inspect_docx(path)
            name, accepted = QInputDialog.getText(self, "Name this template", "Template name:", text=Path(path).stem)
            if accepted: self.import_path(path, name)
        except Exception as exc: QMessageBox.warning(self, "Cannot import Word template", str(exc))

    def confirm_discard(self):
        return not self.dirty or QMessageBox.question(self, "Unsaved template", "Discard the unsaved template changes?") == QMessageBox.StandardButton.Yes

    def example(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save example Word template", "SOP_template.docx", "Word document (*.docx)")
        if path:
            try: create_example(path)
            except Exception as exc: QMessageBox.warning(self, "Cannot save example", str(exc))

    def delete_selected(self):
        if self.current_id in {None, "standard"}: return
        if QMessageBox.question(self, "Delete template", "Remove this template from the library? Existing SOP snapshots will be retained.") == QMessageBox.StandardButton.Yes:
            try:
                self.library.delete(self.current_id)
                self.refresh()
            except Exception as exc: QMessageBox.warning(self, "Cannot delete template", str(exc))

    def apply_selected(self):
        if self.dirty:
            QMessageBox.information(self, "Save template first", "Save your template changes before applying it to an SOP.")
            return False
        try:
            self.apply_callback(self.current_id)
            return True
        except Exception as exc:
            QMessageBox.warning(self, "Cannot apply template", str(exc))
            return False

    def preview_selected(self):
        if self.library_preview_callback is not None:
            if self.dirty:
                QMessageBox.information(self,'Save template first','Save your template changes before previewing.');return
            self.library_preview_callback(self.current_id);return
        if self.apply_selected(): self.preview_callback()
