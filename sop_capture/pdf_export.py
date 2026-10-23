from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image as PDFImage, KeepTogether

from .geometry import fit_rect
from .imaging import font_path, render_step
from .storage import ProjectStore, atomic_bytes


def export_pdf(project, root, output, orientation=None):
    output = Path(output)
    for name, bold in (("Vera", False), ("VeraBold", True)):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(font_path(bold))))
    page_size = landscape(A4) if (orientation or project.orientation) == "landscape" else A4
    stream = BytesIO()
    doc = SimpleDocTemplate(stream, pagesize=page_size, leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=22*mm, bottomMargin=20*mm, title=project.title, author=project.author)
    styles = getSampleStyleSheet()
    body = ParagraphStyle("SOPBody", fontName="Vera", fontSize=9, leading=14, spaceAfter=10, splitLongWords=True)
    heading = ParagraphStyle("SOPHeading", parent=body, fontName="VeraBold", fontSize=16, leading=21, textColor=colors.HexColor("#15344b"), spaceBefore=14, keepWithNext=True)
    title = ParagraphStyle("SOPTitle", parent=heading, fontSize=29, leading=36, spaceAfter=25)
    small = ParagraphStyle("SOPSmall", parent=body, fontSize=8, textColor=colors.HexColor("#526777"))
    story = []

    def para(text, style=body):
        return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)

    def content(text, style=body):
        # Bound individual paragraphs so very long user text always has split points.
        for line in str(text).split("\n"):
            for start in range(0, max(1, len(line)), 3000):
                story.append(para(line[start:start+3000], style))

    if project.logo:
        try:
            from PIL import Image
            logo_path = ProjectStore(root).resolve(project.logo)
            with Image.open(logo_path) as logo:
                w, h = fit_rect(logo.size, (140, 65))
            story.append(PDFImage(str(logo_path), width=w, height=h, hAlign="LEFT"))
        except (OSError, ValueError):
            story.append(para("Company logo unavailable", small))
    content(project.company or "STANDARD OPERATING PROCEDURE", small)
    story.append(Spacer(1, 30*mm))
    content(project.title, title)
    content(f"{project.reference}  |  Version {project.version}  |  {project.status}", heading)
    for label, value in (("Author", project.author), ("Created", project.created[:10]), ("Updated", project.updated[:10]), ("Reviewer", project.reviewer), ("Approver", project.approver)):
        content(f"{label}: {value or '—'}")
    story.append(PageBreak())
    content("Document information", heading)
    content(f"{project.title}\nReference: {project.reference}\nVersion: {project.version}\nStatus: {project.status}")
    for label, text in (("Purpose", project.purpose), ("Scope", project.scope), ("Prerequisites", project.prerequisites)):
        if text or label != "Prerequisites":
            content(label, heading)
            content(text or "Not specified.")
    content("Procedure", heading)
    if not project.steps:
        content("No procedural steps have been added.")
    for number, step in enumerate(project.steps, 1):
        step_heading = para(f"{number:02d}  {step.title}", heading)
        image_item = None
        if step.image:
            try:
                image = render_step(root, step, number, project)
                data = BytesIO()
                image.save(data, "PNG")
                data.seek(0)
                width, height = fit_rect(image.size, (doc.width, min(doc.height * .58, 350)))
                image_item = PDFImage(data, width=width, height=height)
            except (OSError, ValueError):
                image_item = para("Image unavailable — replace the screenshot in the editor.", small)
        group = [step_heading]
        if image_item:
            group += [image_item, Spacer(1, 10)]
        if len(step.description) < 600:
            group.append(para(step.description))
            story.append(KeepTogether(group))
        else:
            story.append(KeepTogether(group))
            content(step.description)
        if step.notes:
            content("Notes / warnings", small)
            content(step.notes)
        story.append(Spacer(1, 10))
    story.append(PageBreak())
    content("Revision history", heading)
    content(project.revision_history or "No revisions recorded.")

    def page(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d5e0e8"))
        canvas.line(doc.leftMargin, page_size[1]-16*mm, page_size[0]-doc.rightMargin, page_size[1]-16*mm)
        canvas.setFont("Vera", 8)
        canvas.setFillColor(colors.HexColor("#526777"))
        # Keep arbitrary metadata out of a fixed-width header.
        header = project.reference[:50] + "  |  " + project.status[:15]
        canvas.drawString(doc.leftMargin, page_size[1]-13*mm, header)
        canvas.drawString(doc.leftMargin, 12*mm, "SOP Capture Studio")
        canvas.drawRightString(page_size[0]-doc.rightMargin, 12*mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=page, onLaterPages=page)
    atomic_bytes(output, stream.getvalue())
    return output
