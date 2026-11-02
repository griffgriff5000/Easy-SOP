import time
from PySide6.QtWidgets import QApplication
from sop_capture.training_video import VideoSession
from sop_capture.media_export import VideoExport


def test_failed_export_keeps_existing_output_and_original(qt_application,tmp_path):
    video=VideoSession.create(tmp_path,'Failed export');video.original='broken.mkv';video.duration=3
    video.asset(video.original).write_bytes(b'not a video')
    output=tmp_path/'existing.mp4';output.write_bytes(b'previous successful export')
    job=VideoExport();results=[];job.finished.connect(lambda path,error:results.append((path,error)))
    job.start(video,output)
    deadline=time.monotonic()+15
    while not results and time.monotonic()<deadline:QApplication.processEvents();time.sleep(.01)
    assert results and results[0][1] is not None
    assert output.read_bytes()==b'previous successful export'
    assert video.asset(video.original).read_bytes()==b'not a video'
    assert not list(tmp_path.glob('.sop-video-*'))
    assert not job.busy
    job.deleteLater()
