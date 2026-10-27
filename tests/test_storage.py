import json

import pytest
from PIL import Image

from sop_capture.models import Project, Step
from sop_capture.storage import ProjectStore


def test_roundtrip_reorder_and_immutable_images(tmp_path):
    store = ProjectStore(tmp_path)
    project = Project(title="Permit <workflow>")
    first, second = Step(title="First"), Step(title="Second")
    first.image = store.add_image(Image.new("RGB", (90, 50), "white"), first.id)
    second.image = store.add_image(Image.new("RGB", (50, 90), "blue"), second.id)
    project.steps = [second, first]
    store.save(project)
    loaded = store.load()
    assert [s.id for s in loaded.steps] == [second.id, first.id]
    assert Image.open(store.resolve(loaded.steps[1].image)).size == (90, 50)
    replacement = store.add_image(Image.new("RGB", (20, 20)), first.id)
    assert replacement != first.image
    assert store.resolve(first.image).exists()


def test_corrupt_json_recoverable_backup(tmp_path):
    store = ProjectStore(tmp_path)
    p = Project(title="Saved")
    store.save(p)
    p.title = "Updated"
    store.save(p)
    (tmp_path / "project.json").write_text("broken")
    with pytest.raises(ValueError, match="backup"):
        store.load()
    assert store.load(backup=True).title == "Saved"


@pytest.mark.parametrize("path", ["../outside.png", "C:/secret.png", "/secret.png", "Screenshots/../../secret.png"])
def test_rejects_unsafe_paths(tmp_path, path):
    store = ProjectStore(tmp_path)
    with pytest.raises(ValueError):
        store.resolve(path)


def test_invalid_schema_and_missing_images(tmp_path):
    store = ProjectStore(tmp_path)
    store.save(Project(steps=[Step(image="Screenshots/missing.png")]))
    assert store.load().steps[0].image == "Screenshots/missing.png"
    raw = json.loads((tmp_path / "project.json").read_text())
    raw["schema_version"] = 99
    (tmp_path / "project.json").write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="version"):
        store.load()


def test_exclusive_lock(tmp_path):
    first, second = ProjectStore(tmp_path), ProjectStore(tmp_path)
    first.acquire()
    try:
        with pytest.raises(RuntimeError, match="open"):
            second.acquire()
    finally:
        first.release()
    second.acquire()
    second.release()
