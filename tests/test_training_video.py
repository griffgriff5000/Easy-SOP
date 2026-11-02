import json
from pathlib import Path
import pytest
from sop_capture.training_video import VideoSession,export_arguments


def session(tmp_path):
    value=VideoSession.create(tmp_path,'Training example')
    value.original='original.mkv';(value.root/value.original).write_bytes(b'original')
    value.duration=10;value.save();return value


def test_sessions_are_independent_and_reopen_with_edits(tmp_path):
    first=session(tmp_path);second=VideoSession.create(tmp_path,'Training example')
    assert first.root!=second.root
    first.trim_start=2;first.trim_end=8;first.volume=.5;first.save()
    loaded=VideoSession.load(first.root)
    assert (loaded.trim_start,loaded.trim_end,loaded.volume)==(2,8,.5)
    assert loaded.asset(loaded.original).read_bytes()==b'original'
    data=json.loads((first.root/'video.json').read_text());data['original']='../outside.mkv'
    (first.root/'video.json').write_text(json.dumps(data))
    with pytest.raises(ValueError):VideoSession.load(first.root)


@pytest.mark.parametrize('name',['original.mp4 ','original.mp4.','NUL.mkv','CON','a\x00.mkv'])
def test_windows_aliases_and_device_names_are_not_video_assets(tmp_path,name):
    value=VideoSession.create(tmp_path,'Safe paths')
    with pytest.raises(ValueError):value.asset(name)


def test_export_trims_both_tracks_and_pads_narration_without_shortening_video(tmp_path):
    value=session(tmp_path);value.narration='voice.wav';(value.root/'voice.wav').write_bytes(b'audio')
    value.use_narration=True;value.trim_start=2;value.trim_end=8;value.volume=.5
    args=export_arguments(value,tmp_path/'output.mp4')
    assert args.count('-ss')==2
    assert args[args.index('-t')+1]=='6'
    assert args[args.index('-map')+1]=='0:v:0'
    assert '1:a:0' in args
    assert 'apad' in args[args.index('-af')+1]
    assert 'volume=0.5' in args[args.index('-af')+1]
    assert '-shortest' not in args
    with pytest.raises(ValueError):export_arguments(value,value.asset(value.original))
    value.trim_end=1
    with pytest.raises(ValueError):export_arguments(value,tmp_path/'output.mp4')
