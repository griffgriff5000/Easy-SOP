import time
from PIL import Image

from sop_capture.capture import CaptureSession, CaptureOptions
from sop_capture.windows import WindowInfo


class Backend:
    focused = True
    def validate(self, target, foreground=True):
        if foreground and not self.focused:
            raise RuntimeError("Target is not foreground")
        return (0, 0, 200, 100)
    def capture(self, target, foreground=True):
        bounds = self.validate(target, foreground)
        return Image.new("RGB", (200, 100), "white"), bounds


def session(options=None):
    results, errors = [], []
    backend = Backend()
    capture = CaptureSession(backend, results.append, errors.append)
    capture.start(WindowInfo(123, 456, "Example", "example.exe"), options or CaptureOptions(delay_ms=30))
    return capture, backend, results, errors


def test_delayed_focus_change_discards_capture():
    s, b, results, errors = session()
    s.trigger((50, 30), "left")
    b.focused = False
    s.stop()
    assert not results
    assert errors


def test_stop_drains_accepted_click_and_maps_marker():
    s, b, results, errors = session()
    s.trigger((50, 30), "left")
    s.stop()
    assert len(results) == 1
    assert results[0].marker == (50, 30)
    assert results[0].button == "left"
    assert not errors
    s.trigger((40, 20), "left")
    assert len(results) == 1


def test_pause_invalidates_pending_and_resume_manual():
    s, b, results, errors = session(CaptureOptions(delay_ms=150))
    s.trigger((50, 30), "left")
    s.pause()
    time.sleep(.2)
    assert not results
    s.resume()
    s.manual()
    s.stop()
    assert len(results) == 1
    assert results[0].marker is None


def test_preclick_uses_cached_frame():
    s, b, results, errors = session(CaptureOptions(before_click=True))
    time.sleep(.2)
    s.trigger((50, 30), "left")
    s.stop()
    assert len(results) == 1
    assert results[0].frame_age_ms >= 0


def test_buttons_and_outside_target_ignored():
    s, b, results, errors = session()
    s.trigger((50, 30), "right")
    s.trigger((250, 30), "left")
    s.stop()
    assert not results
