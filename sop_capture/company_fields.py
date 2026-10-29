"""Retained company form cells and Word content-control data bindings."""
import re
from lxml import etree
from docx.oxml.ns import qn,nsmap


def xp(node,expression):
    return etree.XPath(expression,namespaces=nsmap)(node)
from docx.text.paragraph import Paragraph

LABELS={'documenttitle':'title','contractordocno':'reference','documentnumber':'reference',
        'reference':'reference','contractorrev':'version','rev':'version',
        'preparedby':'author','checkedby':'reviewer','approvedby':'approver','contractorname':'company'}
LABEL_NAMES=set(LABELS)|{'teamcenterid','legacydocno','ecscodes','positiontitle','status','amendment','date'}


def text(node):return ''.join(xp(node,'.//w:t/text()')).strip()


def normal(value):return re.sub('[^a-z0-9]','',value.lower())


def label_field(value):
    return LABELS.get(normal(value)) if not any(c in value for c in '<>[]') else None


def is_label(value):return normal(value) in LABEL_NAMES and not any(c in value for c in '<>[]')


def cells(row):
    return [c for c in xp(row,'.//w:tc') if xp(c,'ancestor::w:tr[1]')[0] is row]


def form_cells(document):
    """Each value cell, its readable label and any unambiguous project field."""
    for number,table in enumerate(xp(document.element.body,'.//w:tbl')):
        context='Company table '+str(number+1)
        for previous in table.itersiblings(preceding=True):
            if previous.tag==qn('w:p') and text(previous):context=text(previous);break
        rows=xp(table,'./w:tr')
        if not rows:continue
        headers=[text(c) for c in cells(rows[0])]
        tabular=all(is_label(h) for h in headers) and (any(normal(h) in {'preparedby','checkedby','approvedby'} for h in headers) or {'rev','status'}.issubset({normal(h) for h in headers}))
        for ri,row in enumerate(rows):
            row_cells=cells(row)
            for ci,cell in enumerate(row_cells):
                current=text(cell)
                if is_label(current) or (ri==0 and tabular):continue
                preceding=text(row_cells[ci-1]) if ci else ''
                canonical=label_field(headers[ci]) if tabular and ci<len(headers) else label_field(preceding)
                if not tabular and len(row_cells)>2 and not any(normal(text(c))=='contractorname' for c in cells(rows[0])):canonical=None
                if tabular and ri>1:canonical=None  # historical/extra rows must not repeat current metadata
                label=headers[ci] if tabular and ci<len(headers) else preceding if is_label(preceding) else (headers[ci] if ci<len(headers) and headers[ci] else 'Value')
                for pi,node in enumerate(xp(cell,'.//w:p')):
                    if xp(node,'ancestor::w:tc[1]')[0] is cell:
                        yield node,f'{context} / {label} (row {ri+1}, column {ci+1})',canonical


def update_control_binding(document,control):
    if xp(control,'.//w:sdt'):return  # grouped forms are not single-value controls
    binding=control.find('./'+qn('w:sdtPr')+'/'+qn('w:dataBinding'))
    if binding is None:return
    store_id=binding.get(qn('w:storeItemID'),'').casefold()
    xpath=binding.get(qn('w:xpath'),'')
    namespaces=dict(re.findall(r"xmlns:(\w+)\s*=\s*['\"]([^'\"]+)['\"]",binding.get(qn('w:prefixMappings'),'')))
    value=text(control)
    if 'coreProperties' in xpath:
        root=document.core_properties._element
        try:targets=etree.XPath(xpath,namespaces=namespaces)(root)
        except etree.XPathError:targets=[]
        for target in targets:
            if isinstance(target,etree._Element):target.text=value
    for part in document.part.package.parts:
        if not str(part.partname).startswith('/customXml/item') or 'Props' in str(part.partname):continue
        for relationship in part.rels.values():
            if relationship.is_external or not relationship.reltype.endswith('/customXmlProps'):continue
            props=etree.fromstring(relationship.target_part.blob)
            if (props.get('{http://schemas.openxmlformats.org/officeDocument/2006/customXml}itemID') or '').casefold()!=store_id:continue
            root=etree.fromstring(part.blob,etree.XMLParser(resolve_entities=False,no_network=True))
            try:targets=root.xpath(xpath,namespaces=namespaces)
            except etree.XPathError:return
            for target in targets:
                if isinstance(target,etree._Element):
                    target.text=value
                    target.attrib.pop('{http://www.w3.org/2001/XMLSchema-instance}nil',None)
            part._blob=etree.tostring(root,encoding='UTF-8',xml_declaration=True)
    # Synchronise repeated visual controls with the same binding, retaining all
    # control properties and formatting instead of flattening the Word form.
    from .word_template import replace_element_text
    for part in document.part.package.parts:
        root=getattr(part,'element',None)
        if root is None:continue
        for other in xp(root,'.//w:sdt'):
            other_binding=other.find('./'+qn('w:sdtPr')+'/'+qn('w:dataBinding'))
            if other is control or other_binding is None:continue
            if other_binding.get(qn('w:storeItemID'),'').casefold()==store_id and other_binding.get(qn('w:xpath'))==xpath:
                old=text(other)
                if old:replace_element_text(other,old,value)


def fill_form(document,project):
    from .word_template import replace_prompt,replace_element_text
    for node,label,canonical in form_cells(document):
        if not canonical:continue
        value=getattr(project,canonical,'')
        if not value:continue
        old=text(node)
        if old:replace_prompt(Paragraph(node,document.part),old,value)
        else:
            Paragraph(node,document.part).add_run(value)
        controls=xp(node,'ancestor::w:sdt')+xp(node,'.//w:sdt')
        for control in controls:update_control_binding(document,control)
    # A form may use bound title controls outside table cells (cover/header).
    for part in document.part.package.parts:
        root=getattr(part,'element',None)
        if root is None:continue
        for control in xp(root,'.//w:sdt'):
            tags=xp(control,'./w:sdtPr/w:alias/@w:val|./w:sdtPr/w:tag/@w:val')
            if any(normal(t) in {'documentx0020name','documenttitle','title'} for t in tags):
                old=text(control)
                if old:replace_element_text(control,old,project.title)
                update_control_binding(document,control)
