import pytest
from PIL import Image
from sop_capture.models import Project
from sop_capture.storage import ProjectStore
from sop_capture.templates import TemplateLibrary, appearance


def test_named_profiles_and_portable_snapshot(tmp_path):
    library = TemplateLibrary(tmp_path / "library")
    logo = tmp_path / "logo.png"
    Image.new("RGB", (100, 50), "blue").save(logo)
    profile = library.save("Company standard", {"font": "Helvetica", "body_size": 12, "footer": "Controlled document"}, logo=logo)
    assert [item["name"] for item in library.list()] == ["Standard SOP", "Company standard"]
    store = ProjectStore(tmp_path / "project")
    project = Project(template=library.snapshot(profile["id"], store.root))
    store.save(project)
    import json
    assert json.loads((store.root / "project.json").read_text())["schema_version"] == 2
    library.save("Company standard", {"body_size": 16}, identity=profile["id"])
    library.delete(profile["id"])
    loaded = store.load()
    assert loaded.template["settings"]["body_size"] == 12
    assert store.resolve(loaded.template["logo"]).exists()
    assert appearance(loaded.template["settings"])["footer"] == "Controlled document"


def test_duplicate_names_and_bad_parameters_rejected(tmp_path):
    library = TemplateLibrary(tmp_path)
    library.save("Quality", {})
    with pytest.raises(ValueError, match="name"):
        library.save("quality", {})
    with pytest.raises(ValueError): appearance({"body_size": -1})
    with pytest.raises(ValueError): appearance({"margin_mm": 100})
    with pytest.raises(ValueError): appearance({"heading_color": "bad-colour"})


def test_old_projects_and_snapshot_paths(tmp_path):
    data = Project().to_dict()
    data.pop("template", None)
    assert Project.from_dict(data).template == {}
    store = ProjectStore(tmp_path)
    with pytest.raises(ValueError):
        store.save(Project(template={"kind": "docx", "name": "Unsafe", "docx": "../other.docx", "settings": {}}))


def test_custom_pdf_uses_profile_and_keeps_project_metadata(tmp_path):
    from pypdf import PdfReader
    from sop_capture.pdf_export import export_pdf
    p = Project(title="Procedure", template={"kind": "custom", "name": "Corporate", "settings": {
        "font": "Helvetica", "body_size": 12, "heading_color": "#aa0000", "footer": "Controlled company copy",
        "company": "Example Limited", "orientation": "landscape", "cover": False, "margin_mm": 25}})
    pdf = PdfReader(export_pdf(p, tmp_path, tmp_path / "custom.pdf"))
    assert float(pdf.pages[0].mediabox.width) > float(pdf.pages[0].mediabox.height)
    assert "Controlled company copy" in pdf.pages[0].extract_text()
    assert p.company == ""


def test_small_margin_keeps_header_outside_body(tmp_path):
    from pypdf import PdfReader
    from sop_capture.pdf_export import export_pdf
    p = Project(template={"kind":"custom", "name":"Small", "settings":{"margin_mm":10,"cover":False,"header":"HEADER"}})
    page = PdfReader(export_pdf(p, tmp_path, tmp_path / "small.pdf")).pages[0]
    positions = {}
    def visit(text, cm, tm, font, size):
        if text.strip() in {"HEADER", "Document information"}: positions[text.strip()] = (tm[4]*cm[1]+tm[5]*cm[3]+cm[5], size)
    page.extract_text(visitor_text=visit)
    assert positions["HEADER"][0]-positions["Document information"][0] > positions["Document information"][1]+10
