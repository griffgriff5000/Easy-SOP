import pytest
from sop_capture.workspace_layouts import LayoutLibrary,portable_copy,validate_layout


def sample():
    return {'version':1,'screen':'editor','state':'','panels':{'outline':{'area':'left','visible':True,'floating':False,'size':[210,500]},'properties':{'area':'right','visible':False,'floating':False,'size':[280,500]}},'toolbar':['save','undo'],'tool_style':'both','theme':'auto','font_size':10,'density':'comfortable','locked':False}


def test_screen_layouts_and_named_presets_are_independent(tmp_path):
    library=LayoutLibrary(tmp_path/'layouts.json');editor=sample();library.save_screen('editor',editor)
    other=sample();other['screen']='revision';other['panels']['outline']['area']='bottom';library.save_screen('revision',other)
    assert library.screen('editor')['panels']['outline']['area']=='left'
    library.save_preset('My review',other);assert LayoutLibrary(library.path).presets()['My review']['screen']=='revision'
    library.delete_preset('My review');assert not library.presets()


def test_cross_screen_copy_retains_unmatched_tools_and_skips_native_state():
    source=sample();source['state']='AA==';source['toolbar']=['undo','save']
    target=sample();target['screen']='revision';target['toolbar']=['revision_new','revision_export'];target['panels']['assistant']={'area':'bottom','visible':True,'floating':False,'size':[400,120]}
    result=portable_copy(source,target,{'revision_new','revision_export'})
    assert result['screen']=='revision' and result['state']==''
    assert result['toolbar']==['revision_new','revision_export']
    assert result['panels']['assistant']==target['panels']['assistant']
    assert result['panels']['properties']['visible'] is False
    assert target['state']==''


def test_invalid_and_corrupt_layouts_are_recoverable(tmp_path):
    profile=sample();profile['font_size']=999
    with pytest.raises(ValueError):validate_layout(profile)
    path=tmp_path/'layouts.json';path.write_text('{broken');library=LayoutLibrary(path)
    assert library.screen('editor') is None and not library.presets()


def test_copy_hides_shared_unchecked_actions_but_retains_screen_specific_tools():
    source=sample();source['toolbar']=['undo'];source['available_actions']=['undo','save','review']
    target=sample();target['screen']='revision';target['toolbar']=['save','review','revision_export']
    result=portable_copy(source,target,{'save','undo','review','revision_export'})
    assert result['toolbar']==['undo','revision_export']
