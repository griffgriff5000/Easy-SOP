from PIL import Image
from sop_capture.models import Project,Step,Annotation
from sop_capture.storage import ProjectStore
from sop_capture.ui.preview_cache import PreviewCache


def test_preview_cache_reuses_decode_and_invalidates_changed_image(tmp_path,monkeypatch):
    from PIL import Image as Images
    path=tmp_path/'image.png';Image.new('RGB',(300,100),'red').save(path);cache=PreviewCache();calls=[];original=Images.open
    def opened(*args,**kwargs):calls.append(args[0]);return original(*args,**kwargs)
    monkeypatch.setattr(Images,'open',opened)
    assert cache.image(path).getpixel((0,0))==(255,0,0)
    assert cache.image(path).getpixel((0,0))==(255,0,0) and len(calls)==1
    Image.new('RGB',(301,100),'blue').save(path)
    assert cache.image(path).getpixel((0,0))==(0,0,255) and len(calls)==2


def test_thumbnails_reuse_shared_images_and_respect_annotation_changes(tmp_path,monkeypatch):
    import sop_capture.ui.preview_cache as module
    store=ProjectStore(tmp_path);step=Step();step.image=store.add_image(Image.new('RGB',(400,200),'white'),step.id);project=Project(steps=[step]);cache=PreviewCache();calls=[];render=module.render_image
    def counted(*args):calls.append(1);return render(*args)
    monkeypatch.setattr(module,'render_image',counted)
    cache.thumbnail(tmp_path,step,1,project);cache.thumbnail(tmp_path,step,2,project);assert len(calls)==1
    step.annotations.append(Annotation(kind='redact',points=[0,0,200,200]))
    result=cache.thumbnail(tmp_path,step,2,project);assert len(calls)==2 and result.getpixel((1,1))==(0,0,0)
    assert cache.image(store.resolve(step.image)).getpixel((0,0))==(255,255,255)


def test_layout_library_skips_unchanged_atomic_writes(tmp_path,monkeypatch):
    import sop_capture.workspace_layouts as module
    from test_workspace_layouts import sample
    library=module.LayoutLibrary(tmp_path/'layouts.json');calls=[];original=module.atomic_bytes
    def write(*args):calls.append(1);return original(*args)
    monkeypatch.setattr(module,'atomic_bytes',write)
    library.save_screen('editor',sample());library.save_screen('editor',sample());assert len(calls)==1


def test_library_revisit_does_not_render_unchanged_designs(tmp_path,monkeypatch):
    import sop_capture.ui.annotation_library_page as module
    from sop_capture.designs import AnnotationLibrary,new_design
    library=AnnotationLibrary(tmp_path/'annotations');identity=library.save('Saved',new_design())
    page=module.AnnotationLibraryPage(library);calls=[];render=module.render_design
    def counted(*args,**kwargs):calls.append(1);return render(*args,**kwargs)
    monkeypatch.setattr(module,'render_design',counted);page.refresh();page.refresh()
    assert not calls
    library.save('Changed',new_design(500,200),identity);page.refresh();assert calls
    page.close();page.deleteLater()


def test_revision_does_not_rebuild_word_preview_during_placement_edits(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QApplication
    from test_revisions import documents
    from sop_capture.revisions import RevisionWorkspace
    import sop_capture.ui.revision_page as module
    old,template=documents(tmp_path);work=RevisionWorkspace.create(tmp_path/'revision',old,template,'B');calls=[]
    def build(*args):calls.append(1);return template
    monkeypatch.setattr(module,'build_document',build)
    page=module.RevisionPage(None);page.bind(work);page.sources.setCurrentRow(1);page.approve()
    assert not calls
    page.right_tabs.setCurrentIndex(2);QApplication.processEvents();assert len(calls)==1
    page.right_tabs.setCurrentIndex(0);page.right_tabs.setCurrentIndex(2);QApplication.processEvents();assert len(calls)==1
    page.close_session();page.close();page.deleteLater()


def test_canvas_reuses_rendered_screenshot_until_its_annotations_change(tmp_path,monkeypatch):
    from sop_capture.ui.canvas import AnnotationCanvas
    import sop_capture.ui.preview_cache as module
    store=ProjectStore(tmp_path);step=Step();step.image=store.add_image(Image.new('RGB',(400,200),'white'),step.id);project=Project(steps=[step]);calls=[];render=module.render_image
    def counted(*args):calls.append(1);return render(*args)
    monkeypatch.setattr(module,'render_image',counted);canvas=AnnotationCanvas();canvas.set_step(tmp_path,project,step,1);canvas.refresh();canvas.refresh()
    assert len(calls)==1
    step.annotations.append(Annotation(kind='redact',points=[0,0,100,100]));canvas.refresh();assert len(calls)==2
    canvas.close();canvas.deleteLater()


def test_final_word_save_does_not_restart_preview_after_closing(tmp_path,monkeypatch):
    from test_revisions import documents
    from sop_capture.revisions import RevisionWorkspace
    from sop_capture.ui.revision_page import RevisionPage
    old,template=documents(tmp_path);page=RevisionPage(None);page.bind(RevisionWorkspace.create(tmp_path/'revision',old,template,'B'));page.right_tabs.setCurrentIndex(2)
    monkeypatch.setattr(page.word_editor,'close_document',lambda:page.persist_document(template.read_bytes(),''))
    assert page.close_session() and not page.preview_timer.isActive()
    page.close();page.deleteLater()


def test_temporary_library_read_failure_is_retried_on_revisit(tmp_path,monkeypatch):
    import sop_capture.designs as designs
    from sop_capture.ui.annotation_library_page import AnnotationLibraryPage
    library=designs.AnnotationLibrary(tmp_path/'annotations');library.save('Saved',designs.new_design());original=designs.load_pack;calls=[]
    def temporarily_locked(path):
        calls.append(1)
        if len(calls)==1:raise PermissionError('Temporary sharing violation')
        return original(path)
    monkeypatch.setattr(designs,'load_pack',temporarily_locked);page=AnnotationLibraryPage(library);assert page.entries.count()==0
    page.refresh();assert page.entries.count()==1
    page.close();page.deleteLater()
