import math
import pytest
from pypdf import PdfReader

from sop_capture.models import Project, Step
from sop_capture.pdf_export import export_pdf


@pytest.mark.parametrize("field,value", [("created", 123), ("marker_color", "not-a-color"), ("marker_size", "large")])
def test_project_rejects_invalid_rendering_metadata(field, value):
    data = Project().to_dict()
    data[field] = value
    with pytest.raises(ValueError):
        Project.from_dict(data)


def test_project_rejects_nonfinite_coordinates():
    data = Project(steps=[Step(marker=(math.nan, 10))]).to_dict()
    with pytest.raises(ValueError):
        Project.from_dict(data)


def test_very_long_step_title_paginated(tmp_path):
    project = Project(steps=[Step(title="A lengthy step title " * 500, description="Do the action.")])
    path = export_pdf(project, tmp_path, tmp_path / "long-title.pdf")
    assert "Do the action." in "".join(page.extract_text() for page in PdfReader(path).pages)
