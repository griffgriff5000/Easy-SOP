"""Bounded UI-only image caches. Export rendering always reads preserved originals."""
from collections import OrderedDict
from dataclasses import asdict
import json
from hashlib import sha256
from pathlib import Path
from PIL import Image
from ..imaging import render_image
from ..storage import ProjectStore


class PreviewCache:
    def __init__(self,max_bytes=64*1024*1024,max_thumbnails=256):
        self.max_bytes=max_bytes;self.max_thumbnails=max_thumbnails;self.images=OrderedDict();self.thumbnails=OrderedDict();self.bytes=0;self.pixmaps=OrderedDict();self.pixmap_bytes=0

    @staticmethod
    def identity(path):
        path=Path(path).resolve();stat=path.stat();return (str(path),stat.st_mtime_ns,stat.st_size)

    def image(self,path):
        key=self.identity(path)
        if key in self.images:self.images.move_to_end(key);return self.images[key]
        with Image.open(path) as source:image=source.convert('RGB')
        size=image.width*image.height*3
        for old in list(self.images):
            if old[0]==key[0]:previous=self.images.pop(old);self.bytes-=previous.width*previous.height*3
        while self.images and self.bytes+size>self.max_bytes:
            _,previous=self.images.popitem(last=False);self.bytes-=previous.width*previous.height*3
        if size<=self.max_bytes:self.images[key]=image;self.bytes+=size
        return image

    def render_key(self,root,step,number,project):
        path=ProjectStore(root).resolve(step.image);marker=step.marker if step.marker_visible else None
        style=(project.marker_color,project.marker_size,project.marker_numbers)
        annotations=sha256(json.dumps([asdict(a) for a in step.annotations],sort_keys=True).encode()).digest()
        return path,(self.identity(path),annotations,tuple(marker) if marker else None,number if marker and project.marker_numbers else None,style)

    def pixmap(self,root,step,number,project):
        from .canvas import image_pixmap
        path,key=self.render_key(root,step,number,project)
        if key in self.pixmaps:self.pixmaps.move_to_end(key);return self.pixmaps[key]
        pixmap=image_pixmap(render_image(self.image(path),step,number,project));size=pixmap.width()*pixmap.height()*4;budget=32*1024*1024
        while self.pixmaps and self.pixmap_bytes+size>budget:
            _,old=self.pixmaps.popitem(last=False);self.pixmap_bytes-=old.width()*old.height()*4
        if size<=budget:self.pixmaps[key]=pixmap;self.pixmap_bytes+=size
        return pixmap

    def thumbnail(self,root,step,number,project):
        path,key=self.render_key(root,step,number,project)
        if key in self.thumbnails:self.thumbnails.move_to_end(key);return self.thumbnails[key]
        image=render_image(self.image(path),step,number,project);image.thumbnail((130,72));self.thumbnails[key]=image
        while len(self.thumbnails)>self.max_thumbnails:self.thumbnails.popitem(last=False)
        return image
