"""Small rich-text editor for company information preceding captured SOP steps."""
from PySide6.QtCore import Signal,Qt
from PySide6.QtGui import QTextDocument,QTextCharFormat,QTextCursor,QFont,QTextListFormat,QTextTableFormat,QTextLength
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QTextEdit,QComboBox,QToolButton,QDialog,QFormLayout,QSpinBox,QDialogButtonBox
from ..company_information import parse_information,information_html
from .components import menu_button


class LocalTextDocument(QTextDocument):
    def loadResource(self,resource_type,name):
        # This editor is text/tables only; HTML never loads local or remote assets.
        return None


class BasicTextEdit(QTextEdit):
    problem=Signal(str)

    def __init__(self):
        super().__init__()
        self.setDocument(LocalTextDocument(self))
        self.document().setDocumentMargin(16)
        self.setAcceptRichText(True)

    def insertFromMimeData(self,source):
        if len(self.toPlainText())+len(source.text())>50_000:
            self.problem.emit('Paste is too large. Company information supports up to 50,000 text characters.');return
        if source.hasHtml():
            try:self.textCursor().insertHtml(information_html(parse_information(source.html())))
            except ValueError as exc:self.problem.emit(str(exc))
        elif source.hasText():self.textCursor().insertText(source.text())


class CompanyInformationEditor(QWidget):
    changed=Signal(str)
    problem=Signal(str)

    def __init__(self):
        super().__init__()
        self.syncing=False
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(8)
        tools=QHBoxLayout()
        self.heading=QComboBox()
        for title,level in [('Normal text',0),('Heading 1',1),('Heading 2',2),('Heading 3',3)]:self.heading.addItem(title,level)
        self.heading.currentIndexChanged.connect(lambda:self.set_heading(self.heading.currentData()))
        tools.addWidget(self.heading)
        self.formats={}
        for title,key in [('Bold','bold'),('Italic','italic'),('Underline','underline')]:
            button=QToolButton();button.setText(title[0]);button.setToolTip(title);button.setAccessibleName(title);button.setCheckable(True)
            button.clicked.connect(lambda checked,k=key:self.set_format(k,checked));tools.addWidget(button);self.formats[key]=button
        extras=QHBoxLayout()
        extras.addWidget(menu_button('List',[('Bulleted list',lambda:self.set_list('bullet')),('Numbered list',lambda:self.set_list('number')),('Remove list',lambda:self.set_list(None))]))
        table=QToolButton();table.setText('Table...');table.setToolTip('Insert a simple company-information table');table.clicked.connect(self.table_dialog);extras.addWidget(table);extras.addStretch();tools.addStretch()
        layout.addLayout(tools);layout.addLayout(extras)
        self.text=BasicTextEdit();self.text.setPlaceholderText('Enter the company-required information here. Add headings, lists or a table as needed.\n\nYour captured SOP steps will follow this section automatically.')
        layout.addWidget(self.text,1)
        self.text.textChanged.connect(self.text_changed);self.text.cursorPositionChanged.connect(self.sync_format)
        self.text.problem.connect(self.problem)

    def set_content(self,value):
        self.text.blockSignals(True);self.text.setHtml(value);self.text.blockSignals(False);self.sync_format()

    def content(self):
        html=self.text.toHtml()
        return html if parse_information(html) else ''

    def text_changed(self):
        try:self.changed.emit(self.content())
        except ValueError as exc:self.problem.emit(str(exc))

    def sync_format(self):
        self.syncing=True
        char=self.text.currentCharFormat()
        for key,value in [('bold',char.fontWeight()>=QFont.Weight.DemiBold),('italic',char.fontItalic()),('underline',char.fontUnderline())]:self.formats[key].setChecked(value)
        self.heading.setCurrentIndex(max(0,self.heading.findData(self.text.textCursor().blockFormat().headingLevel())))
        self.syncing=False

    def set_format(self,key,enabled):
        if self.syncing:return
        fmt=QTextCharFormat()
        if key=='bold':fmt.setFontWeight(QFont.Weight.Bold if enabled else QFont.Weight.Normal)
        elif key=='italic':fmt.setFontItalic(enabled)
        else:fmt.setFontUnderline(enabled)
        self.text.mergeCurrentCharFormat(fmt);self.text.setFocus()

    def set_heading(self,level):
        if self.syncing:return
        cursor=self.text.textCursor();cursor.beginEditBlock();block=cursor.blockFormat();block.setHeadingLevel(level);cursor.mergeBlockFormat(block)
        selected=QTextCursor(cursor);selected.select(QTextCursor.SelectionType.BlockUnderCursor)
        fmt=QTextCharFormat();fmt.setFontPointSize({0:10,1:18,2:15,3:12}[level]);fmt.setFontWeight(QFont.Weight.Bold if level else QFont.Weight.Normal)
        selected.mergeCharFormat(fmt);cursor.endEditBlock();self.text.setTextCursor(cursor);self.text.setCurrentCharFormat(fmt);self.text.setFocus()

    def set_list(self,kind):
        cursor=self.text.textCursor();cursor.beginEditBlock()
        if kind is None:
            block=cursor.blockFormat();block.setObjectIndex(-1);block.setIndent(0);cursor.setBlockFormat(block)
        else:
            fmt=QTextListFormat();fmt.setStyle(QTextListFormat.Style.ListDisc if kind=='bullet' else QTextListFormat.Style.ListDecimal);cursor.createList(fmt)
        cursor.endEditBlock();self.text.setFocus()

    def insert_table(self,rows,columns):
        if self.text.textCursor().currentTable() is not None:
            self.problem.emit('Move the cursor outside the current table before inserting another one.');return
        fmt=QTextTableFormat();fmt.setBorder(1);fmt.setCellPadding(5);fmt.setCellSpacing(0);fmt.setWidth(QTextLength(QTextLength.Type.PercentageLength,100))
        self.text.textCursor().insertTable(rows,columns,fmt);self.text.setFocus()

    def table_dialog(self):
        dialog=QDialog(self);dialog.setWindowTitle('Insert information table');form=QFormLayout(dialog)
        rows,columns=QSpinBox(),QSpinBox();rows.setRange(1,20);columns.setRange(1,6);rows.setValue(4);columns.setValue(2)
        form.addRow('Rows',rows);form.addRow('Columns',columns)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
        if dialog.exec():self.insert_table(rows.value(),columns.value())
