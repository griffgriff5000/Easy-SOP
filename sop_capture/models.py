from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
import uuid
import math
from PIL import ImageColor


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Annotation:
    kind: str = "highlight"
    points: list[float] = field(default_factory=list)
    color: str = "#ef4444"
    width: int = 4


@dataclass
class Step:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = "New step"
    description: str = ""
    notes: str = ""
    image: str | None = None
    timestamp: str = field(default_factory=now)
    button: str | None = None
    marker: tuple[float, float] | None = None
    marker_visible: bool = True
    annotations: list[Annotation] = field(default_factory=list)
    capture_bounds: list[int] = field(default_factory=list)
    frame_age_ms: float | None = None


@dataclass
class Project:
    schema_version: int = 1
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = "Untitled SOP"
    company: str = ""
    logo: str | None = None
    reference: str = "SOP-001"
    version: str = "1.0"
    author: str = ""
    reviewer: str = ""
    approver: str = ""
    status: str = "Draft"
    created: str = field(default_factory=now)
    updated: str = field(default_factory=now)
    purpose: str = ""
    scope: str = ""
    prerequisites: str = ""
    revision_history: str = "1.0 — Initial issue"
    orientation: str = "portrait"
    marker_color: str = "#ef4444"
    marker_size: int = 24
    marker_numbers: bool = True
    steps: list[Step] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise ValueError("Unsupported project schema version")
        try:
            project = cls(**{k: v for k, v in data.items() if k in {f.name for f in fields(cls)} and k != "steps"})
            if not isinstance(data.get("steps", []), list):
                raise ValueError("Steps must be a list")
            for row in data.get("steps", []):
                step = Step(**{k: v for k, v in row.items() if k in {f.name for f in fields(Step)} and k != "annotations"})
                if not isinstance(step.id, str) or not step.id or any(c not in "0123456789abcdef-" for c in step.id):
                    raise ValueError("Invalid step identifier")
                if step.marker is not None:
                    if len(step.marker) != 2 or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in step.marker):
                        raise ValueError("Invalid marker")
                    step.marker = tuple(step.marker)
                step.annotations = [Annotation(**a) for a in row.get("annotations", [])]
                for a in step.annotations:
                    if a.kind not in {"arrow", "circle", "highlight", "redact", "blur"} or len(a.points) != 4:
                        raise ValueError("Invalid annotation")
                    if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in a.points):
                        raise ValueError("Invalid annotation coordinates")
                    ImageColor.getrgb(a.color)
                    if not isinstance(a.width, int) or not 1 <= a.width <= 30:
                        raise ValueError("Invalid annotation width")
                for name in ("title", "description", "notes", "timestamp"):
                    if not isinstance(getattr(step, name), str):
                        raise ValueError(f"Invalid step {name}")
                if step.image is not None and not isinstance(step.image, str):
                    raise ValueError("Invalid image reference")
                if not isinstance(step.marker_visible, bool):
                    raise ValueError("Invalid marker visibility")
                project.steps.append(step)
            if len({s.id for s in project.steps}) != len(project.steps):
                raise ValueError("Duplicate step identifiers")
            for name in ("title", "company", "reference", "version", "author", "reviewer", "approver", "created", "updated", "status", "purpose", "scope", "prerequisites", "revision_history"):
                if not isinstance(getattr(project, name), str):
                    raise ValueError(f"Invalid {name}")
            if not isinstance(project.marker_size, int) or not 5 <= project.marker_size <= 150:
                raise ValueError("Invalid marker size")
            ImageColor.getrgb(project.marker_color)
            if project.orientation not in {"portrait", "landscape"} or project.status not in {"Draft", "Approved"}:
                raise ValueError("Invalid document orientation or status")
            if not isinstance(project.marker_numbers, bool):
                raise ValueError("Invalid marker numbering")
            return project
        except (TypeError, KeyError, AttributeError) as exc:
            raise ValueError(f"Invalid project data: {exc}") from exc
