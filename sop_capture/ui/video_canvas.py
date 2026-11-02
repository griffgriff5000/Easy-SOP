"""Existing annotation gestures over a normalized live video frame."""
from PIL import Image
from .canvas import AnnotationCanvas,image_pixmap
from ..models import Project,Step
from ..video_timeline import render_overlays,SIZE

class VideoCanvas(AnnotationCanvas):
    def __init__(self):
        super().__init__();self.frame=Image.new('RGB',SIZE,'#172e42')
        self.project=Project();self.step=Step(marker_visible=False);self.number=1;self.tool='edit'
        self.refresh()

    def set_frame(self,image):
        self.frame=image;self.refresh()

    def refresh(self):
        if not hasattr(self,'frame'):return
        if self.selected is not None and self.selected>=len(self.step.annotations):self.select(None)
        self.original=self.frame
        from dataclasses import asdict
        overlays=[dict(start=0,end=1,annotation=asdict(a)) for a in self.step.annotations]
        self.pixmap=image_pixmap(render_overlays(self.frame,{'overlays':overlays},0));self.update()

    def mousePressEvent(self,event):
        if hasattr(self,'before_edit') and not self.before_edit():return
        super().mousePressEvent(event)

    def apply_gesture(self,start,end):
        if hasattr(self,'before_edit') and not self.before_edit():return
        super().apply_gesture(start,end)
