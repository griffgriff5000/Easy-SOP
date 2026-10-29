"""Local named templates and portable per-project snapshots."""
from copy import deepcopy
import json
import logging
from pathlib import Path
import uuid

from PIL import Image, ImageColor
from .storage import atomic_bytes, ProjectStore

DEFAULT_APPEARANCE = {
    "font": "Vera", "body_size": 9, "heading_size": 16, "title_size": 29,
    "heading_color": "#15344b", "text_color": "#183247", "margin_mm": 20,
    "image_width_percent": 100, "page_per_step": False, "cover": True,
    "header": "", "footer": "SOP Capture Studio", "company": "",
    "orientation": "project", "heading_style": "Heading 2", "body_style": "Normal", "caption_style": "Caption",
    "title_style": "Title",
}


def appearance(values=None):
    if not isinstance(values or {}, dict): raise ValueError("Invalid template appearance")
    result = DEFAULT_APPEARANCE | (values or {})
    for key, low, high in (("body_size", 7, 18), ("heading_size", 10, 30), ("title_size", 18, 44), ("margin_mm", 10, 35), ("image_width_percent", 30, 100)):
        if not isinstance(result[key], (int, float)) or not low <= result[key] <= high:
            raise ValueError(f"Invalid template {key}")
    if result["font"] not in {"Vera", "Helvetica", "Times-Roman", "Courier"}: raise ValueError("Unsupported template font")
    for key in ("heading_color", "text_color"):
        rgb = ImageColor.getrgb(result[key])
        result[key] = "#%02x%02x%02x" % rgb[:3]
    for key in ("cover", "page_per_step"):
        if not isinstance(result[key], bool): raise ValueError(f"Invalid template {key}")
    for key in ("header", "footer", "company", "heading_style", "body_style", "caption_style", "title_style"):
        if not isinstance(result[key], str) or len(result[key]) > 500: raise ValueError(f"Invalid template {key}")
    if result["orientation"] not in {"project", "portrait", "landscape"}: raise ValueError("Invalid template orientation")
    return result


def validate_snapshot(value):
    if not isinstance(value, dict): raise ValueError("Invalid project template")
    if not value: return
    if value.get("kind") not in {"standard", "custom", "docx"} or not isinstance(value.get("name"), str):
        raise ValueError("Invalid project template")
    appearance(value.get("settings", {}))
    if not isinstance(value.get('prepared',False),bool):raise ValueError('Invalid template preparation setting')
    if value["kind"] == "docx" and not value.get("docx"): raise ValueError("Word template file is missing")


def standard_profile():
    return {"id": "standard", "name": "Standard SOP", "kind": "standard", "version": 1, "settings": appearance(), "logo": None, "docx": None}


class TemplateLibrary:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _directory(self, identity):
        if not isinstance(identity, str) or len(identity) != 32 or any(c not in "0123456789abcdef" for c in identity):
            raise ValueError("Invalid template identifier")
        return self.root / identity

    def load(self, identity):
        if identity == "standard": return standard_profile()
        directory = self._directory(identity)
        profile = json.loads((directory / "profile.json").read_text(encoding="utf-8"))
        validate_snapshot(profile)
        if profile.get("id") != identity: raise ValueError("Invalid template identity")
        for key in ("logo", "docx"):
            if profile.get(key): ProjectStore(directory).resolve(profile[key])
        return profile

    def asset(self, profile, key):
        return ProjectStore(self._directory(profile["id"])).resolve(profile[key]) if profile.get(key) else None

    def list(self):
        profiles = []
        for path in self.root.glob("*/profile.json"):
            try: profiles.append(self.load(path.parent.name))
            except (ValueError, OSError, TypeError): logging.getLogger(__name__).warning("An invalid template profile was skipped")
        return [standard_profile()] + sorted(profiles, key=lambda p: p["name"].casefold())

    def save(self, name, settings, *, identity=None, source_docx=None, logo=None, prepare_word=False, prepared=False):
        name = name.strip()
        if not name or len(name) > 120: raise ValueError("Enter a template name of 1–120 characters")
        if any(p["name"].casefold() == name.casefold() and p["id"] != identity for p in self.list()):
            raise ValueError("A template with that name already exists")
        old = self.load(identity) if identity else None
        identity = identity or uuid.uuid4().hex
        directory = self._directory(identity)
        prepared_payload=None
        if source_docx:
            from .word_export import inspect_docx
            inspect_docx(source_docx)
            if prepare_word:
                from .word_template import prepare_template
                prepared_payload,learned=prepare_template(source_docx)
                settings=learned | settings
        settings = appearance(settings)
        assets = {}
        for key, source in (("docx", source_docx), ("logo", logo)):
            if source:
                suffix = ".docx" if key == "docx" else ".png"
                filename = uuid.uuid4().hex + suffix
                if key == "logo":
                    from io import BytesIO
                    data = BytesIO()
                    with Image.open(source) as image: image.convert("RGBA").save(data, "PNG")
                    payload = data.getvalue()
                else: payload = prepared_payload if prepared_payload is not None else Path(source).read_bytes()
                atomic_bytes(directory / filename, payload)
                assets[key] = filename
            else: assets[key] = None
        profile = {"id": identity, "name": name, "kind": "docx" if source_docx else "custom",
                   "version": old["version"]+1 if old else 1, "settings": settings, **assets}
        if source_docx and (prepare_word or prepared or (old and old.get('prepared'))):
            profile['prepared']=True
            if prepare_word:
                from .word_template import has_structure
                profile['structured']=has_structure(prepared_payload);profile['preparation_version']=2
            elif old:
                for key in ('structured','preparation_version'):
                    if key in old:profile[key]=old[key]
            elif prepared:
                from .word_template import has_structure
                profile['structured']=has_structure(Path(source_docx).read_bytes());profile['preparation_version']=2
        atomic_bytes(directory / "profile.json", json.dumps(profile, ensure_ascii=False, indent=2).encode("utf-8"))
        return profile

    def delete(self, identity):
        # Remove only the catalogue entry. Asset retention avoids deleting files
        # another open editor may still be using; project snapshots are separate.
        (self._directory(identity) / "profile.json").unlink()

    def snapshot(self, identity, project_root):
        profile = deepcopy(self.load(identity))
        if identity == "standard": return {}
        store = ProjectStore(project_root)
        folder = f"Templates/{uuid.uuid4().hex}"
        for key in ("docx", "logo"):
            source = self.asset(profile, key)
            if source:
                if not source.is_file(): raise ValueError(f"Template {key} file is missing; import it again")
                relative = f"{folder}/{key}{source.suffix}"
                atomic_bytes(store.resolve(relative), source.read_bytes())
                profile[key] = relative
        return profile
