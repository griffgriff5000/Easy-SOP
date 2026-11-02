from copy import deepcopy
import pytest
from PIL import Image
from sop_capture.training_video import VideoSession
from sop_capture.video_timeline import legacy_section,split_section,validate_timeline,section_duration,render_card,render_overlays


def test_legacy_session_migrates_without_changing_original(tmp_path):
    session=VideoSession.create(tmp_path,'Legacy');session.original='take.mkv';session.duration=10;session.trim_start=2;session.trim_end=8
    session.asset('take.mkv').write_bytes(b'original');session.narration='voice.wav';session.use_narration=True
    clip=legacy_section(session);assert (clip['start'],clip['end'],clip['narration_origin'])==(2,8,0)
    session.timeline=[clip];session.save();loaded=VideoSession.load(session.root)
    assert loaded.timeline==[clip] and loaded.asset('take.mkv').read_bytes()==b'original'


def test_split_preserves_source_alignment_and_relative_overlays(tmp_path):
    session=VideoSession.create(tmp_path,'Split');session.original='take.mkv';session.duration=10
    clip=legacy_section(session);clip['start']=2;clip['end']=8;clip['narration']='voice.wav';clip['narration_origin']=2
    clip['overlays']=[{'start':1,'end':5,'annotation':{'kind':'highlight','points':[10,10,100,100]}}]
    left,right=split_section(clip,3)
    assert (left['start'],left['end'],right['start'],right['end'])==(2,5,5,8)
    assert left['overlays'][0]['end']==3 and right['overlays'][0]['start']==0 and right['overlays'][0]['end']==2
    assert right['narration_origin']==2 and clip['end']==8
    with pytest.raises(ValueError):split_section(clip,6)


def test_invalid_timing_and_paths_are_rejected(tmp_path):
    session=VideoSession.create(tmp_path,'Bounds');session.original='take.mkv';session.duration=10
    clip=legacy_section(session)
    for changes in ({'source':'../outside.mp4'},{'end':11},{'start':float('nan')},{'volume':-1}):
        with pytest.raises(ValueError):validate_timeline(session,[clip|changes])
    with pytest.raises(ValueError):validate_timeline(session,[clip|{'overlays':[{'start':0,'end':99,'annotation':{'points':[0,0,1,1]}}]}])


def test_card_and_timed_overlay_share_rendering(tmp_path):
    session=VideoSession.create(tmp_path,'Cards')
    card={'kind':'card','title':'Training','text':'Credits: Operator','duration':2,'background':'#123456','foreground':'#ffffff','logo':None,'overlays':[]}
    validate_timeline(session,[card]);assert section_duration(card)==2
    image=render_card(session,card);assert image.size==(1280,720) and image.getpixel((0,0))[:3]==(18,52,86)
    clip={'overlays':[{'start':1,'end':2,'annotation':{'kind':'highlight','points':[10,10,100,100],'color':'#ff0000','width':4}}]}
    before=render_overlays(Image.new('RGB',(1280,720),'white'),clip,.5)
    during=render_overlays(Image.new('RGB',(1280,720),'white'),clip,1.5)
    assert before.getpixel((10,10))==(255,255,255)
    assert during.crop((5,5,105,105)).tobytes()!=before.crop((5,5,105,105)).tobytes()


def test_edited_session_uses_new_schema_so_older_app_cannot_drop_timeline(tmp_path):
    import json
    session=VideoSession.create(tmp_path,'Schema');assert json.loads((session.root/'video.json').read_text())['schema_version']==1
    session.original='take.mp4';session.duration=3;session.timeline=[legacy_section(session)];session.save()
    assert json.loads((session.root/'video.json').read_text())['schema_version']==2
    assert VideoSession.load(session.root).timeline==session.timeline
