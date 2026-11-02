import time
from PySide6.QtWidgets import QApplication
from sop_capture.training_video import VideoSession
from sop_capture.video_timeline import legacy_section
from sop_capture.sequence_export import SequenceExport,section_arguments


def test_video_render_plan_normalizes_silent_audio_and_voice_alignment(tmp_path):
    session=VideoSession.create(tmp_path,'Export');session.original='source.mkv';session.duration=8
    clip=legacy_section(session);clip.update(start=3,end=7,narration='voice.wav',narration_origin=2,use_narration=True)
    args=section_arguments(session,clip,tmp_path,tmp_path/'clip.mp4',has_audio=False)
    assert 'anullsrc=r=48000:cl=stereo' in args
    assert '1' in args and '1280' in ' '.join(args)
    assert '-filter_complex' in args and 'apad' in ' '.join(args)
    assert args[-1]==str(tmp_path/'clip.mp4')


def test_sequence_failure_retains_existing_output_and_sources(qt_application,tmp_path):
    session=VideoSession.create(tmp_path,'Failure');session.original='broken.mkv';session.duration=2
    session.asset(session.original).write_bytes(b'original');session.timeline=[legacy_section(session)]
    output=tmp_path/'output.mp4';output.write_bytes(b'previous')
    job=SequenceExport();results=[];job.finished.connect(lambda path,error:results.append(error))
    job.start(session,output);deadline=time.monotonic()+15
    while not results and time.monotonic()<deadline:QApplication.processEvents();time.sleep(.02)
    assert results and results[0]
    assert output.read_bytes()==b'previous' and session.asset(session.original).read_bytes()==b'original'
    assert not job.busy and not list(tmp_path.glob('.sop-sequence-*'))


def test_cancel_sequence_keeps_existing_destination(qt_application,tmp_path):
    session=VideoSession.create(tmp_path,'Cancelled')
    session.timeline=[dict(kind='card',title='Title',text='Test',duration=120,background='#ffffff',foreground='#000000',logo=None,overlays=[])]
    output=tmp_path/'existing.mp4';output.write_bytes(b'previous')
    job=SequenceExport();results=[];job.finished.connect(lambda path,error:results.append(error))
    job.start(session,output);job.cancel();deadline=time.monotonic()+15
    while not results and time.monotonic()<deadline:QApplication.processEvents();time.sleep(.02)
    assert results and 'cancelled' in str(results[0]).lower()
    assert not job.busy and output.read_bytes()==b'previous' and not list(tmp_path.glob('.sop-sequence-*'))
