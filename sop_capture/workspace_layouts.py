"""Local, versioned UI preferences. Never contains document or project data."""
from copy import deepcopy
import base64
import json
import logging
from pathlib import Path
from .storage import atomic_bytes


def validate_layout(value):
    if not isinstance(value,dict) or value.get('version')!=1:raise ValueError('Unsupported workspace layout.')
    result=deepcopy(value)
    if not isinstance(result.get('screen'),str) or len(result['screen'])>80:raise ValueError('Invalid workspace screen.')
    if result.get('theme') not in {'auto','light','dark'} or result.get('density') not in {'compact','comfortable'}:raise ValueError('Invalid workspace appearance.')
    if type(result.get('font_size')) is not int or not 8<=result['font_size']<=16:raise ValueError('Text size must be 8–16 points.')
    if type(result.get('locked')) is not bool or result.get('tool_style') not in {'icons','text','both'}:raise ValueError('Invalid workspace controls.')
    actions=result.get('toolbar')
    if not isinstance(actions,list) or len(actions)>100 or any(not isinstance(a,str) or len(a)>100 for a in actions):raise ValueError('Invalid workspace toolbar.')
    result['toolbar']=list(dict.fromkeys(actions))
    available=result.get('available_actions',result['toolbar'])
    if not isinstance(available,list) or len(available)>200 or any(not isinstance(a,str) or len(a)>100 for a in available):raise ValueError('Invalid workspace action catalogue.')
    result['available_actions']=list(dict.fromkeys(available))
    state=result.get('state','')
    if not isinstance(state,str) or len(state)>200000:raise ValueError('Invalid dock state.')
    try:base64.b64decode(state,validate=True)
    except Exception as exc:raise ValueError('Invalid dock state encoding.') from exc
    panels=result.get('panels')
    if not isinstance(panels,dict) or len(panels)>30:raise ValueError('Invalid workspace panels.')
    for role,panel in panels.items():
        if not isinstance(role,str) or not isinstance(panel,dict) or panel.get('area') not in {'left','right','top','bottom'}:raise ValueError('Invalid panel position.')
        if any(type(panel.get(key)) is not bool for key in ('visible','floating')):raise ValueError('Invalid panel visibility.')
        for key,length in (('size',2),('geometry',4)):
            if key not in panel and key=='geometry':continue
            coords=panel.get(key)
            if not isinstance(coords,list) or len(coords)!=length or any(type(n) is not int or abs(n)>100000 for n in coords):raise ValueError('Invalid panel dimensions.')
    return result


def portable_copy(source,target,allowed_actions):
    source=validate_layout(source);target=validate_layout(target)
    for key in ('theme','density','font_size','locked','tool_style'):target[key]=source[key]
    for role in target['panels']:
        if role in source['panels']:target['panels'][role]=deepcopy(source['panels'][role])
    matching=[a for a in source['toolbar'] if a in allowed_actions]
    target['toolbar']=matching+[a for a in target['toolbar'] if a not in source['available_actions'] and a not in matching]
    target['state']=''
    return target


class LayoutLibrary:
    def __init__(self,path):
        self.path=Path(path);self.data={'version':1,'screens':{},'presets':{}}
        try:
            raw=json.loads(self.path.read_text(encoding='utf-8'))
            if raw.get('version')!=1:raise ValueError('Unsupported layout preferences.')
            for category in ('screens','presets'):
                if not isinstance(raw.get(category),dict):continue
                for name,value in raw[category].items():
                    try:self.data[category][name]=validate_layout(value)
                    except (ValueError,TypeError):logging.getLogger(__name__).warning('Skipped invalid workspace layout')
        except FileNotFoundError:pass
        except (ValueError,OSError,TypeError,AttributeError):logging.getLogger(__name__).warning('Workspace preferences could not be read; using defaults')

    def write(self):atomic_bytes(self.path,json.dumps(self.data,ensure_ascii=False,indent=2).encode())
    def screen(self,name):return deepcopy(self.data['screens'].get(name))
    def save_screen(self,name,value):self.data['screens'][name]=validate_layout(value);self.write()
    def presets(self):return deepcopy(self.data['presets'])
    def save_preset(self,name,value):
        name=name.strip()
        if not name or len(name)>100:raise ValueError('Enter a layout name of 1–100 characters.')
        self.data['presets'][name]=validate_layout(value);self.write()
    def delete_preset(self,name):self.data['presets'].pop(name,None);self.write()
