"""Local recent-project metadata. Never modifies the projects themselves."""
import json
import logging
import os
from pathlib import Path
from .models import now
from .storage import atomic_bytes


class RecentProjects:
    def __init__(self,path,limit=12):
        self.path=Path(path);self.limit=limit

    @staticmethod
    def key(root):return os.path.normcase(str(Path(root).expanduser().resolve()))

    def entries(self):
        try:
            if not self.path.exists():return []
            data=json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(data,dict) or data.get('version')!=1 or not isinstance(data.get('projects'),list):return []
            result=[];seen=set()
            for row in data['projects']:
                if not isinstance(row,dict) or not all(isinstance(row.get(k),str) for k in ('root','title')) or not row['root']:continue
                key=self.key(row['root'])
                if key in seen:continue
                seen.add(key);result.append({k:row.get(k,'') if isinstance(row.get(k,''),str) else '' for k in ('root','title','template','opened')})
                if len(result)>=self.limit:break
            return result
        except (OSError,ValueError):
            logging.getLogger(__name__).warning('Recent project history could not be read')
            return []

    def _write(self,rows):
        atomic_bytes(self.path,json.dumps({'version':1,'projects':rows[:self.limit]},ensure_ascii=False,indent=2).encode('utf-8'))

    def record(self,project,root):
        key=self.key(root)
        rows=[row for row in self.entries() if self.key(row['root'])!=key]
        rows.insert(0,{'root':str(Path(root).resolve()),'title':project.title,'template':project.template.get('name','Standard SOP'),'opened':now()})
        self._write(rows)

    def remove(self,root):self._write([row for row in self.entries() if self.key(row['root'])!=self.key(root)])

    def update_title(self,project,root):
        rows=self.entries();changed=False
        for row in rows:
            if self.key(row['root'])==self.key(root) and row['title']!=project.title:
                row['title']=project.title;changed=True
        if changed:self._write(rows)
