"""Create a portable demonstration with entirely synthetic screenshots."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw, ImageFont
from sop_capture.models import Project, Step, Annotation
from sop_capture.imaging import font_path, render_step
from sop_capture.storage import ProjectStore
from sop_capture.pdf_export import export_pdf


def main():
    root = Path(__file__).resolve().parents[1] / "demo" / "Permit Management"
    if (root / "project.json").exists():
        print(root)
        return
    store = ProjectStore(root)
    project = Project(title="Create a work permit", company="Example Engineering", reference="DEMO-SOP-001", author="SOP Capture Studio",
                      purpose="Create a work permit and confirm its details before submitting it for review.",
                      scope="Demonstration of a local SOP project using a fictional application and synthetic information.",
                      prerequisites="Access to the permit dashboard and the relevant work order. All screenshots in this example are fictional.")
    project.created = project.updated = "2026-10-26T09:00:00+00:00"
    specs = [("Open Permit Management", "Choose Permit Management from the navigation menu to view the available permits.", (133, 220)),
             ("Create a new permit", "Select New permit. Enter the work package and check the proposed location. Redact sensitive information before sharing screenshots.", (1070, 155)),
             ("Review and submit", "Check the work area, task description and required approvals. Select Submit for review when the details are correct.", (1000, 650))]
    font = ImageFont.truetype(str(font_path()), 20)
    bold = ImageFont.truetype(str(font_path(True)), 27)
    for index, (title, description, marker) in enumerate(specs):
        image = Image.new("RGB", (1280, 780), "#f2f6fa")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 1280, 60), fill="#ffffff")
        draw.text((24, 19), "EXAMPLE ENGINEERING  /  Work management", fill="#15344b", font=font)
        draw.rectangle((0, 60, 245, 780), fill="#15344b")
        for i, text in enumerate(("Dashboard", "Permit Management", "Work packages", "Reports")):
            if i == 1: draw.rounded_rectangle((10, 195, 235, 245), radius=9, fill="#27617a")
            draw.text((22, 140+i*66), text, font=font, fill="white")
        draw.text((280, 100), "Permit Management" if index == 0 else "New work permit", font=bold, fill="#15344b")
        draw.rounded_rectangle((970, 135, 1220, 182), radius=8, fill="#087f8c")
        draw.text((1010, 146), "New permit", font=font, fill="white")
        if index == 0:
            for row in range(5):
                y = 230+row*80
                draw.rounded_rectangle((280, y, 1220, y+60), radius=8, fill="white")
                draw.text((305, y+18), f"WP-{100+row}     Example work area {row+1}                      Draft", font=font, fill="#36556d")
        else:
            for row, (label, value) in enumerate((("Work package", "WP-104"), ("Location", "Example work area 5"), ("Task", "Inspect access platform"), ("Contact", "Synthetic example contact"))):
                y = 210+row*90
                draw.text((285, y), label, font=font, fill="#36556d")
                draw.rounded_rectangle((280, y+30, 1210, y+75), radius=6, fill="white", outline="#d5e0e8")
                draw.text((300, y+40), value, font=font, fill="#15344b")
            draw.rounded_rectangle((850, 625, 1190, 685), radius=8, fill="#087f8c")
            draw.text((890, 644), "Submit for review", font=font, fill="white")
        step = Step(title=title, description=description, marker=marker, button="left")
        step.image = store.add_image(image, step.id)
        if index == 1:
            step.annotations.append(Annotation(kind="redact", points=[295, 510, 650, 548]))
            step.notes = "Solid redactions remove visible pixels from the exported image. Original project images remain unredacted."
        project.steps.append(step)
        rendered = render_step(root, step, index+1, project)
        (root / "Annotated").mkdir(exist_ok=True)
        rendered.save(root / "Annotated" / f"{step.id}.png")
    store.save(project)
    export_pdf(project, root, root / "Exports" / "Create_a_work_permit.pdf")
    print(root)


if __name__ == "__main__":
    main()
