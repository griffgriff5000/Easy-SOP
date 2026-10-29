from PySide6.QtWidgets import QApplication
from sop_capture.revisions import RevisionWorkspace
from sop_capture.ui.revision_page import RevisionPage
from test_revisions import documents


def test_review_approve_edit_move_and_reopen(tmp_path):
    app=QApplication.instance();old,template=documents(tmp_path)
    work=RevisionWorkspace.create(tmp_path/'revision',old,template,'B');page=RevisionPage(None)
    page.bind(work);index=next(i for i,e in enumerate(work.elements) if e['kind']=='text');page.sources.setCurrentRow(index)
    page.text.setPlainText('Changed by reviewer');page.approve()
    assert work.state['placements'][0]['text']=='Changed by reviewer'
    page.sources.setCurrentRow(next(i for i,e in enumerate(work.elements) if e['kind']=='table'))
    page.table.item(1,1).setText('Revised duty');page.approve()
    assert work.state['placements'][1]['rows'][1][1]=='Revised duty'
    page.placements.setCurrentRow(1);page.move(-1)
    assert work.element(work.state['placements'][0]['source'])['kind']=='table'
    page.undo();assert work.element(work.state['placements'][0]['source'])['kind']=='text'
    page.bind(RevisionWorkspace.open(work.root));assert page.placements.count()==2
    page.close_session();page.close();page.deleteLater();app.processEvents()


def test_assistant_does_not_approve_and_word_edits_are_preserved(tmp_path):
    old,template=documents(tmp_path);work=RevisionWorkspace.create(tmp_path/'revision',old,template,'B');page=RevisionPage(None);page.bind(work)
    page.sources.setCurrentRow(1);page.instruction.setText('Move below Roles and responsibilities');page.ask()
    assert work.status(work.elements[1]['id'])=='Suggested' and not work.state['placements']
    page.approve();page.persist_document(b'edited file','')
    assert work.state['authored'] and (work.root/'authored.docx').read_bytes()==b'edited file'
    assert not page.approve_button.isEnabled()
    page.close_session();page.close();page.deleteLater()


def test_pdf_workspace_preview_and_lock_cleanup(tmp_path):
    from reportlab.pdfgen.canvas import Canvas
    from PySide6.QtCore import QLockFile
    old,template=documents(tmp_path);pdf=tmp_path/'old.pdf';c=Canvas(str(pdf));c.drawString(50,700,'Old procedure');c.save()
    work=RevisionWorkspace.create(tmp_path/'revision',pdf,template,'B');page=RevisionPage(None);page.bind(work)
    assert page.pdf_document.pageCount()==1
    other=QLockFile(str(work.root/'revision.lock'));assert not other.tryLock(0)
    assert page.close_session();assert other.tryLock(0);other.unlock()
    page.close();page.deleteLater()
