"""Portable, bounded layered annotation documents and their shared renderer."""
import base64
import json
import math
import re
import uuid
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from functools import lru_cache
import xml.etree.ElementTree as ET
from PIL import Image, ImageColor, ImageDraw, ImageFont

MAX_PACK = 20 * 1024 * 1024
KINDS = {'rect','ellipse','triangle','diamond','arrow','line','text','path','image'}


def new_design(width=800, height=500):
    return {'version':1, 'size':[width,height], 'layers':[]}


def new_layer(kind, **values):
    layer = dict(id=uuid.uuid4().hex, name=kind.title(), kind=kind, x=80, y=80, w=200, h=100,
                 rotation=0, opacity=100, stroke='#ef4444', fill=None, width=4,
                 text='Label', font_size=32, font='sans', bold=False, italic=False,
                 visible=True, locked=False, group='', points=[], image='', arrow_style='solid')
    layer.update(values)
    return layer


def finite(value, low, high):
    return isinstance(value, (int,float)) and not isinstance(value,bool) and math.isfinite(value) and low <= value <= high


@lru_cache(maxsize=8)
def decode_artwork(encoded):
    if not isinstance(encoded,str) or not encoded or len(encoded)>12*1024*1024:
        raise ValueError('Invalid embedded artwork.')
    try:
        raw=base64.b64decode(encoded,validate=True)
        with Image.open(BytesIO(raw)) as source:
            if source.format!='PNG' or max(source.size)>4096 or source.width*source.height>8_000_000:
                raise ValueError('Artwork must be PNG, up to 4096 pixels per side and 8 million pixels.')
            return source.convert('RGBA')
    except (OSError,ValueError,Image.DecompressionBombError) as exc:
        raise ValueError('Invalid embedded PNG artwork.') from exc


def validate_design(design):
    if not isinstance(design,dict) or design.get('version')!=1 or set(design)-{'version','size','layers'}:
        raise ValueError('Unsupported annotation design.')
    size=design.get('size');layers=design.get('layers')
    if not isinstance(size,list) or len(size)!=2 or not all(isinstance(v,int) and not isinstance(v,bool) and 16<=v<=2048 for v in size):
        raise ValueError('Canvas dimensions must be between 16 and 2048 pixels.')
    if not isinstance(layers,list) or len(layers)>100:
        raise ValueError('A design supports up to 100 layers.')
    identities=set();total=0
    allowed=set(new_layer('rect'))
    for layer in layers:
        if not isinstance(layer,dict) or set(layer)!=allowed or layer.get('kind') not in KINDS:
            raise ValueError('Invalid annotation layer.')
        identity=layer['id']
        if not isinstance(identity,str) or not identity or len(identity)>80 or identity in identities:
            raise ValueError('Layers require unique identifiers.')
        identities.add(identity)
        for key in ('x','y'):
            if not finite(layer[key],-4096,4096):raise ValueError('Invalid layer position.')
        for key in ('w','h'):
            if not finite(layer[key],1,2048):raise ValueError('Layer size must be 1-2048 pixels.')
        for key,lo,hi in [('rotation',-360,360),('opacity',0,100),('width',0,30),('font_size',8,144)]:
            if not finite(layer[key],lo,hi):raise ValueError('Invalid layer '+key)
        for key in ('visible','locked','bold','italic'):
            if not isinstance(layer[key],bool):raise ValueError('Invalid layer '+key)
        for key,limit in [('name',120),('text',5000),('group',80)]:
            if not isinstance(layer[key],str) or len(layer[key])>limit:raise ValueError('Invalid layer '+key)
        if layer['arrow_style'] not in {'solid','open','double'}:raise ValueError('Invalid arrow style.')
        if layer['font'] not in {'sans','serif','mono','vera'}:raise ValueError('Invalid font preset.')
        for key in ('stroke','fill'):
            if key=='fill' and layer[key] is None:continue
            if not isinstance(layer[key],str):raise ValueError('Invalid colour.')
            try:ImageColor.getrgb(layer[key])
            except ValueError as exc:raise ValueError('Invalid colour.') from exc
        points=layer['points']
        if not isinstance(points,list) or len(points)>2000 or any(not isinstance(p,list) or len(p)!=2 or not all(finite(v,0,1) for v in p) for p in points):
            raise ValueError('Invalid freehand/line coordinates.')
        if layer['kind']=='path' and len(points)<2:raise ValueError('Freehand needs at least two points.')
        if layer['kind'] in {'line','arrow'} and points and len(points)!=2:raise ValueError('Line needs two points.')
        if layer['kind']=='image':
            total+=len(layer['image'])
            if total>16*1024*1024:raise ValueError('Embedded artwork exceeds 16 MB.')
            decode_artwork(layer['image'])
        elif layer['image']!='':raise ValueError('Only image layers contain artwork.')
    return deepcopy(design)


def text_font(layer):
    # Standard Windows families, with a bundled fallback on other platforms.
    family=layer['font'];bold=layer['bold'];italic=layer['italic']
    names={'sans':('arial','arialbd','ariali','arialbi'), 'serif':('times','timesbd','timesi','timesbi'), 'mono':('cour','courbd','couri','courbi')}
    filename=names.get(family,names['sans'])[(1 if bold else 0)+(2 if italic else 0)]+'.ttf'
    path=Path('C:/Windows/Fonts')/filename
    if family=='vera' or not path.is_file():
        import reportlab
        path=Path(reportlab.__file__).parent/'fonts'/('VeraBI.ttf' if bold and italic else 'VeraBd.ttf' if bold else 'VeraIt.ttf' if italic else 'Vera.ttf')
    return ImageFont.truetype(str(path),round(layer['font_size']))


def layer_padding(layer):
    if layer['kind'] in {'arrow','line','path'}:
        return math.ceil(max(12,layer['width']*4) if layer['kind']=='arrow' else layer['width'])
    return 0


def layer_image(layer):
    """Unrotated layer pixels; opacity is applied by the compositor/scene."""
    w,h=max(1,round(layer['w'])),max(1,round(layer['h']))
    padding=layer_padding(layer)
    image=Image.new('RGBA',(w+2*padding,h+2*padding));draw=ImageDraw.Draw(image)
    stroke=layer['stroke'];fill=layer['fill'];width=round(layer['width']);kind=layer['kind']
    inset=width/2;box=(inset,inset,max(inset,w-1-inset),max(inset,h-1-inset))
    if kind in {'rect','ellipse'}:
        getattr(draw,'rectangle' if kind=='rect' else 'ellipse')(box,fill=fill,outline=stroke if width else None,width=max(1,width))
    elif kind in {'triangle','diamond'}:
        x1,y1,x2,y2=box;cx=(x1+x2)/2;cy=(y1+y2)/2
        points=[(cx,y1),(x2,y2),(x1,y2)] if kind=='triangle' else [(cx,y1),(x2,cy),(cx,y2),(x1,cy)]
        if fill:draw.polygon(points,fill=fill)
        if width:draw.line(points+[points[0]],fill=stroke,width=width,joint='curve')
    elif kind in {'line','arrow','path'}:
        if not width:return image
        points=layer['points'] or [[0,0],[1,1]]
        points=[(padding+x*(w-1),padding+y*(h-1)) for x,y in points]
        draw.line(points,fill=stroke,width=max(1,width),joint='curve')
        if kind=='arrow':
            x,y=points[-1];sx,sy=points[-2];angle=math.atan2(y-sy,x-sx);length=max(12,width*4)
            def head(x,y,angle):
                first=(x-length*math.cos(angle-.5),y-length*math.sin(angle-.5));last=(x-length*math.cos(angle+.5),y-length*math.sin(angle+.5))
                if layer['arrow_style']=='open':draw.line([first,(x,y),last],fill=stroke,width=width)
                else:draw.polygon([(x,y),first,last],fill=stroke)
            head(x,y,angle)
            if layer['arrow_style']=='double':head(points[0][0],points[0][1],angle+math.pi)
    elif kind=='text':
        if fill:draw.rectangle((0,0,w,h),fill=fill)
        from .imaging import wrap_text
        font=text_font(layer);y=0
        for line in wrap_text(layer['text'],font,max(1,w-4)):
            draw.text((2,y),line,font=font,fill=stroke);y+=round(layer['font_size']*1.3)
            if y>=h:break
    elif kind=='image':
        artwork=decode_artwork(layer['image']).copy();artwork.thumbnail((w,h),Image.Resampling.LANCZOS)
        image.alpha_composite(artwork,((w-artwork.width)//2,(h-artwork.height)//2))
    return image


def render_design(design, size=None):
    """Render a validated snapshot; callers validate documents at their input boundary."""
    image=Image.new('RGBA',tuple(design['size']))
    for layer in design['layers']:
        if not layer['visible']:continue
        tile=layer_image(layer)
        if layer['opacity']!=100:
            tile.putalpha(tile.getchannel('A').point(lambda a:round(a*layer['opacity']/100)))
        tile=tile.rotate(-layer['rotation'],resample=Image.Resampling.BICUBIC,expand=True)
        x=round(layer['x']+layer['w']/2-tile.width/2);y=round(layer['y']+layer['h']/2-tile.height/2)
        image.alpha_composite(tile,(x,y))
    if size:image=image.resize(tuple(max(1,round(v)) for v in size),Image.Resampling.LANCZOS)
    return image


def import_artwork(path):
    path=Path(path)
    if path.stat().st_size>MAX_PACK:raise ValueError('Artwork file exceeds 20 MB.')
    if path.suffix.lower()=='.svg':
        raw=path.read_bytes()
        if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():raise ValueError('SVG entities are unsupported.')
        try:root=ET.fromstring(raw)
        except ET.ParseError as exc:raise ValueError('Invalid SVG file.') from exc
        # Static vector subset: no references, CSS, scripts, foreign HTML or remote resources.
        allowed={'svg','g','defs','use','path','rect','circle','ellipse','line','polyline','polygon','text','tspan','linearGradient','radialGradient','stop','clipPath','title','desc'}
        for element in root.iter():
            if element.tag.split('}')[-1] not in allowed:raise ValueError('SVG contains unsupported active or referenced content.')
            for name,value in element.attrib.items():
                attribute=name.split('}')[-1].lower()
                local_urls=re.sub(r'url\(\s*[\"\']?#[A-Za-z0-9_.:-]+[\"\']?\s*\)', '', value, flags=re.I)
                if attribute.startswith('on') or (attribute=='href' and not re.fullmatch(r'#[A-Za-z0-9_.:-]+',value)) or 'url(' in local_urls.lower() or '@import' in value.lower():
                    raise ValueError('SVG references and scripts are unsupported; export a standalone PNG instead.')
        from PySide6.QtSvg import QSvgRenderer
        from PySide6.QtCore import QByteArray,Qt
        from PySide6.QtGui import QImage,QPainter
        renderer=QSvgRenderer(QByteArray(raw))
        if not renderer.isValid():raise ValueError('SVG could not be rendered.')
        size=renderer.defaultSize()
        if size.isEmpty():size=__import__('PySide6.QtCore',fromlist=['QSize']).QSize(800,500)
        if max(size.width(),size.height())>2048:size.scale(2048,2048,Qt.AspectRatioMode.KeepAspectRatio)
        target=QImage(size,QImage.Format.Format_RGBA8888);target.fill(Qt.GlobalColor.transparent)
        painter=QPainter(target);renderer.render(painter);painter.end()
        image=Image.frombytes('RGBA',(target.width(),target.height()),bytes(target.bits()),'raw','RGBA',target.bytesPerLine())
    else:
        try:
            with Image.open(path) as source:
                if source.format not in {'PNG','JPEG','WEBP'}:raise ValueError('Use PNG, JPEG, WebP or SVG artwork.')
                if max(source.size)>8192 or source.width*source.height>16_000_000:raise ValueError('Artwork is too large (maximum 16 million pixels).')
                from PIL import ImageOps
                image=ImageOps.exif_transpose(source).convert('RGBA')
        except (OSError,Image.DecompressionBombError) as exc:raise ValueError('Cannot read this artwork.') from exc
        image.thumbnail((2048,2048),Image.Resampling.LANCZOS)
    data=BytesIO();image.save(data,'PNG')
    width,height=image.size;scale=min(1,400/max(width,height))
    return new_layer('image',name=path.stem[:120],w=max(1,round(width*scale)),h=max(1,round(height*scale)),image=base64.b64encode(data.getvalue()).decode('ascii'))


def save_pack(path,name,design):
    from .storage import atomic_bytes
    design=validate_design(design)
    if not isinstance(name,str) or not name.strip() or len(name)>120:raise ValueError('Enter a name of up to 120 characters.')
    payload=json.dumps({'format':'SOP annotation','version':1,'name':name.strip(),'design':design},ensure_ascii=False).encode('utf-8')
    if len(payload)>MAX_PACK:raise ValueError('Annotation pack exceeds 20 MB.')
    atomic_bytes(Path(path),payload)


def load_pack(path):
    path=Path(path)
    if path.stat().st_size>MAX_PACK:raise ValueError('Annotation pack exceeds 20 MB.')
    try:
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(data,dict) or data.get('format')!='SOP annotation' or data.get('version')!=1:raise ValueError('Unsupported annotation pack.')
        name=data.get('name')
        if not isinstance(name,str) or not name.strip() or len(name)>120:raise ValueError('Invalid design name.')
        return name,validate_design(data.get('design'))
    except (RecursionError,TypeError) as exc:raise ValueError('Invalid annotation pack.') from exc


class AnnotationLibrary:
    def __init__(self,root):
        from collections import OrderedDict
        self.root=Path(root);self._packs=OrderedDict();self._pack_bytes=0

    def signature(self):
        result=[]
        for path in self.root.glob('*.sopannotation'):
            try:stat=path.stat();result.append((path.name,stat.st_mtime_ns,stat.st_size))
            except OSError:continue
        return tuple(sorted(result))

    def _read(self,identity):
        path=self._path(identity);stat=path.stat();key=(str(path.resolve()),stat.st_mtime_ns,stat.st_size)
        cached=self._packs.get(identity)
        if cached and cached[0]==key:self._packs.move_to_end(identity);return cached[1]
        if cached:self._pack_bytes-=cached[2];self._packs.pop(identity)
        result=load_pack(path)
        if stat.st_size<=16*1024*1024:
            while self._packs and (self._pack_bytes+stat.st_size>16*1024*1024 or len(self._packs)>=64):
                _,old=self._packs.popitem(last=False);self._pack_bytes-=old[2]
            self._packs[identity]=(key,result,stat.st_size);self._pack_bytes+=stat.st_size
        return result

    def _path(self,identity):
        if not isinstance(identity,str) or len(identity)!=32 or any(c not in '0123456789abcdef' for c in identity):raise ValueError('Invalid design identifier.')
        return self.root/(identity+'.sopannotation')

    def entries(self):
        entries=[];self._read_failed=False
        if self.root.exists():
            for path in self.root.glob('*.sopannotation'):
                try:
                    self._path(path.stem);name,_=self._read(path.stem);entries.append((path.stem,name))
                except OSError:self._read_failed=True;continue
                except ValueError:continue
        return sorted(entries,key=lambda row:row[1].lower())

    def load(self,identity):
        name,design=self._read(identity);return name,deepcopy(design)

    def save(self,name,design,identity=None):
        identity=identity or uuid.uuid4().hex
        save_pack(self._path(identity),name,design)
        return identity

    def delete(self,identity):self._path(identity).unlink(missing_ok=True)

def from_annotation(annotation, image_size=None):
    """Convert an existing editable annotation into a local layered document and bounds."""
    if annotation.kind=='design':return deepcopy(annotation.design),list(annotation.points)
    kinds={'highlight':'rect','highlighter':'rect','circle':'ellipse','arrow':'arrow','line':'line','text':'text'}
    if annotation.kind not in kinds and annotation.kind!='callout':raise ValueError('Redactions and blur masks stay in the screenshot editor.')
    x1,y1,x2,y2=annotation.points
    left,top,right,bottom=min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2)
    if annotation.kind=='callout':
        from .imaging import callout_layout
        box,_,_=callout_layout(annotation,image_size or (max(16,math.ceil(right+800)),max(16,math.ceil(bottom+500))))
        left=min(x1,box[0]);top=min(y1,box[1]);right=max(x1,box[2]);bottom=max(y1,box[3])
    padding=max(8,annotation.width*4)
    bounds=[left-padding,top-padding,right+padding,bottom+padding]
    width,height=bounds[2]-bounds[0],bounds[3]-bounds[1];scale=min(1,2048/max(width,height))
    design=new_design(max(16,math.ceil(width*scale)),max(16,math.ceil(height*scale)))
    def layer(kind,x,y,w,h,**extras):
        return new_layer(kind,x=(x-bounds[0])*scale,y=(y-bounds[1])*scale,w=max(1,w*scale),h=max(1,h*scale),stroke=annotation.color,arrow_style=annotation.arrow_style,width=max(1,min(30,annotation.width*scale)),font_size=max(8,min(144,annotation.font_size*scale)),text=annotation.text,font='vera',**extras)
    if annotation.kind=='callout':
        bx,by,br,bb=box
        target_x=max(bx,min(br,x1));target_y=max(by,min(bb,y1))
        ax,ay=min(x1,target_x),min(y1,target_y);aw=max(1,abs(x1-target_x));ah=max(1,abs(y1-target_y))
        arrow=layer('arrow',ax,ay,aw,ah,points=[[(target_x-ax)/aw,(target_y-ay)/ah],[(x1-ax)/aw,(y1-ay)/ah]])
        design['layers']=[arrow,layer('rect',bx,by,br-bx,bb-by,fill='#ffffff'),layer('text',bx+6,by+8,max(1,br-bx-12),max(1,bb-by-16),bold=True)]
    else:
        item=layer(kinds[annotation.kind],left,top,max(1,right-left),max(1,bottom-top))
        if annotation.kind in {'arrow','line'}:
            item['points']=[[(x1-left)/max(1,right-left),(y1-top)/max(1,bottom-top)],[(x2-left)/max(1,right-left),(y2-top)/max(1,bottom-top)]]
        if annotation.kind=='text':item['bold']=True
        if annotation.kind=='highlighter':item.update(fill=annotation.color,width=0,opacity=annotation.opacity)
        design['layers']=[item]
    return validate_design(design),bounds
