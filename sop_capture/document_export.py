from pathlib import Path
import tempfile
from .pdf_export import export_pdf as standard_pdf
from .storage import atomic_bytes


def export_pdf(project, root, output):
    if project.template.get("kind") != "docx": return standard_pdf(project, root, output)
    from .word_export import export_docx, word_pdf
    with tempfile.TemporaryDirectory(prefix="sop-word-") as temporary:
        docx = export_docx(project, root, Path(temporary) / "procedure.docx")
        pdf = word_pdf(docx, Path(temporary) / "procedure.pdf")
        atomic_bytes(output, pdf.read_bytes())
    return Path(output)
