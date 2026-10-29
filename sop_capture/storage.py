import json
import os
from pathlib import Path, PureWindowsPath
import tempfile
import uuid

from PIL import Image

from .models import Project, now


def atomic_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".writing-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


class ProjectStore:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.lock_token = None

    def resolve(self, relative):
        if not isinstance(relative, str) or not relative or PureWindowsPath(relative).is_absolute() or PureWindowsPath(relative).drive:
            raise ValueError("Unsafe project path")
        result = (self.root / relative).resolve()
        if not result.is_relative_to(self.root) or Path(relative).is_absolute():
            raise ValueError("Unsafe project path")
        return result

    def prepare(self):
        for folder in ("Screenshots", "Annotated", "Exports"):
            (self.root / folder).mkdir(parents=True, exist_ok=True)

    def acquire(self, force=False):
        self.prepare()
        path = self.root / ".project.lock"
        if force:
            path.unlink(missing_ok=True)
        token = uuid.uuid4().hex
        try:
            with path.open("x", encoding="utf-8") as stream:
                json.dump({"pid": os.getpid(), "token": token, "created": now()}, stream)
        except FileExistsError as exc:
            raise RuntimeError("Project is already open, or has a stale lock after a crash.") from exc
        self.lock_token = token

    def release(self):
        if self.lock_token:
            path = self.root / ".project.lock"
            try:
                if json.loads(path.read_text()).get("token") == self.lock_token:
                    path.unlink()
            except (OSError, ValueError):
                pass
            self.lock_token = None

    def add_image(self, image: Image.Image, step_id, compression=6):
        self.prepare()
        import io
        data = io.BytesIO()
        image.convert("RGB").save(data, "PNG", compress_level=compression)
        relative = f"Screenshots/{uuid.uuid4().hex}.png"
        atomic_bytes(self.resolve(relative), data.getvalue())
        return relative

    def save(self, project):
        self.prepare()
        if any(a.kind=='magnifier' for step in project.steps for a in step.annotations):
            project.schema_version=max(project.schema_version,8)
        if project.document_file:
            self.resolve(project.document_file)
            project.schema_version = max(project.schema_version, 7)
        if any(s.section or any(a.kind == "callout" for a in s.annotations) for s in project.steps):
            project.schema_version = max(project.schema_version, 3)
        if any(a.kind == "design" for step in project.steps for a in step.annotations):
            project.schema_version = max(project.schema_version, 4)
        if project.template_text_edits:
            project.schema_version = max(project.schema_version, 6)
        if project.company_information:
            project.schema_version = max(project.schema_version, 5)
        if project.template:
            project.schema_version = max(project.schema_version, 2)  # Older applications must not silently discard the selected layout.
        # Validate before replacing the last usable project.
        Project.from_dict(project.to_dict())
        for step in project.steps:
            if step.image:
                self.resolve(step.image)
        if project.logo:
            self.resolve(project.logo)
        for key in ("logo", "docx"):
            if project.template.get(key): self.resolve(project.template[key])
        project.updated = now()
        path = self.root / "project.json"
        if path.exists():
            try:
                Project.from_dict(json.loads(path.read_text(encoding="utf-8")))
                atomic_bytes(self.root / "project.backup.json", path.read_bytes())
            except (ValueError, OSError):
                pass
        atomic_bytes(path, json.dumps(project.to_dict(), indent=2, ensure_ascii=False).encode("utf-8"))

    def load(self, backup=False):
        path = self.root / ("project.backup.json" if backup else "project.json")
        try:
            project = Project.from_dict(json.loads(path.read_text(encoding="utf-8")))
            if project.document_file:
                self.resolve(project.document_file)
            for step in project.steps:
                if step.image:
                    self.resolve(step.image)
            if project.logo:
                self.resolve(project.logo)
            for key in ("logo", "docx"):
                if project.template.get(key): self.resolve(project.template[key])
            return project
        except (OSError, ValueError) as exc:
            raise ValueError(f"Cannot open project: {exc}. A project.backup.json may be recoverable.") from exc
