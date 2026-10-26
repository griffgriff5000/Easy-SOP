from io import BytesIO
import math
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QPainter, QPixmap, QColor, QPen
from PySide6.QtWidgets import QWidget

from ..imaging import render_step
from ..models import Annotation


def image_pixmap(image):
    buffer = BytesIO()
    image.save(buffer, "PNG")
    pixmap = QPixmap()
    pixmap.loadFromData(buffer.getvalue())
    return pixmap


class AnnotationCanvas(QWidget):
    changing = Signal()
    changed = Signal()
    selection_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(350, 240)
        self.step = self.project = self.root = None
        self.pixmap = None
        self.tool = "marker"
        self.anchor = self.pointer = None
        self.selected = None
        self.drag_hit = None
        self.setMouseTracking(True)

    def set_tool(self, tool):
        self.tool = tool
        self.anchor = self.pointer = self.drag_hit = None
        self.select(None)
        self.setCursor(Qt.CursorShape.OpenHandCursor if tool == "edit" else Qt.CursorShape.CrossCursor)

    def set_step(self, root, project, step, number):
        self.select(None)
        self.anchor = self.pointer = self.drag_hit = None
        self.root, self.project, self.step, self.number = root, project, step, number
        self.refresh()

    def refresh(self):
        if self.selected is not None and (not self.step or self.selected >= len(self.step.annotations)):
            self.select(None)
        self.pixmap = None
        if self.step and self.step.image:
            try:
                self.pixmap = image_pixmap(render_step(self.root, self.step, self.number, self.project))
            except (OSError, ValueError):
                pass
        self.update()

    def image_rect(self):
        if not self.pixmap: return QRectF()
        size = self.pixmap.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        return QRectF((self.width()-size.width())/2, (self.height()-size.height())/2, size.width(), size.height())

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
        self.update()

    @staticmethod
    def handles(annotation, points=None):
        x1, y1, x2, y2 = points or annotation.points
        if annotation.kind == "arrow": return [(x1, y1), (x2, y2)]
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
            if annotation.kind == "arrow":
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
        if handle is None:
            dx = max(-min(x1, x2), min(width-max(x1, x2), end[0]-start[0]))
            dy = max(-min(y1, y2), min(height-max(y1, y2), end[1]-start[1]))
            return [x1+dx, y1+dy, x2+dx, y2+dy]
        x, y = max(0, min(width, end[0])), max(0, min(height, end[1]))
        if annotation.kind == "arrow":
            return [x, y, x2, y2] if handle == 0 else [x1, y1, x, y]
        opposite = self.handles(annotation)[(handle+2) % 4]
        return [min(x, opposite[0]), min(y, opposite[1]), max(x, opposite[0]), max(y, opposite[1])]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#e4ebf2"))
        if self.pixmap:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawPixmap(self.image_rect(), self.pixmap, QRectF(self.pixmap.rect()))
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
            if annotation.kind == "arrow": painter.drawLine(first, last)
            else: painter.drawRect(QRectF(first, last).normalized())
            painter.setBrush(QColor("white"))
            for position in self.handles(annotation, points):
                p = self.display_point(position)
                painter.drawRect(QRectF(p.x()-5, p.y()-5, 10, 10))
        elif self.anchor is not None and self.pointer is not None:
            painter.setPen(QPen(QColor("#087f8c"), 2, Qt.PenStyle.DashLine))
            painter.drawRect(QRectF(self.anchor, self.pointer).normalized())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.image_point(event.position()) is not None:
            self.anchor = self.pointer = event.position()
            if self.tool == "edit":
                self.drag_hit = self.hit_test(self.image_point(event.position()))
                self.select(self.drag_hit[0] if self.drag_hit else None)

    def mouseMoveEvent(self, event):
        if self.anchor is not None:
            self.pointer = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
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
            if annotation.kind != "arrow" and (abs(points[2]-points[0]) < 2 or abs(points[3]-points[1]) < 2): return
            self.changing.emit()
            annotation.points = points
            self.refresh()
            self.changed.emit()
            return
        if self.tool == "arrow":
            if math.dist(start, end) < 2: return
        elif self.tool != "marker" and (abs(start[0]-end[0]) < 2 or abs(start[1]-end[1]) < 2):
            return
        self.changing.emit()
        if self.tool == "marker":
            self.step.marker = tuple(end)
            self.step.marker_visible = True
        else:
            self.step.annotations.append(Annotation(kind=self.tool, points=[*start, *end], color=self.project.marker_color))
        self.refresh()
        self.changed.emit()

    def delete_selected(self):
        if not self.step or self.selected is None: return
        self.changing.emit()
        self.step.annotations.pop(self.selected)
        self.select(None)
        self.refresh()
        self.changed.emit()
