import math
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont
import reportlab

from .storage import ProjectStore


def font_path(bold=False):
    return Path(reportlab.__file__).parent / "fonts" / ("VeraBd.ttf" if bold else "Vera.ttf")


def render_step(root, step, number, style=None):
    store = ProjectStore(root)
    if not step.image:
        raise FileNotFoundError("Step has no image")
    with Image.open(store.resolve(step.image)) as original:
        return render_image(original, step, number, style)


def callout_layout(annotation, size):
    font = ImageFont.truetype(str(font_path(True)), annotation.font_size)
    padding = 8
    limit = max(1, min(size[0]-padding*2, max(160, size[0]*.45)))
    lines = wrap_text(annotation.text or "Label", font, limit)
    line_height = round(annotation.font_size*1.3)
    lines = lines[:max(1, (size[1]-padding*2)//line_height)]
    width = min(size[0], max(font.getlength(line) for line in lines)+padding*2)
    height = min(size[1], len(lines)*line_height+padding*2)
    left = max(0, min(size[0]-width, annotation.points[2]))
    top = max(0, min(size[1]-height, annotation.points[3]))
    return (left, top, left+width, top+height), lines, font


def render_image(original, step, number, style=None):
    """One renderer for exports and non-mutating canvas previews."""
    image = original.convert("RGB").copy()
    draw = ImageDraw.Draw(image)
    for annotation in step.annotations:
        x1, y1, x2, y2 = annotation.points
        box = (max(0, min(x1, x2)), max(0, min(y1, y2)), min(image.width, max(x1, x2)), min(image.height, max(y1, y2)))
        color = ImageColor.getrgb(annotation.color)
        width = max(1, min(30, annotation.width))
        if annotation.kind == "callout":
            label, lines, font = callout_layout(annotation, image.size)
            left, top, right, bottom = label
            edge = (max(left, min(right, x1)), max(top, min(bottom, y1)))
            draw.line([edge, (x1, y1)], fill=color, width=width)
            angle = math.atan2(y1-edge[1], x1-edge[0])
            length = max(12, width*4)
            draw.polygon([(x1,y1), (x1-length*math.cos(angle-.5), y1-length*math.sin(angle-.5)), (x1-length*math.cos(angle+.5), y1-length*math.sin(angle+.5))], fill=color)
            draw.rectangle(label, fill="white", outline=color, width=width)
            for i, line in enumerate(lines):
                draw.text((left+8, top+8+i*round(annotation.font_size*1.3)), line, font=font, fill=color)
        elif annotation.kind == "circle":
            draw.ellipse(box, outline=color, width=width)
        elif annotation.kind == "highlight":
            draw.rectangle(box, outline=color, width=width)
        elif annotation.kind == "highlighter":
            overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
            ImageDraw.Draw(overlay).rectangle(box, fill=(*color[:3], round(255*annotation.opacity/100)))
            image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(image)
        elif annotation.kind == "text":
            left, top, right, bottom = [int(value) for value in box]
            if right > left and bottom > top:
                font = ImageFont.truetype(str(font_path(True)), annotation.font_size)
                layer = Image.new("RGBA", (right-left, bottom-top), (0, 0, 0, 0))
                text_draw = ImageDraw.Draw(layer)
                y = 0
                for line in wrap_text(annotation.text, font, max(1, right-left-4)):
                    text_draw.text((2, y), line, font=font, fill=color)
                    y += round(annotation.font_size*1.3)
                    if y >= bottom-top: break
                image.paste(layer, (left, top), layer)
        elif annotation.kind in {"arrow", "line"}:
            draw.line((x1, y1, x2, y2), fill=color, width=width)
            if annotation.kind == "line": continue
            angle = math.atan2(y2 - y1, x2 - x1)
            length = max(12, width * 4)
            def head(x, y, direction):
                first = (x-length*math.cos(direction-.5), y-length*math.sin(direction-.5))
                last = (x-length*math.cos(direction+.5), y-length*math.sin(direction+.5))
                if annotation.arrow_style == "open":
                    draw.line([first, (x, y), last], fill=color, width=width)
                else:
                    draw.polygon([(x, y), first, last], fill=color)
            head(x2, y2, angle)
            if annotation.arrow_style == "double": head(x1, y1, angle+math.pi)
    if step.marker is not None and step.marker_visible:
        color = getattr(style, "marker_color", "#ef4444")
        radius = getattr(style, "marker_size", 24)
        x, y = step.marker
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill="white", outline=color, width=max(3, radius//6))
        if getattr(style, "marker_numbers", True):
            font = ImageFont.truetype(str(font_path(True)), max(10, radius))
            draw.text((x, y), str(number), font=font, fill=color, anchor="mm")
    # Redactions always flatten last, including over markers and other annotations.
    for a in step.annotations:
        if a.kind not in {"redact", "blur"}:
            continue
        x1, y1, x2, y2 = a.points
        box = tuple(int(v) for v in (max(0, min(x1, x2)), max(0, min(y1, y2)), min(image.width, max(x1, x2)), min(image.height, max(y1, y2))))
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        if a.kind == "redact":
            draw.rectangle(box, fill="black")
        else:
            image.paste(image.crop(box).filter(ImageFilter.GaussianBlur(18)), box[:2])
    return image


def wrap_text(text, font, width):
    """Wrap labels to their drawn box, retaining explicit newlines."""
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for character in paragraph:
            candidate = line+character
            if line and font.getlength(candidate) > width:
                # Prefer a word boundary, but also wrap unbroken identifiers.
                split = line.rfind(" ")
                if split > 0:
                    lines.append(line[:split])
                    line = line[split+1:]+character
                else:
                    lines.append(line)
                    line = character
            else:
                line = candidate
        lines.append(line)
    return lines
