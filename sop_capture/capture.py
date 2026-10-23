from dataclasses import dataclass, field
import queue
import threading
import time

from .geometry import screen_to_image
from .models import now


@dataclass
class CaptureOptions:
    delay_ms: int = 400
    before_click: bool = False
    buttons: tuple[str, ...] = ("left",)
    max_queue: int = 30


@dataclass
class CaptureResult:
    image: object
    bounds: tuple
    marker: tuple | None
    button: str | None
    timestamp: str
    frame_age_ms: float | None = None


class CaptureSession:
    def __init__(self, backend, on_result, on_error):
        self.backend, self.on_result, self.on_error = backend, on_result, on_error
        self.state = "idle"
        self.lock = threading.RLock()
        self.generation = 0
        self.cache = None

    def start(self, target, options=None):
        if self.state != "idle":
            raise RuntimeError("Capture is already active")
        self.backend.validate(target, foreground=False)
        self.target, self.options = target, options or CaptureOptions()
        self.jobs = queue.Queue(maxsize=self.options.max_queue)
        self.shutdown = threading.Event()
        self.cache = None
        self.state = "recording"
        self.worker = threading.Thread(target=self._work, name="Screenshot worker", daemon=True)
        self.worker.start()

    def pause(self):
        with self.lock:
            if self.state == "recording":
                self.state = "paused"
                self.generation += 1
                self.cache = None

    def resume(self):
        with self.lock:
            if self.state == "paused":
                self.state = "recording"

    def trigger(self, point, button):
        if button not in self.options.buttons:
            return
        self._enqueue(point, button)

    def manual(self):
        self._enqueue(None, None)

    def _enqueue(self, point, button):
        with self.lock:
            if self.state != "recording":
                return
            try:
                bounds = self.backend.validate(self.target)
                if point:
                    if screen_to_image(point, bounds, (bounds[2]-bounds[0], bounds[3]-bounds[1])) is None:
                        return
                    if hasattr(self.backend, "owns_point") and not self.backend.owns_point(self.target, point):
                        return
                cached = self.cache if self.options.before_click and point else None
                if self.options.before_click and point and (cached is None or time.monotonic()-cached[2] > 1):
                    self.on_error("Pre-click frame is not ready; try again after a moment")
                    return
                self.jobs.put_nowait((time.monotonic() + (0 if cached else self.options.delay_ms/1000), self.generation, point, button, bounds, now(), cached))
            except queue.Full:
                self.on_error("Capture queue is full; slow down and try again")
            except Exception:
                # Non-target mouse interactions are deliberately ignored.
                if point is None:
                    self.on_error("Manual capture skipped: selected window must be foreground")

    def _work(self):
        while not self.shutdown.is_set() or not self.jobs.empty():
            try:
                job = self.jobs.get(timeout=.08)
            except queue.Empty:
                if self.options.before_click and self.state == "recording":
                    try:
                        image, bounds = self.backend.capture(self.target)
                        with self.lock:
                            if self.state == "recording":
                                self.cache = (image, bounds, time.monotonic())
                    except Exception:
                        with self.lock:
                            self.cache = None
                continue
            due, generation, point, button, old_bounds, timestamp, cached = job
            try:
                while time.monotonic() < due:
                    if generation != self.generation:
                        break
                    time.sleep(min(.02, max(0, due-time.monotonic())))
                if generation != self.generation:
                    continue
                self.backend.validate(self.target)
                if cached:
                    image, bounds, captured_at = cached
                    age = max(0, (due-captured_at)*1000)
                else:
                    image, bounds = self.backend.capture(self.target)
                    age = None
                marker = None
                if point:
                    relative = screen_to_image(point, old_bounds, (1, 1))
                    if relative:
                        marker = (relative[0]*image.width, relative[1]*image.height)
                with self.lock:
                    if generation == self.generation:
                        self.on_result(CaptureResult(image, bounds, marker, button, timestamp, age))
            except Exception as exc:
                self.on_error(str(exc))
            finally:
                self.jobs.task_done()

    def stop(self):
        with self.lock:
            if self.state == "idle":
                return
            self.state = "stopping"
            self.shutdown.set()
        self.worker.join(timeout=15)
        if self.worker.is_alive():
            raise RuntimeError("Capture is still finishing; wait before closing")
        self.state = "idle"
        self.cache = None
