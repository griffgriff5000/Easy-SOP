from sop_capture.video_recorder import VideoRecorder


def test_constructing_recorder_does_not_start_screen_or_microphone(qt_application):
    recorder=VideoRecorder()
    assert not recorder.busy
    assert recorder.session.audioInput() is None
    assert recorder.session.screenCapture() is None
    assert recorder.session.windowCapture() is None
    recorder.stop()
    assert not recorder.busy
    recorder.deleteLater()
