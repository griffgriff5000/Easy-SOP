from PIL import Image
from docx import Document
from pypdf import PdfReader
from sop_capture.models import Project,Step
from sop_capture.storage import ProjectStore
from sop_capture.pdf_export import export_pdf
from sop_capture.word_export import export_docx
import pytest


def example(tmp_path,layout):
    store=ProjectStore(tmp_path);steps=[]
    for n in range(4):
        step=Step(title=f'Example {n}',description=f'Instruction {n}')
        step.image=store.add_image(Image.new('RGB',(300,20),(20+n*40,100,150)),step.id);steps.append(step)
    return Project(steps=steps,template={'kind':'custom','name':'Layout','settings':{'cover':False,'screenshots_per_page':2,'screenshot_layout':layout}})


def test_vertical_pdf_limits_images_and_preserves_all_instructions(tmp_path):
    project=example(tmp_path,'vertical');output=export_pdf(project,tmp_path,tmp_path/'layout.pdf')
    pages=PdfReader(output).pages
    assert all(len(page.images)<=2 for page in pages)
    assert sum(len(page.images) for page in pages)==4
    text=''.join(p.extract_text() for p in pages)
    assert all(f'Instruction {n}' in text for n in range(4))


@pytest.mark.parametrize('count',[1,2,3,4,6])
@pytest.mark.parametrize('layout',['vertical','grid'])
def test_pdf_choices_keep_every_image_and_do_not_exceed_limit(tmp_path,count,layout):
    project=example(tmp_path,layout);project.template['settings']['screenshots_per_page']=count
    pages=PdfReader(export_pdf(project,tmp_path,tmp_path/'choice.pdf')).pages
    assert sum(len(p.images) for p in pages)==4
    assert all(len(p.images)<=count for p in pages)


def test_long_grid_instructions_flow_without_clipping(tmp_path):
    project=example(tmp_path,'grid')
    project.steps[0].description=('Long instruction. '*600)+'END OF INSTRUCTION'
    output=export_pdf(project,tmp_path,tmp_path/'long.pdf')
    text=''.join(p.extract_text() for p in PdfReader(output).pages)
    assert 'END OF INSTRUCTION' in text
    assert 'Instruction 3' in text
    assert sum(len(p.images) for p in PdfReader(output).pages)==4


def test_grid_word_uses_two_columns_and_keeps_template_structure(tmp_path):
    project=example(tmp_path,'grid')
    source=Document();source.sections[0].header.paragraphs[0].text='Company header'
    source.add_paragraph('Company cover');source.add_table(rows=1,cols=1).cell(0,0).text='Required table'
    source.add_paragraph('{{steps}}');source.save(tmp_path/'template.docx')
    project.template.update(kind='docx',docx='template.docx')
    document=Document(export_docx(project,tmp_path,tmp_path/'layout.docx'))
    assert document.sections[0].header.paragraphs[0].text=='Company header'
    assert document.tables[0].cell(0,0).text=='Required table'
    grids=[t for t in document.tables if len(t.columns)==2]
    assert len(grids)==2
    assert all(f'Instruction {n}' in '\n'.join(c.text for t in grids for r in t.rows for c in r.cells) for n in range(4))


@pytest.mark.parametrize('layout',['vertical','grid'])
def test_cover_does_not_add_a_second_empty_page_break(tmp_path,layout):
    project=example(tmp_path,layout);project.steps=project.steps[:1];project.template['settings']['cover']=True
    document=Document(export_docx(project,tmp_path,tmp_path/'cover.docx'))
    breaks=[p for p in document.paragraphs if p.paragraph_format.page_break_before]
    assert len(breaks)==1


def test_existing_procedure_heading_stays_with_generated_grid(tmp_path):
    project=example(tmp_path,'grid')
    source=Document();source.add_paragraph('Company cover');source.add_paragraph('Procedure',style='Heading 1');source.add_paragraph('{{steps}}');source.save(tmp_path/'template.docx')
    project.template.update(kind='docx',docx='template.docx')
    document=Document(export_docx(project,tmp_path,tmp_path/'procedure.docx'))
    heading=next(p for p in document.paragraphs if p.text=='Procedure')
    assert heading.paragraph_format.page_break_before
    assert heading.paragraph_format.keep_with_next


def test_directly_edited_document_is_not_regenerated_by_layout_settings(tmp_path):
    project=example(tmp_path,'grid');source=Document();source.add_paragraph('My direct document edits')
    source.save(tmp_path/'authored.docx');project.document_file='authored.docx'
    original=(tmp_path/'authored.docx').read_bytes()
    output=export_docx(project,tmp_path,tmp_path/'preserved.docx')
    assert output.read_bytes()==original
