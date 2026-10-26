from io import BytesIO
import math
from PySide6.QtCore import Qt, Signal, QRectF
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

    def __init__(self):
        super().__init__()
        self.setMinimumSize(350, 240)
        self.step = self.project = self.root = None
        self.pixmap = None
        self.tool = "marker"
        self.anchor = self.pointer = None
        self.setMouseTracking(True)

    def set_tool(self, tool):
        self.tool = tool
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_step(self, root, project, step, number):
        self.root, self.project, self.step, self.number = root, project, step, number
        self.refresh()

    def refresh(self):
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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#e4ebf2"))
        if self.pixmap:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawPixmap(self.image_rect(), self.pixmap, QRectF(self.pixmap.rect()))
        else:
            painter.setPen(QColor("#597084"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Select a step with a screenshot\nor attach an image to a manual step")
        if self.anchor is not None and self.pointer is not None:
            painter.setPen(QPen(QColor("#087f8c"), 2, Qt.PenStyle.DashLine))
            painter.drawRect(QRectF(self.anchor, self.pointer).normalized())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.image_point(event.position()) is not None:
            self.anchor = self.pointer = event.position()

    def mouseMoveEvent(self, event):
        if self.anchor is not None:
            self.pointer = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.anchor is not None:
            start, end = self.image_point(self.anchor), self.image_point(event.position())
            self.anchor = self.pointer = None
            if start is not None and end is not None:
                self.apply_gesture(start, end)
            self.update()

    def apply_gesture(self, start, end):
        if not self.step: return
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
