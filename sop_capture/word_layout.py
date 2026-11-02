"""Lay out only the generated SOP, preserving surrounding Word template elements."""
from io import BytesIO
from math import ceil
from docx.shared import Inches
from docx.oxml.ns import qn
from .imaging import render_step
from .screenshot_layout import screenshot_groups,layout_columns
from .word_template import numbered


def append_steps(document,project,root,settings,paragraph,generated,heading,body,caption,prepared,section_width,max_height,procedure_heading=None):
    columns=layout_columns(settings);previous_section=''
    paginated=bool(settings['screenshots_per_page'] or settings['screenshot_layout']=='grid')
    page_height=min(s.page_height-s.top_margin-s.bottom_margin for s in document.sections)/914400
    groups=screenshot_groups(project.steps,settings)
    if paginated and groups and generated:
        last=generated[-1]
        if last.tag==qn('w:p') and not last.xpath('.//w:t') and last.xpath('./w:pPr/w:pageBreakBefore'):
            generated.pop();last.getparent().remove(last)
    for group_index,group in enumerate(groups):
        external_heading=procedure_heading if group_index==0 else None
        if paginated and external_heading is not None:
            external_heading.paragraph_format.page_break_before=True
            external_heading.paragraph_format.keep_with_next=True
        if paginated and columns>1 and external_heading is None:
            separator=paragraph(keep=True);separator.paragraph_format.page_break_before=True
            separator.paragraph_format.space_after=0;separator.paragraph_format.space_before=0
        table=None
        if columns>1:
            table=document.add_table(rows=ceil(len(group)/columns),cols=columns);table.autofit=False
            for column in table.columns:column.width=int(section_width/columns)
            for row in table.rows:
                for cell in row.cells:cell.width=int(section_width/columns)
            generated.append(table._tbl)
        height=max(.3,page_height/ceil(len(group)/columns)-1.25) if paginated else max_height/914400
        width=section_width/914400/columns*settings['image_width_percent']/100-(.16 if table is not None else 0)
        for index,(number,step) in enumerate(group):
            cell=table.cell(index//columns,index%columns) if table is not None else None
            def add(text='',name=body,keep=False):
                if cell is None:return paragraph(text,name,keep)
                if len(cell.paragraphs)==1 and not cell.paragraphs[0].text and not cell.paragraphs[0].runs:
                    p=cell.paragraphs[0];p.style=name;p.add_run(text)
                else:p=cell.add_paragraph(text,style=name)
                p.paragraph_format.keep_with_next=keep
                return p
            section_heading=add(step.section,heading,True) if step.section and step.section!=previous_section else None
            previous_section=step.section
            title=step.title if prepared and numbered(document.styles[heading]) else f'{number:02d}  {step.title}'
            title_paragraph=add(title,heading,True)
            if paginated and columns==1 and index==0 and external_heading is None:
                (section_heading if section_heading is not None else title_paragraph).paragraph_format.page_break_before=True
            if step.image:
                try:
                    image=render_step(root,step,number,project);data=BytesIO();image.save(data,'PNG');data.seek(0)
                    ratio=min(max(.2,width)/image.width,height/image.height)
                    add(keep=True).add_run().add_picture(data,width=Inches(image.width*ratio),height=Inches(image.height*ratio))
                    add(f'Step {number} screenshot',caption,True)
                except (OSError,ValueError):add('Image unavailable — replace the screenshot in the editor.')
            add(step.description)
            if step.notes:add('Notes / warnings: '+step.notes)
