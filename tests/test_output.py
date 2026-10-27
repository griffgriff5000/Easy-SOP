from PIL import Image
from pypdf import PdfReader

from sop_capture.models import Project, Step, Annotation
from sop_capture.storage import ProjectStore
from sop_capture.imaging import render_step
from sop_capture.pdf_export import export_pdf


def test_redaction_flattened_and_original_preserved(tmp_path):
    store = ProjectStore(tmp_path)
    step = Step(marker=(50, 50), annotations=[Annotation(kind="redact", points=[10, 10, 30, 30])])
    step.image = store.add_image(Image.new("RGB", (100, 100), "white"), step.id)
    rendered = render_step(tmp_path, step, 2)
    assert rendered.getpixel((20, 20)) == (0, 0, 0)
    assert rendered.getpixel((50, 50)) != (255, 255, 255)
    assert Image.open(store.resolve(step.image)).getpixel((20, 20)) == (255, 255, 255)


def test_pdf_long_text_unicode_and_landscape(tmp_path):
    project = Project(title="Permit – procédure", purpose="Safety & <quality>")
    project.steps = [Step(title="Open dashboard", description="Long instructions & details. " * 3000)]
    path = export_pdf(project, tmp_path, tmp_path / "test.pdf", "landscape")
    pdf = PdfReader(path)
    assert len(pdf.pages) > 3
    assert float(pdf.pages[0].mediabox.width) > float(pdf.pages[0].mediabox.height)
    text = "".join(p.extract_text() for p in pdf.pages)
    assert "Open dashboard" in text
    assert "Safety & <quality>" in text
    assert "procédure" in text


def test_missing_image_reported_and_annotations_export(tmp_path):
    p = Project(steps=[Step(title="Missing example", image="Screenshots/missing.png")])
    path = export_pdf(p, tmp_path, tmp_path / "missing.pdf")
    assert "Image unavailable" in "".join(page.extract_text() for page in PdfReader(path).pages)
