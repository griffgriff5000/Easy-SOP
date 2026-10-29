"""Per-project Word text patches that retain the source document's structure."""
from hashlib import sha256
from difflib import SequenceMatcher
from pathlib import Path
import re
from docx import Document
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from lxml import etree


def source_hash(path):return sha256(Path(path).read_bytes()).hexdigest()


def validate_edits(value):
    if not isinstance(value,dict):raise ValueError('Invalid template text edits.')
    if not value:return
    if set(value)!={'source_hash','paragraphs'} or not isinstance(value['source_hash'],str) or len(value['source_hash'])!=64 or any(c not in '0123456789abcdef' for c in value['source_hash']):raise ValueError('Invalid template text source.')
    edits=value['paragraphs']
    if not isinstance(edits,dict) or len(edits)>1000:raise ValueError('Too many template text edits.')
    for key,edit in edits.items():
        if not isinstance(key,str) or len(key)>200 or not isinstance(edit,dict) or set(edit)!={'original','text'}:raise ValueError('Invalid template text edit.')
        if any(not isinstance(edit[name],str) or len(edit[name])>20000 for name in ('original','text')):raise ValueError('Template paragraphs support up to 20,000 characters.')
        if re.search(r'\{\{\s*[A-Za-z_]\w*\s*\}\}',edit['text']):raise ValueError('Use document fields for automatic values; template text edits cannot add insertion markers.')


def paragraph_records(document):
    from .word_export import TOKEN
    from .company_fields import form_cells
    form={node:(label,canonical) for node,label,canonical in form_cells(document)}
    for part in document.part.package.parts:
        element=getattr(part,'element',None)
        if element is None or etree.QName(element).localname not in {'document','hdr','ftr'}:continue
        for number,node in enumerate(element.xpath('.//w:p')):
            paragraph=Paragraph(node,part);text=paragraph.text
            if not text and not node.xpath('ancestor::w:tc'):continue
            complex_content=bool(node.xpath('.//w:drawing|.//w:pict|.//w:fldChar|.//w:fldSimple|.//w:object|.//w:txbxContent|.//w:ins|.//w:del|.//w:sdt'))
            run_nodes=node.xpath('.//w:r')
            text_children={'rPr','t','tab','br','cr'}
            complex_content=complex_content or any(etree.QName(child).localname not in text_children for run in run_nodes for child in run)
            run_text=''.join(Run(run,paragraph).text for run in run_nodes)
            editable=not complex_content and not TOKEN.search(text) and run_text==text and len(text)<=20000
            label,canonical=form.get(node,('',None))
            if not label and re.search(r'<[^>]+>',text):label=etree.QName(element).localname.title()+' / '+text[:90]
            if label and not text:text=''.join(node.xpath('.//w:t/text()'))
            yield {'key':str(part.partname)+':'+str(number),'text':text,'editable':editable,'location':etree.QName(element).localname,'field_label':label,'canonical':canonical},paragraph


def template_paragraphs(path):
    from .word_export import inspect_docx
    inspect_docx(path)
    return [record for record,_ in paragraph_records(Document(path))]


def edit_snapshot(path,changes):
    records={row['key']:row for row in template_paragraphs(path)};result={'source_hash':source_hash(path),'paragraphs':{}}
    for key,text in changes.items():
        row=records.get(key)
        if row is None or not row['editable']:raise ValueError('This paragraph contains a dynamic field or complex Word content. Use the document fields instead.')
        if text!=row['text']:result['paragraphs'][key]={'original':row['text'],'text':text}
    validate_edits(result)
    return result if result['paragraphs'] else {}


def replace_text_preserving_runs(paragraph,text):
    old=paragraph.text
    for operation,start,end,new_start,new_end in reversed(SequenceMatcher(None,old,text).get_opcodes()):
        if operation=='equal':continue
        replacement=text[new_start:new_end]
        runs=[Run(node,paragraph) for node in paragraph._p.xpath('.//w:r')]
        if not runs:paragraph.add_run(replacement);continue
        positioned=[];offset=0
        for run in runs:
            positioned.append((run,offset,offset+len(run.text)));offset+=len(run.text)
        if start==end:
            run,left,right=next(((r,a,b) for r,a,b in positioned if a<=start<=b),positioned[-1])
            index=max(0,min(len(run.text),start-left));run.text=run.text[:index]+replacement+run.text[index:]
        else:
            touched=[item for item in positioned if item[1]<end and item[2]>start]
            for index,(run,left,right) in enumerate(touched):
                a=max(0,start-left);b=min(len(run.text),end-left)
                run.text=run.text[:a]+(replacement if index==0 else '')+run.text[b:]


def apply_edits(document,path,edits):
    validate_edits(edits)
    if not edits:return
    if source_hash(path)!=edits['source_hash']:raise ValueError('The Word template has changed. Reapply the template before editing its text.')
    records={record['key']:(record,paragraph) for record,paragraph in paragraph_records(document)}
    for key,edit in edits['paragraphs'].items():
        row,paragraph=records.get(key,(None,None))
        if row is None or not row['editable'] or row['text']!=edit['original']:raise ValueError('A template paragraph has changed. Reapply the template before editing its text.')
        replace_text_preserving_runs(paragraph,edit['text'])
        controls=paragraph._p.xpath('ancestor::w:sdt')
        if controls:
            from .company_fields import update_control_binding
            update_control_binding(document,controls[-1])
