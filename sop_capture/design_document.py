"""Undoable document operations for the annotation studio."""
from copy import deepcopy
import uuid
from PySide6.QtCore import QObject, Signal
from .designs import new_design, validate_design


class DesignDocument(QObject):
    changed=Signal()
    selection_changed=Signal()

    def __init__(self, design=None):
        super().__init__()
        self.design=validate_design(design or new_design())
        self.selected=[];self.history=[];self.future=[]

    def set_selection(self, identities):
        self.selected=[row['id'] for row in self.design['layers'] if row['id'] in identities]
        self.selection_changed.emit()

    def selected_layers(self, editable=False):
        return [row for row in self.design['layers'] if row['id'] in self.selected and (not editable or not row['locked'])]

    def commit(self, design):
        candidate=validate_design(design)
        if candidate==self.design:return False
        self.history.append(deepcopy(self.design));self.history=self.history[-60:];self.future.clear()
        self.design=candidate
        self.selected=[identity for identity in self.selected if any(row['id']==identity for row in candidate['layers'])]
        self.changed.emit();return True

    def add(self, layer):
        candidate=deepcopy(self.design);candidate['layers'].append(deepcopy(layer))
        self.commit(candidate);self.set_selection([layer['id']])

    def update(self, values):
        candidate=deepcopy(self.design)
        for row in candidate['layers']:
            if row['id'] in self.selected and (not row['locked'] or set(values)<= {'locked','visible'}):row.update(values)
        self.commit(candidate)

    def undo(self):
        if not self.history:return
        self.future.append(self.design);self.design=self.history.pop();self.selected=[];self.changed.emit()

    def redo(self):
        if not self.future:return
        self.history.append(self.design);self.design=self.future.pop();self.selected=[];self.changed.emit()

    def remove(self):
        candidate=deepcopy(self.design)
        candidate['layers']=[row for row in candidate['layers'] if row['id'] not in self.selected or row['locked']]
        self.commit(candidate)

    def duplicate(self):
        candidate=deepcopy(self.design);identities=[];groups={}
        for row in self.selected_layers():
            row=deepcopy(row);row['id']=uuid.uuid4().hex;row['x']+=10;row['y']+=10;row['locked']=False
            if row['group']:row['group']=groups.setdefault(row['group'],uuid.uuid4().hex)
            identities.append(row['id']);candidate['layers'].append(row)
        self.commit(candidate);self.set_selection(identities)

    def group(self, ungroup=False):
        self.update({'group':'' if ungroup else uuid.uuid4().hex})

    def reorder(self, delta):
        candidate=deepcopy(self.design);layers=candidate['layers']
        indices=range(len(layers)-2,-1,-1) if delta>0 else range(1,len(layers))
        for i in indices:
            j=i+delta
            if layers[i]['id'] in self.selected and not layers[i]['locked'] and layers[j]['id'] not in self.selected:
                layers[i],layers[j]=layers[j],layers[i]
        self.commit(candidate)

    def align(self, mode):
        layers=self.selected_layers(editable=True)
        if not layers:return
        candidate=deepcopy(self.design)
        left=min(row['x'] for row in layers);top=min(row['y'] for row in layers)
        right=max(row['x']+row['w'] for row in layers);bottom=max(row['y']+row['h'] for row in layers)
        for row in candidate['layers']:
            if row['id'] not in self.selected or row['locked']:continue
            if mode=='left':row['x']=left
            elif mode=='top':row['y']=top
            elif mode=='center':row['x']=(self.design['size'][0]-row['w'])/2
            elif mode=='middle':row['y']=(self.design['size'][1]-row['h'])/2
            elif mode=='right':row['x']=right-row['w']
            elif mode=='bottom':row['y']=bottom-row['h']
        self.commit(candidate)
