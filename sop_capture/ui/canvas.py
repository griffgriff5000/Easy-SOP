import math
from dataclasses import replace
from copy import deepcopy
from PIL import Image
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QPainter, QPixmap, QColor, QPen, QImage
from PySide6.QtWidgets import QWidget

from ..imaging import render_image, callout_layout
from ..storage import ProjectStore
from ..models import Annotation


def image_pixmap(image):
    rgba = image.convert("RGBA")
    return QPixmap.fromImage(QImage(rgba.tobytes(), rgba.width, rgba.height, rgba.width*4, QImage.Format.Format_RGBA8888).copy())


class AnnotationCanvas(QWidget):
    changing = Signal()
    changed = Signal()
    selection_changed = Signal(bool)
    style_changed = Signal()

    def __init__(self):
        super().__init__()
        self.setMinimumSize(350, 240)
        self.step = self.project = self.root = None
        self.pixmap = None
        self.original = None
        self.tool = "marker"
        self.zoom_factor = 1.0
        self.pan = QPointF()
        self.pan_anchor = None
        self.anchor = self.pointer = None
        self.selected = None
        self.drag_hit = None
        self.design_template = None
        self.draw_color = "#ef4444"
        self.draw_width = 4
        self.draw_font_size = 24
        self.draw_opacity = 30
        self.draw_text = "Text label"
        self.draw_arrow_style = "solid"
        self.draw_zoom = 2.0
        self.style_project_id = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_tool(self, tool):
        self.tool = tool
        self.anchor = self.pointer = self.drag_hit = None
        self.select(None)
        self.setCursor(Qt.CursorShape.OpenHandCursor if tool == "edit" else Qt.CursorShape.CrossCursor)

    def set_step(self, root, project, step, number):
        self.select(None)
        self.anchor = self.pointer = self.drag_hit = None
        if self.step is not step:self.pan = QPointF()
        self.root, self.project, self.step, self.number = root, project, step, number
        if project and self.style_project_id != project.id:
            self.draw_color = project.marker_color
            self.style_project_id = project.id
            self.style_changed.emit()
        self.refresh()

    def refresh(self):
        if self.selected is not None and (not self.step or self.selected >= len(self.step.annotations)):
            self.select(None)
        self.pixmap = None
        self.original = None
        if self.step and self.step.image:
            try:
                with Image.open(ProjectStore(self.root).resolve(self.step.image)) as image:
                    self.original = image.convert("RGB")
                self.pixmap = image_pixmap(render_image(self.original, self.step, self.number, self.project))
            except (OSError, ValueError):
                pass
        self.update()

    def image_rect(self):
        if not self.pixmap: return QRectF()
        size = self.pixmap.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        width,height = size.width()*self.zoom_factor,size.height()*self.zoom_factor
        return QRectF((self.width()-width)/2+self.pan.x(), (self.height()-height)/2+self.pan.y(), width,height)

    def set_zoom(self, factor):
        self.cancel_gesture()
        self.zoom_factor = max(1,min(4,float(factor or 1)))
        if self.zoom_factor == 1:self.pan = QPointF()
        self.update()

    def image_point(self, point):
        rect = self.image_rect()
        if not self.pixmap or not rect.contains(point): return None
        return ((point.x()-rect.x())/rect.width()*self.pixmap.width(), (point.y()-rect.y())/rect.height()*self.pixmap.height())

    def clamped_point(self, point):
        rect = self.image_rect()
        if not self.pixmap or rect.isEmpty(): return None
        return (max(0, min(self.pixmap.width()-1, (point.x()-rect.x())/rect.width()*self.pixmap.width())),
                max(0, min(self.pixmap.height()-1, (point.y()-rect.y())/rect.height()*self.pixmap.height())))

    def display_point(self, point):
        rect = self.image_rect()
        return QPointF(rect.x()+point[0]*rect.width()/self.pixmap.width(), rect.y()+point[1]*rect.height()/self.pixmap.height())

    def select(self, index):
        self.selected = index
        self.selection_changed.emit(index is not None)
        self.style_changed.emit()
        self.update()

    def annotation_style(self):
        if self.selected is not None and self.step:
            a = self.step.annotations[self.selected]
            return {"color": a.color, "width": a.width, "font_size": a.font_size, "opacity": a.opacity, "text": a.text, "arrow_style": a.arrow_style,"zoom":a.zoom}
        return {"color": self.draw_color, "width": self.draw_width, "font_size": self.draw_font_size, "opacity": self.draw_opacity, "text": self.draw_text, "arrow_style": self.draw_arrow_style,"zoom":self.draw_zoom}

    def set_annotation_style(self, **values):
        style = self.annotation_style() | values
        # Validate style through the same schema used by project persistence.
        from ..models import Project, Step
        Project.from_dict(Project(steps=[Step(annotations=[Annotation(kind='magnifier',points=[0, 0, 10, 10], **style)])]).to_dict())
        if self.selected is not None and self.step:
            annotation = self.step.annotations[self.selected]
            if any(getattr(annotation, key) != value for key, value in values.items()):
                self.changing.emit()
                for key, value in values.items(): setattr(annotation, key, value)
                self.refresh()
                self.changed.emit()
        for key, value in values.items(): setattr(self, "draw_"+key, value)
        self.style_changed.emit()
        self.update()

    def new_annotation(self, start, end):
        if self.tool == "design":
            return Annotation(kind="design", points=[*start,*end], design=deepcopy(self.design_template))
        return Annotation(kind=self.tool, points=[*start, *end], color=self.draw_color, width=self.draw_width,
                          text=self.draw_text if self.tool in {"text", "callout"} else "", font_size=self.draw_font_size, opacity=self.draw_opacity, arrow_style=self.draw_arrow_style,zoom=self.draw_zoom)

    def preview_image(self):
        if self.original is None or self.step is None: return None
        preview = replace(self.step, annotations=list(self.step.annotations))
        if self.anchor is not None and self.pointer is not None:
            start, end = self.clamped_point(self.anchor), self.clamped_point(self.pointer)
            if self.tool == "edit":
                if self.drag_hit is not None:
                    index, handle = self.drag_hit
                    annotation = self.step.annotations[index]
                    preview.annotations[index] = replace(annotation, points=self.edit_points(annotation, handle, start, end))
            elif self.tool == "marker":
                preview.marker, preview.marker_visible = end, True
            elif self.valid_gesture(start, end):
                preview.annotations.append(self.new_annotation(start, end))
        return render_image(self.original, preview, self.number, self.project)

    def cancel_gesture(self):
        self.anchor = self.pointer = self.drag_hit = None
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_gesture()
            event.accept()
        else:
            super().keyPressEvent(event)

    def valid_gesture(self, start, end):
        if self.tool == "design" and not self.design_template: return False
        if self.tool in {"arrow", "line", "callout"}: return math.dist(start, end) >= 2
        return self.tool == "marker" or (abs(start[0]-end[0]) >= 2 and abs(start[1]-end[1]) >= 2)

    @staticmethod
    def handles(annotation, points=None):
        x1, y1, x2, y2 = points or annotation.points
        if annotation.kind in {"arrow", "line", "callout"}: return [(x1, y1), (x2, y2)]
        return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]

    def hit_test(self, point):
        if not self.step or not self.pixmap: return None
        rect = self.image_rect()
        tolerance = 8*self.pixmap.width()/max(1, rect.width())
        x, y = point
        for index in range(len(self.step.annotations)-1, -1, -1):
            annotation = self.step.annotations[index]
            for handle, position in enumerate(self.handles(annotation)):
                if math.dist(point, position) <= tolerance:
                    return index, handle
            x1, y1, x2, y2 = annotation.points
            if annotation.kind == "callout":
                box, _, _ = callout_layout(annotation, (self.pixmap.width(), self.pixmap.height()))
                if box[0] <= x <= box[2] and box[1] <= y <= box[3]: return index, None
                x2 = max(box[0], min(box[2], x1))
                y2 = max(box[1], min(box[3], y1))
            if annotation.kind in {"arrow", "line", "callout"}:
                dx, dy = x2-x1, y2-y1
                length_squared = dx*dx+dy*dy
                t = max(0, min(1, ((x-x1)*dx+(y-y1)*dy)/length_squared)) if length_squared else 0
                inside = math.dist(point, (x1+t*dx, y1+t*dy)) <= tolerance
            elif annotation.kind == "circle":
                rx, ry = abs(x2-x1)/2, abs(y2-y1)/2
                inside = rx > 0 and ry > 0 and ((x-(x1+x2)/2)/(rx+tolerance))**2+((y-(y1+y2)/2)/(ry+tolerance))**2 <= 1
            else:
                inside = min(x1, x2)-tolerance <= x <= max(x1, x2)+tolerance and min(y1, y2)-tolerance <= y <= max(y1, y2)+tolerance
            if inside: return index, None
        return None

    def edit_points(self, annotation, handle, start, end):
        x1, y1, x2, y2 = annotation.points
        width, height = self.pixmap.width()-1, self.pixmap.height()-1
        if annotation.kind == "callout" and handle is None:
            box, _, _ = callout_layout(annotation, (self.pixmap.width(), self.pixmap.height()))
            x2, y2 = box[:2]
            return [x1, y1, max(0, min(width, x2+end[0]-start[0])), max(0, min(height, y2+end[1]-start[1]))]
        if handle is None:
            dx = max(-min(x1, x2), min(width-max(x1, x2), end[0]-start[0]))
            dy = max(-min(y1, y2), min(height-max(y1, y2), end[1]-start[1]))
            return [x1+dx, y1+dy, x2+dx, y2+dy]
        x, y = max(0, min(width, end[0])), max(0, min(height, end[1]))
        if annotation.kind in {"arrow", "line", "callout"}:
            return [x, y, x2, y2] if handle == 0 else [x1, y1, x, y]
        opposite = self.handles(annotation)[(handle+2) % 4]
        return [min(x, opposite[0]), min(y, opposite[1]), max(x, opposite[0]), max(y, opposite[1])]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#e4ebf2"))
        if self.pixmap:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            pixmap = image_pixmap(self.preview_image()) if self.anchor is not None and self.pointer is not None else self.pixmap
            painter.drawPixmap(self.image_rect(), pixmap, QRectF(pixmap.rect()))
        else:
            painter.setPen(QColor("#597084"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Select a step with a screenshot\nor attach an image to a manual step")
        if self.tool == "edit" and self.selected is not None and self.pixmap:
            annotation = self.step.annotations[self.selected]
            points = annotation.points
            if self.drag_hit is not None and self.anchor is not None and self.pointer is not None:
                points = self.edit_points(annotation, self.drag_hit[1], self.clamped_point(self.anchor), self.clamped_point(self.pointer))
            first, last = self.display_point(points[:2]), self.display_point(points[2:])
            painter.setPen(QPen(QColor("#087f8c"), 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            if annotation.kind in {"arrow", "line", "callout"}: painter.drawLine(first, last)
            else: painter.drawRect(QRectF(first, last).normalized())
            painter.setBrush(QColor("white"))
            for position in self.handles(annotation, points):
                p = self.display_point(position)
                painter.drawRect(QRectF(p.x()-5, p.y()-5, 10, 10))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            if self.zoom_factor > 1:self.pan_anchor = event.position()
            return
        if event.button() == Qt.MouseButton.LeftButton and self.image_point(event.position()) is not None:
            self.setFocus()
            self.anchor = self.pointer = event.position()
            if self.tool == "edit":
                self.drag_hit = self.hit_test(self.image_point(event.position()))
                self.select(self.drag_hit[0] if self.drag_hit else None)

    def mouseMoveEvent(self, event):
        if self.pan_anchor is not None:
            self.pan += event.position()-self.pan_anchor;self.pan_anchor=event.position();self.update();return
        if self.anchor is not None:
            self.pointer = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.pan_anchor=None;return
        if self.anchor is not None:
            start, end = self.image_point(self.anchor), self.clamped_point(event.position())
            if start is not None and end is not None:
                self.apply_gesture(start, end)
            self.anchor = self.pointer = self.drag_hit = None
            self.update()

    def apply_gesture(self, start, end):
        if not self.step: return
        if self.tool == "edit":
            hit = self.drag_hit or self.hit_test(start)
            self.select(hit[0] if hit else None)
            if hit is None: return
            annotation = self.step.annotations[hit[0]]
            points = self.edit_points(annotation, hit[1], start, end)
            if math.dist(start, end) < .5 or points == annotation.points: return
            if annotation.kind not in {"arrow", "line", "callout"} and (abs(points[2]-points[0]) < 2 or abs(points[3]-points[1]) < 2): return
            self.changing.emit()
            annotation.points = points
            self.refresh()
            self.changed.emit()
            return
        if not self.valid_gesture(start, end): return
        self.changing.emit()
        if self.tool == "marker":
            self.step.marker = tuple(end)
            self.step.marker_visible = True
        else:
            self.step.annotations.append(self.new_annotation(start, end))
        self.refresh()
        self.changed.emit()

    def delete_selected(self):
        if not self.step or self.selected is None: return
        self.changing.emit()
        self.step.annotations.pop(self.selected)
        self.select(None)
        self.refresh()
        self.changed.emit()
