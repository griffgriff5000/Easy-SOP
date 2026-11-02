"""Paginated screenshot layouts for the standard PDF renderer."""
from io import BytesIO
from math import ceil
from xml.sax.saxutils import escape
from reportlab.platypus import Paragraph,Image,Spacer,PageBreak,KeepTogether,Table,TableStyle
from .screenshot_layout import screenshot_groups,layout_columns
from .geometry import fit_rect
from .imaging import render_step


def screenshot_pages(project,root,settings,doc,body,heading,small):
    result=[];previous_section='';columns=layout_columns(settings)
    def para(text,style=body):return Paragraph(escape(str(text)).replace('\n','<br/>'),style)
    def text(text,style=body):
        return [para(line[start:start+3000],style) for line in str(text).split('\n') for start in range(0,max(1,len(line)),3000)]
    for group_index,group in enumerate(screenshot_groups(project.steps,settings)):
        result.append(PageBreak())
        if group_index==0:result.append(para('Procedure',heading))
        rows=max(1,ceil(len(group)/columns));width=(doc.width-12*(columns-1))/columns
        max_image_height=min(350,max(24,(doc.height-55)/rows-95))
        cells=[]
        for number,step in group:
            block=[]
            if step.section and step.section!=previous_section:block.append(para(step.section,heading))
            previous_section=step.section
            block.append(para(f'{number:02d}  {step.title}',heading))
            if step.image:
                try:
                    image=render_step(root,step,number,project);data=BytesIO();image.save(data,'PNG');data.seek(0)
                    w,h=fit_rect(image.size,(max(12,width-12)*settings['image_width_percent']/100,max_image_height))
                    block.extend([Image(data,width=w,height=h),Spacer(1,8)])
                except (OSError,ValueError):block.append(para('Image unavailable — replace the screenshot in the editor.',small))
            description=text(step.description)
            notes=text('Notes / warnings: '+step.notes,small) if step.notes else []
            if columns==1:
                result.append(KeepTogether(block+(description if len(step.description)<600 else [])))
                if len(step.description)>=600:result.extend(description)
                result.extend(notes);result.append(Spacer(1,8))
            else:cells.append(block+description+notes)
        if columns>1:
            if len(cells)%columns:cells.append([])
            table=Table([cells[i:i+columns] for i in range(0,len(cells),columns)],colWidths=[width]*columns,hAlign='LEFT',splitInRow=1)
            table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),12)]))
            result.append(table)
    return result
