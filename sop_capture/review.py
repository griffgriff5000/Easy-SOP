"""Non-mutating checks for incomplete SOP drafts."""
from dataclasses import dataclass
import re
from PIL import Image
from .storage import ProjectStore


@dataclass(frozen=True)
class ReviewIssue:
    field: str
    message: str
    step_id: str | None = None


def review_project(project, root):
    issues = []
    for field in ('title', 'reference', 'version', 'author', 'company', 'purpose', 'scope'):
        value = getattr(project, field)
        if field == 'company':
            value = value or project.template.get('settings', {}).get('company', '')
        if not value.strip() or (field == 'title' and value == 'Untitled SOP'):
            issues.append(ReviewIssue(field, f'Document: add {field}.'))
    if not project.steps:
        issues.append(ReviewIssue('steps', 'Add at least one procedural step.'))
    for field, relative in (('logo', project.template.get('logo') or project.logo), ('template', project.template.get('docx'))):
        if not relative:
            continue
        try:
            asset = ProjectStore(root).resolve(relative)
            if not asset.is_file():
                raise ValueError('Missing asset')
            if field == 'logo':
                with Image.open(asset) as image:
                    image.verify()
        except (OSError, ValueError):
            issues.append(ReviewIssue(field, f'Document: replace the unavailable {field} asset.'))
    for number, step in enumerate(project.steps, 1):
        prefix = f'Step {number}: '
        if not step.title.strip() or step.title == 'New step' or re.fullmatch(r'Step\s+\d+', step.title):
            issues.append(ReviewIssue('title', prefix+'give this step a descriptive title.', step.id))
        if not step.description.strip():
            issues.append(ReviewIssue('description', prefix+'add instructions.', step.id))
        if not step.image:
            issues.append(ReviewIssue('image', prefix+'no screenshot attached (may be intentional).', step.id))
        else:
            try:
                with Image.open(ProjectStore(root).resolve(step.image)) as image:
                    image.verify()
            except (OSError, ValueError):
                issues.append(ReviewIssue('image', prefix+'replace the unavailable screenshot.', step.id))
    for field in ('reviewer', 'approver'):
        if project.status == 'Approved' and not getattr(project, field).strip():
            issues.append(ReviewIssue(field, f'Approved document: add {field}.'))
    return issues
