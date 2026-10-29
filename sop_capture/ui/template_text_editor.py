"""Original Word paragraph/table-cell text controls for the document Builder."""
from copy import deepcopy
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QComboBox,QPlainTextEdit,QPushButton
from ..template_text import template_paragraphs,source_hash,validate_edits


class TemplateTextEditor(QWidget):
    changed=Signal(object)
    field_requested=Signal(str)
    def __init__(self,fields_only=False):
        super().__init__();self.setObjectName('scrollPage');self.loading=False;self.records=[];self.edits={};self.hash=None
        self.fields_only=fields_only
        box=QVBoxLayout(self);box.setSpacing(8)
        self.info=QLabel('Choose a Word template to edit its existing text here.');self.info.setWordWrap(True);self.info.setObjectName('caption');box.addWidget(self.info)
        self.picker=QComboBox();self.picker.setMinimumContentsLength(10);self.picker.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);box.addWidget(self.picker)
        self.text=QPlainTextEdit();self.text.setPlaceholderText('Select a template paragraph or table cell.');box.addWidget(self.text,1)
        self.field_button=QPushButton('Edit document field');self.field_button.clicked.connect(self.edit_field);box.addWidget(self.field_button)
        self.next_blank=QPushButton('Next blank or placeholder');self.next_blank.clicked.connect(self.next_unfinished);self.next_blank.setVisible(fields_only);box.addWidget(self.next_blank)
        self.picker.currentIndexChanged.connect(self.select_record);self.text.textChanged.connect(self.text_changed)
        self.set_source(None,{})

    def set_source(self,path,edits):
        self.loading=True;self.picker.clear();self.records=[];self.edits=deepcopy(edits);self.hash=None
        if path:
            try:
                self.records=template_paragraphs(path);self.hash=source_hash(path)
                if self.fields_only:self.records=[row for row in self.records if row.get('field_label')]
                if edits and edits['source_hash']!=self.hash:raise ValueError('Template text edits belong to another template. Reapply your template.')
                self.info.setText('Edit existing text without rebuilding the Word layout. Automatic fields and complex paragraphs stay protected.')
                if self.fields_only:self.info.setText('Fill retained company table cells below. Linked SOP fields use Document details. Direct document edits are retained until you explicitly rebuild from these source values.')
                for index,row in enumerate(self.records):
                    label=(row.get('field_label') if self.fields_only else row['text'].replace('\n',' ') or 'Blank table cell')[:110]
                    self.picker.addItem(f'{index+1}. {label}')
            except (ValueError,OSError) as exc:self.records=[];self.picker.clear();self.info.setText(str(exc))
        else:self.info.setText('This layout has no source Word document. Use Details and Company information to edit its content.')
        self.loading=False;self.select_record()

    def select_record(self,*args):
        if self.loading:return
        index=self.picker.currentIndex();row=self.records[index] if 0<=index<len(self.records) else None
        self.loading=True
        value=self.edits.get('paragraphs',{}).get(row['key'],{}).get('text',row['text']) if row else ''
        if self.fields_only and row and row.get('canonical') and getattr(self,'project',None):
            value=getattr(self.project,row['canonical'],'')
        self.text.setPlainText(value);self.text.setReadOnly(not row or not row['editable'] or bool(self.fields_only and row.get('canonical')))
        from ..word_export import TOKEN
        self.fields=[match.group(1) for match in TOKEN.finditer(row['text'])] if row else []
        if self.fields_only and row and row.get('canonical'):self.fields=[row['canonical']]
        if self.fields_only and row and not row['editable'] and not self.fields:self.fields=['__native__']
        self.field_button.setText('Edit on document' if self.fields==['__native__'] else 'Edit document field')
        self.field_button.setVisible(bool(self.fields))
        self.loading=False

    def edit_field(self):
        if self.fields:self.field_requested.emit(self.fields[0])

    def next_unfinished(self):
        import re
        for offset in range(1,len(self.records)+1):
            index=(self.picker.currentIndex()+offset)%len(self.records);row=self.records[index]
            value=self.edits.get('paragraphs',{}).get(row['key'],{}).get('text',row['text'])
            if row.get('canonical') and getattr(self,'project',None):value=getattr(self.project,row['canonical'],'')
            if not value.strip() or re.search(r'<[^>]+>|dd/mm/yyyy|9XXXXX',value):
                self.picker.setCurrentIndex(index);return

    def text_changed(self):
        if self.loading:return
        index=self.picker.currentIndex()
        if not 0<=index<len(self.records):return
        row=self.records[index]
        if not row['editable'] or (self.fields_only and row.get('canonical')):return
        text=self.text.toPlainText()
        if len(text)>20000:self.text.undo();return
        result=deepcopy(self.edits) or {'source_hash':self.hash,'paragraphs':{}}
        if text==row['text']:result['paragraphs'].pop(row['key'],None)
        else:result['paragraphs'][row['key']]={'original':row['text'],'text':text}
        if not result['paragraphs']:result={}
        try:validate_edits(result)
        except ValueError as exc:
            self.loading=True;self.text.undo();self.loading=False;self.info.setText(str(exc));return
        self.edits=result;self.changed.emit(deepcopy(result))
