"""Local training-video session data and non-destructive MP4 export plans."""
from dataclasses import dataclass,asdict
from pathlib import Path
import json,math,re,uuid
from .storage import atomic_bytes


@dataclass
class VideoSession:
    root: Path
    title: str='Training video'
    original: str | None=None
    narration: str | None=None
    duration: float=0
    trim_start: float=0
    trim_end: float=0
    volume: float=1
    use_narration: bool=False

    @classmethod
    def create(cls,parent,title):
        title=title.strip()
        if not title or len(title)>120:raise ValueError('Enter a video name of up to 120 characters.')
        name=re.sub(r'[^\w .-]','_',title).strip(' .') or 'Training video'
        if re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])',name,re.I):name='Video '+name
        parent=Path(parent).resolve();parent.mkdir(parents=True,exist_ok=True)
        for number in range(1,10000):
            root=parent/(name if number==1 else f'{name} ({number})')
            try:root.mkdir()
            except FileExistsError:continue
            value=cls(root,title);value.save();return value
        raise ValueError('Choose another video name.')

    def asset(self,name):
        if not isinstance(name,str) or not name or Path(name).name!=name or any(c in name for c in '/\\:<>"|?*\0') or name.endswith((' ','.')) or re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)',name,re.I):
            raise ValueError('Invalid video asset path.')
        path=(self.root/name).resolve()
        if not path.is_relative_to(self.root.resolve()) or path==self.root.resolve():raise ValueError('Video asset leaves its session folder.')
        return path

    def new_asset(self,kind,suffix):
        return self.asset(kind+'-'+uuid.uuid4().hex+suffix)

    def validate(self):
        if not isinstance(self.title,str) or not self.title.strip() or len(self.title)>120:raise ValueError('Invalid video name.')
        for name in ('original','narration'):
            if getattr(self,name) is not None:self.asset(getattr(self,name))
        for name in ('duration','trim_start','trim_end','volume'):
            value=getattr(self,name)
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:raise ValueError('Invalid video '+name)
        if self.volume>2 or type(self.use_narration) is not bool:raise ValueError('Invalid narration settings.')
        if self.trim_end and self.trim_end<=self.trim_start:raise ValueError('Trim end must be after the start.')

    def save(self):
        self.validate();data=asdict(self);data.pop('root');data['schema_version']=1
        atomic_bytes(self.root/'video.json',json.dumps(data,indent=2).encode())

    @classmethod
    def load(cls,path):
        path=Path(path).resolve();root=path if path.is_dir() else path.parent
        file=root/'video.json'
        if file.stat().st_size>65536:raise ValueError('Video session is too large.')
        data=json.loads(file.read_text(encoding='utf-8'))
        if not isinstance(data,dict) or data.pop('schema_version',None)!=1:raise ValueError('Unsupported video session.')
        value=cls(root,**{k:v for k,v in data.items() if k in cls.__dataclass_fields__ and k!='root'});value.validate();return value


def export_arguments(session,output):
    session.validate();output=Path(output).resolve()
    protected={session.asset(n) for n in (session.original,session.narration) if n}
    if output in protected or output.suffix.lower()!='.mp4':raise ValueError('Choose a separate MP4 export file; originals are preserved.')
    if not session.original or not session.asset(session.original).is_file():raise ValueError('Record a video first.')
    end=session.trim_end or session.duration
    if end<=session.trim_start or end>session.duration+.1:raise ValueError('Choose a valid start and end within the recording.')
    duration=end-session.trim_start
    args=['-hide_banner','-nostdin','-y','-progress','pipe:1','-nostats','-protocol_whitelist','file,pipe','-ss',f'{session.trim_start:g}','-i',str(session.asset(session.original))]
    if session.use_narration:
        if not session.narration or not session.asset(session.narration).is_file():raise ValueError('Record a voiceover first, or use the original audio.')
        args+=['-protocol_whitelist','file,pipe','-ss',f'{session.trim_start:g}','-i',str(session.asset(session.narration))]
    args+=['-map','0:v:0','-map','1:a:0' if session.use_narration else '0:a:0?','-t',f'{duration:g}',
           '-vf','pad=ceil(iw/2)*2:ceil(ih/2)*2','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',
           '-af',f'volume={session.volume:g},apad','-c:a','aac','-b:a','192k','-movflags','+faststart',str(output)]
    return args
