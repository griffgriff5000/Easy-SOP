import time
import threading
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


def test_cache_capture_crossing_pause_resume_is_discarded():
    entered, release = threading.Event(), threading.Event()
    class SlowBackend(Backend):
        def capture(self, target, foreground=True):
            entered.set()
            release.wait(2)
            return Image.new("RGB", (200, 100), "red"), (0, 0, 200, 100)
    results, errors = [], []
    s = CaptureSession(SlowBackend(), results.append, errors.append)
    s.start(WindowInfo(123, 456, "Example", "example.exe"), CaptureOptions(before_click=True))
    assert entered.wait(1)
    s.pause()
    s.resume()
    release.set()
    time.sleep(.03)
    s.trigger((20, 20), "left")
    s.stop()
    assert not results


def test_native_event_from_previous_epoch_or_other_window_is_discarded():
    from sop_capture.windows import MouseEvent
    s, b, results, errors = session()
    epoch = s.input_context()
    event = MouseEvent(time.monotonic(), "2026-10-26T10:00:00+00:00", 123, 123, epoch)
    s.pause()
    s.resume()
    s.trigger((20, 20), "left", event)
    foreign = MouseEvent(time.monotonic(), "2026-10-26T10:00:00+00:00", 999, 999, s.input_context())
    s.trigger((20, 20), "left", foreign)
    s.stop()
    assert not results


def test_preclick_frame_newer_than_event_is_rejected():
    from sop_capture.windows import MouseEvent
    s, b, results, errors = session(CaptureOptions(before_click=True))
    occurred = time.monotonic()
    time.sleep(.2)
    event = MouseEvent(occurred, "2026-10-26T10:00:00+00:00", 123, 123, s.input_context())
    s.trigger((20, 20), "left", event)
    s.stop()
    assert not results


def test_bounded_queue_reports_overload_without_dropping_accepted_work():
    entered, release = threading.Event(), threading.Event()
    class BlockingBackend(Backend):
        def capture(self, target, foreground=True):
            entered.set()
            release.wait(2)
            return super().capture(target, foreground)
    results, errors = [], []
    s = CaptureSession(BlockingBackend(), results.append, errors.append)
    s.start(WindowInfo(123, 456, "Example", "example.exe"), CaptureOptions(delay_ms=0, max_queue=1))
    s.manual()
    assert entered.wait(1)
    s.manual()
    s.manual()
    release.set()
    s.stop()
    assert len(results) == 2
    assert any("queue is full" in error.lower() for error in errors)
