"""Non-destructive video sections and shared preview/export artwork."""
from copy import deepcopy
from dataclasses import asdict
import math,json
from functools import lru_cache
from PIL import Image,ImageDraw,ImageFont,ImageColor,ImageOps
from .models import Annotation,Project,Step
from .designs import from_annotation,render_design
from .imaging import font_path,wrap_text

SIZE=(1280,720)

def legacy_section(session):
    return dict(kind='video',title=session.title,source=session.original,source_duration=session.duration,
        start=session.trim_start,end=session.trim_end or session.duration,narration=session.narration,
        narration_origin=0,use_narration=session.use_narration,volume=session.volume,overlays=[])

def section_duration(section):
    return section['duration'] if section['kind']=='card' else section['end']-section['start']

def number(value,low,high):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and low<=value<=high

def validate_timeline(session,sections):
    if not isinstance(sections,list) or len(sections)>200:raise ValueError('Use up to 200 video sections.')
    for section in sections:
        if not isinstance(section,dict) or section.get('kind') not in {'video','card'}:raise ValueError('Invalid video section.')
        if not isinstance(section.get('title'),str) or len(section['title'])>200:raise ValueError('Section name is too long.')
        if section['kind']=='video':
            session.asset(section.get('source'))
            if not number(section.get('source_duration'),.04,360000) or not number(section.get('start'),0,section['source_duration']) or not number(section.get('end'),0,section['source_duration']) or section['end']-section['start']<.04:raise ValueError('Choose section start/end within the source video, at least 0.04 seconds apart.')
            if not number(section.get('volume'),0,2) or type(section.get('use_narration')) is not bool:raise ValueError('Invalid section audio settings.')
            if section.get('narration'):session.asset(section['narration'])
            if not number(section.get('narration_origin'),0,section['source_duration']):raise ValueError('Invalid voiceover alignment.')
            if section['use_narration'] and not section.get('narration'):raise ValueError('Record a section voiceover first.')
            if section.get('speech') is not None:
                from .speech_runtime import validate_script
                speech=section['speech']
                if not isinstance(speech,dict) or set(speech)!={'script','voice','speed'}:raise ValueError('Invalid text-to-speech settings.')
                validate_script(speech['script'],speech['voice'],speech['speed'])
        else:
            if not number(section.get('duration'),.1,120):raise ValueError('Card duration must be between 0.1 and 120 seconds.')
            if not isinstance(section.get('text'),str) or len(section['text'])>6000:raise ValueError('Card text is too long.')
            for key in ('background','foreground'):
                try:ImageColor.getrgb(section[key])
                except (KeyError,ValueError,TypeError):raise ValueError('Choose a valid card colour.')
            if section.get('logo'):session.asset(section['logo'])
        overlays=section.get('overlays')
        if not isinstance(overlays,list) or len(overlays)>100:raise ValueError('Use up to 100 annotations per section.')
        for overlay in overlays:
            duration=section_duration(section)
            if not isinstance(overlay,dict) or not number(overlay.get('start'),0,duration) or not number(overlay.get('end'),0,duration) or overlay['end']<=overlay['start']:raise ValueError('Annotation times must be within the section.')
            try:
                a=Annotation(**overlay['annotation'])
                if a.kind not in {'arrow','line','highlight','highlighter','circle','text','callout','design'}:raise ValueError('Unsupported video annotation.')
                Project.from_dict(Project(steps=[Step(annotations=[a])]).to_dict())
                if any(not number(v,0,max(SIZE)) for v in a.points):raise ValueError('Invalid annotation coordinates.')
            except (KeyError,TypeError) as exc:raise ValueError('Invalid video annotation.') from exc
    if sum(section_duration(s) for s in sections)>86400:raise ValueError('Keep the edited video under 24 hours.')
    return sections

def split_section(section,position):
    duration=section_duration(section)
    if section['kind']!='video' or not number(position,.04,duration-.04):raise ValueError('Split inside a video section, away from its ends.')
    left,right=deepcopy(section),deepcopy(section);cut=section['start']+position
    left['end']=cut;right['start']=cut;right['title']+=' (continued)'
    for part,offset,length in ((left,0,position),(right,position,duration-position)):
        part['overlays']=[]
        for item in section['overlays']:
            start=max(0,item['start']-offset);end=min(length,item['end']-offset)
            if end>start:part['overlays'].append(deepcopy(item)|dict(start=start,end=end))
    return left,right

def trim_section(section,start,end):
    result=deepcopy(section);offset=start-section['start'];result.update(start=start,end=end)
    result['overlays']=[]
    for item in section['overlays']:
        a=max(0,item['start']-offset);b=min(end-start,item['end']-offset)
        if b>a:result['overlays'].append(deepcopy(item)|dict(start=a,end=b))
    return result

def overlay_artwork(item):
    return _overlay_artwork(json.dumps(item['annotation'],sort_keys=True))

@lru_cache(maxsize=16)
def _overlay_artwork(encoded):
    annotation=Annotation(**json.loads(encoded));design,bounds=from_annotation(annotation,SIZE)
    artwork=render_design(design);left,top,right,bottom=map(round,bounds)
    artwork=artwork.resize((max(1,right-left),max(1,bottom-top)),Image.Resampling.LANCZOS)
    layer=Image.new('RGBA',SIZE);layer.paste(artwork,(left,top))
    return layer

def render_overlays(image,section,position):
    result=image.convert('RGBA')
    for item in section.get('overlays',[]):
        if item['start']<=position<item['end']:result=Image.alpha_composite(result,overlay_artwork(item))
    return result.convert('RGB')

def render_card(session,section):
    image=Image.new('RGB',SIZE,section['background']);draw=ImageDraw.Draw(image)
    titlefont=ImageFont.truetype(str(font_path(True)),54);font=ImageFont.truetype(str(font_path()),30)
    y=70
    if section.get('logo'):
        with Image.open(session.asset(section['logo'])) as source:
            source.load();logo=source.convert('RGBA');logo.thumbnail((240,130));image.paste(logo,((1280-logo.width)//2,y),logo);y+=150
    lines=wrap_text(section['title'],titlefont,1100)
    for line in lines[:3]:draw.text((640,y),line,font=titlefont,fill=section['foreground'],anchor='mt');y+=67
    y+=30
    for line in wrap_text(section['text'],font,1100):
        if y>660:break
        draw.text((640,y),line,font=font,fill=section['foreground'],anchor='mt');y+=40
    return image
