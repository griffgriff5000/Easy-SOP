"""Synthetic template exports and UI/PDF visual verification on Windows."""
from pathlib import Path
import shutil
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw
from PySide6.QtCore import QSize, Qt, QBuffer, QIODevice
from PySide6.QtGui import QImage, QPainter
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QApplication
from sop_capture.templates import TemplateLibrary
from sop_capture.storage import ProjectStore
from sop_capture.word_export import create_example, export_docx
from sop_capture.document_export import export_pdf
from sop_capture.ui.main_window import MainWindow


def render(path, output, prefix):
    pdf = QPdfDocument()
    source = QBuffer()
    source.setData(path.read_bytes())
    source.open(QIODevice.OpenModeFlag.ReadOnly)
    pdf.load(source)
    for index in range(pdf.pageCount()):
        size = pdf.pagePointSize(index)
        image = pdf.render(index, QSize(int(size.width()*1.2), int(size.height()*1.2)))
        opaque = QImage(image.size(), QImage.Format.Format_RGB32)
        opaque.fill(Qt.GlobalColor.white)
        painter = QPainter(opaque)
        painter.drawImage(0, 0, image)
        painter.end()
        opaque.save(str(output / f"{prefix}-{index+1}.png"))
    count = pdf.pageCount()
    pdf.close()
    return count


def main():
    app = QApplication([])
    root = Path(__file__).resolve().parents[1]
    output = root / ".superpowers" / "templates"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sop-template-qa-") as temporary:
        temporary = Path(temporary)
        shutil.copytree(root / "demo" / "Permit Management", temporary / "project")
        store = ProjectStore(temporary / "project")
        project = store.load()
        logo = temporary / "logo.png"
        image = Image.new("RGB", (300, 100), "#115e59")
        ImageDraw.Draw(image).text((20, 40), "EXAMPLE COMPANY", fill="white")
        image.save(logo)
        library = TemplateLibrary(temporary / "library")
        custom = library.save("Company portrait", {"font": "Helvetica", "body_size": 11, "heading_color": "#115e59", "footer": "Controlled company copy | {reference}", "company": "Example Company", "margin_mm": 22}, logo=logo)
        window = MainWindow(template_library=library)
        window.set_project(project, store)
        window.apply_template(custom["id"])
        custom_pdf = window.export_to(output / "custom.pdf")
        print("Custom PDF pages:", render(custom_pdf, output, "custom"), flush=True)
        example = create_example(output / "company-template.docx")
        imported = window.templates_page.import_path(example, "Company Word")
        window.apply_template(imported["id"])
        docx = export_docx(window.project, store.root, output / "company-result.docx")
        print("Word generated:", docx.name, flush=True)
        pdf = export_pdf(window.project, store.root, output / "company.pdf")
        print("Word PDF pages:", render(pdf, output, "company"), flush=True)
        window.show_page(4)
        window.show()
        app.processEvents()
        window.grab().save(str(output / "templates-word.png"))
        window.templates_page.refresh(custom["id"])
        app.processEvents()
        window.grab().save(str(output / "templates-custom.png"))
        window.close()
    print("Template visual checks complete:", output, flush=True)


if __name__ == "__main__": main()
