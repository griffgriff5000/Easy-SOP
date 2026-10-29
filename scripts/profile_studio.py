"""Repeatable UI benchmark on isolated synthetic project/preferences (no Word automation)."""
from pathlib import Path
from tempfile import TemporaryDirectory
import cProfile,pstats,json,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication
from PIL import Image
from sop_capture.ui.main_window import MainWindow
from sop_capture.workspace_layouts import LayoutLibrary
from sop_capture.recent_projects import RecentProjects
from sop_capture.templates import TemplateLibrary
from sop_capture.designs import AnnotationLibrary,new_design,new_layer
from sop_capture.models import Project,Step
from sop_capture.storage import ProjectStore


def main():
    QStandardPaths.setTestModeEnabled(True);app=QApplication([]);out=Path('.superpowers/performance');out.mkdir(parents=True,exist_ok=True);label=sys.argv[1] if len(sys.argv)>1 else 'run';results={};profile=cProfile.Profile()
    with TemporaryDirectory() as temp:
        root=Path(temp);library=AnnotationLibrary(root/'annotations');design=new_design(300,150);design['layers']=[new_layer('text',x=10,y=20,w=250,h=100,text='Instruction label',font_size=24)]
        for i in range(12):library.save(f'Design {i}',design)
        store=ProjectStore(root/'project');project=Project(steps=[Step(title=f'Step {i}') for i in range(80)]);image=store.add_image(Image.new('RGB',(1600,900),'white'),project.steps[0].id)
        for step in project.steps:step.image=image
        def measured(name,operation):
            start=time.perf_counter();operation();results[name]=round(time.perf_counter()-start,4)
        profile.enable();start=time.perf_counter();window=MainWindow(TemplateLibrary(root/'templates'),RecentProjects(root/'recent.json'),library,LayoutLibrary(root/'layouts.json'));results['construct']=round(time.perf_counter()-start,4)
        window._maybe_builder_preview=lambda:None
        measured('load_80_steps',lambda:window.set_project(project,store));window.show_page(1);window.show();app.processEvents()
        measured('type_30_characters',lambda:[window.step_description.setPlainText('Instruction '+('x'*i)) for i in range(30)])
        measured('select_20_steps',lambda:[window.steps_list.setCurrentRow(i) for i in range(20)])
        measured('navigate_12_screens',lambda:[(window.show_page(i),app.processEvents()) for i in [5,6,1,4]*3])
        measured('resize_10_times',lambda:[(window.resize(1100+i*10,800),app.processEvents()) for i in range(10)])
        measured('idle_100_ticks',lambda:[window._tick() for _ in range(100)])
        window.close();profile.disable()
    profile.dump_stats(str(out/(label+'.prof')))
    with (out/(label+'.txt')).open('w') as stream:pstats.Stats(profile,stream=stream).sort_stats('cumulative').print_stats(45)
    (out/(label+'.json')).write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))

if __name__=='__main__':main()
