"""Independent revision sessions with immutable input snapshots and approval history."""
from copy import deepcopy
from pathlib import Path
import json
import uuid
from .storage import atomic_bytes
from .revision_import import inspect_source,destinations,validate_word_input


class RevisionWorkspace:
    def __init__(self,root,state):
        self.root=Path(root).resolve();self.state=state;self.history=[];self.future=[]

    @property
    def elements(self):return self.state['elements']
    @property
    def destinations(self):return self.state['destinations']

    @classmethod
    def create(cls,root,source,template,revision):
        root=Path(root).resolve();source=Path(source).resolve();template=Path(template).resolve()
        if template.suffix.lower()!='.docx':raise ValueError('The new template must be a Word .docx file.')
        if source.suffix.lower() not in {'.docx','.pdf'}:raise ValueError('Old revision must be Word .docx or PDF.')
        if not revision.strip():raise ValueError('Enter the new revision.')
        validate_word_input(template)
        if source.suffix.lower()=='.docx':validate_word_input(source)
        source_data=source.read_bytes();template_data=template.read_bytes()
        root.mkdir(parents=True,exist_ok=False)
        (root/('source'+source.suffix.lower())).write_bytes(source_data);(root/'template.docx').write_bytes(template_data)
        elements,warnings=inspect_source(root/('source'+source.suffix.lower()),root/'assets')
        state={'version':1,'source_file':'source'+source.suffix.lower(),'source_original':str(source),'template_original':str(template),'revision':revision.strip(),'title':source.stem,'change_summary':'','elements':elements,'destinations':destinations(root/'template.docx'),'warnings':warnings,'placements':[],'suggestions':{},'excluded':{e['id']:'Full-page alternative; extracted elements available' for e in elements if e.get('alternative')},'authored':False}
        work=cls(root,state);work.save();return work

    @classmethod
    def open(cls,root):
        work=cls(root,json.loads((Path(root)/'revision.json').read_text(encoding='utf-8')))
        if work.state.get('version')!=1:raise ValueError('Unsupported revision workspace version.')
        for key in ('source_file',):work.resolve(work.state[key])
        work.resolve('template.docx')
        validate_word_input(work.resolve('template.docx'))
        if work.state['source_file'].endswith('.docx'):validate_word_input(work.resolve(work.state['source_file']))
        for element in work.elements:
            # Stored image paths are relative to the workspace so sessions can move.
            element['images']=[str(work.resolve(p)) for p in element.get('images',[])]
        ids={e['id'] for e in work.elements};dests={d['id'] for d in work.destinations}
        if any(p['source'] not in ids or p['destination'] not in dests for p in work.state['placements']):raise ValueError('Invalid saved placement.')
        return work

    def resolve(self,name):
        path=(self.root/name).resolve()
        if not path.is_relative_to(self.root):raise ValueError('Revision file is outside its workspace.')
        return path

    def save(self):
        data=deepcopy(self.state)
        for item in data['elements']:item['images']=[str(Path(p).resolve().relative_to(self.root)) for p in item.get('images',[])]
        atomic_bytes(self.root/'revision.json',json.dumps(data,ensure_ascii=False,indent=2).encode())

    def checkpoint(self):
        if self.state.get('authored'):raise ValueError('The document has direct Word edits. Return to placements explicitly before changing the transfer.')
        self.history.append(deepcopy(self.state));self.history=self.history[-50:];self.future=[]

    def status(self,identity):
        if any(p['source']==identity for p in self.state['placements']):return 'Approved'
        if identity in self.state['excluded']:return 'Excluded'
        return 'Suggested' if identity in self.state['suggestions'] else 'Not placed'

    def element(self,identity):
        return next(e for e in self.elements if e['id']==identity)

    def suggest(self,identity,destination,reason,text=None):
        self.element(identity)
        if destination not in {d['id'] for d in self.destinations}:raise ValueError('Unknown destination.')
        self.checkpoint();proposal={'destination':destination,'reason':reason}
        if text is not None:proposal['text']=str(text)
        self.state['suggestions'][identity]=proposal;self.save()

    def approve(self,identity,destination,*,text=None,rows=None):
        element=self.element(identity)
        if element.get('blocked'):raise ValueError('This element contains an unsupported Word object. Transfer it manually in the final Word editor, then exclude it here with a note.')
        if destination not in {d['id'] for d in self.destinations}:raise ValueError('Unknown destination.')
        if rows is not None and (not rows or any(len(r)!=len(element['rows'][0]) for r in rows) or len(rows)!=len(element['rows'])):raise ValueError('Keep the imported table dimensions; edit its cell contents.')
        self.checkpoint();existing=next((i for i,p in enumerate(self.state['placements']) if p['source']==identity),None)
        placement={'id':self.state['placements'][existing]['id'] if existing is not None else uuid.uuid4().hex,'source':identity,'destination':destination,'text':element['text'] if text is None else text,'rows':deepcopy(rows if rows is not None else element.get('rows'))}
        if existing is None:self.state['placements'].append(placement)
        else:self.state['placements'][existing]=placement
        self.state['excluded'].pop(identity,None);self.save()

    def exclude(self,identity,reason):
        self.element(identity)
        if not reason.strip():raise ValueError('Enter a reason for excluding this element.')
        if self.state.get('authored'):
            if any(p['source']==identity for p in self.state['placements']):raise ValueError('Return to placements before removing an approved transfer from the Word draft.')
            # Accounting for a manual transfer changes the report only, never the authored DOCX.
        else:self.checkpoint()
        self.state['placements']=[p for p in self.state['placements'] if p['source']!=identity];self.state['excluded'][identity]=reason;self.state['suggestions'].pop(identity,None);self.save()

    def unplace(self,identity):
        self.checkpoint();self.state['placements']=[p for p in self.state['placements'] if p['source']!=identity];self.state['excluded'].pop(identity,None);self.state['suggestions'].pop(identity,None);self.save()

    def move(self,placement_id,offset):
        placements=self.state['placements'];index=next(i for i,p in enumerate(placements) if p['id']==placement_id);target=index+offset
        if 0<=target<len(placements):self.checkpoint();placements[index],placements[target]=placements[target],placements[index];self.save()

    def undo(self):
        if self.history and not self.state.get('authored'):self.future.append(deepcopy(self.state));self.state=self.history.pop();self.save()

    def redo(self):
        if self.future and not self.state.get('authored'):self.history.append(deepcopy(self.state));self.state=self.future.pop();self.save()

    def update_details(self,title,revision,summary):
        if not revision.strip():raise ValueError('Enter the new revision.')
        self.checkpoint();self.state.update(title=title,revision=revision.strip(),change_summary=summary);self.save()
