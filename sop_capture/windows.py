"""Documented Win32 APIs. Never reads desktop pixels or keyboard text."""
import ctypes as C
from ctypes import wintypes as W
from dataclasses import dataclass
import multiprocessing as mp
import os
from pathlib import Path
import queue
import threading

from PIL import Image, ImageStat


@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    pid: int
    title: str
    application: str


def _api():
    if os.name != "nt":
        raise RuntimeError("Live capture requires Windows 10/11")
    u = C.WinDLL("user32", use_last_error=True)
    k = C.WinDLL("kernel32", use_last_error=True)
    g = C.WinDLL("gdi32", use_last_error=True)
    def bind(lib, name, result, *args):
        fn = getattr(lib, name)
        fn.restype, fn.argtypes = result, list(args)
    for name in ("IsWindow", "IsWindowVisible", "IsIconic", "IsHungAppWindow"):
        bind(u, name, W.BOOL, W.HWND)
    bind(u, "GetWindowThreadProcessId", W.DWORD, W.HWND, C.POINTER(W.DWORD))
    bind(u, "GetWindowRect", W.BOOL, W.HWND, C.POINTER(W.RECT))
    bind(u, "GetForegroundWindow", W.HWND)
    bind(u, "GetAncestor", W.HWND, W.HWND, W.UINT)
    bind(u, "WindowFromPoint", W.HWND, W.POINT)
    bind(u, "GetWindowTextLengthW", C.c_int, W.HWND)
    bind(u, "GetWindowTextW", C.c_int, W.HWND, W.LPWSTR, C.c_int)
    bind(u, "GetWindowLongW", C.c_long, W.HWND, C.c_int)
    bind(u, "GetWindowDC", W.HDC, W.HWND)
    bind(u, "ReleaseDC", C.c_int, W.HWND, W.HDC)
    bind(u, "PrintWindow", W.BOOL, W.HWND, W.HDC, W.UINT)
    bind(u, "GetWindowDisplayAffinity", W.BOOL, W.HWND, C.POINTER(W.DWORD))
    bind(u, "SetWindowDisplayAffinity", W.BOOL, W.HWND, W.DWORD)
    bind(u, "SetForegroundWindow", W.BOOL, W.HWND)
    bind(k, "OpenProcess", W.HANDLE, W.DWORD, W.BOOL, W.DWORD)
    bind(k, "CloseHandle", W.BOOL, W.HANDLE)
    bind(k, "QueryFullProcessImageNameW", W.BOOL, W.HANDLE, W.DWORD, W.LPWSTR, C.POINTER(W.DWORD))
    bind(k, "GetCurrentThreadId", W.DWORD)
    bind(k, "GetModuleHandleW", W.HMODULE, W.LPCWSTR)
    bind(g, "CreateCompatibleDC", W.HDC, W.HDC)
    bind(g, "CreateCompatibleBitmap", W.HBITMAP, W.HDC, C.c_int, C.c_int)
    bind(g, "SelectObject", W.HANDLE, W.HDC, W.HANDLE)
    bind(g, "DeleteObject", W.BOOL, W.HANDLE)
    bind(g, "DeleteDC", W.BOOL, W.HDC)
    bind(g, "GetDIBits", C.c_int, W.HDC, W.HBITMAP, W.UINT, W.UINT, C.c_void_p, C.c_void_p, W.UINT)
    return u, k, g


def enable_dpi_awareness():
    if os.name == "nt":
        try:
            u = C.WinDLL("user32", use_last_error=True)
            u.SetProcessDpiAwarenessContext.argtypes = [C.c_void_p]
            u.SetProcessDpiAwarenessContext(C.c_void_p(-4))
        except (AttributeError, OSError):
            pass  # Qt / executable manifest may have already established awareness.


def _render(hwnd):
    enable_dpi_awareness()
    u, _, g = _api()
    rect = W.RECT()
    if not u.GetWindowRect(hwnd, C.byref(rect)):
        raise RuntimeError("Window bounds unavailable")
    width, height = rect.right - rect.left, rect.bottom - rect.top
    if width <= 0 or height <= 0 or width * height > 50_000_000:
        raise RuntimeError("Window dimensions are unsupported")
    source, memory, bitmap, old = None, None, None, None
    try:
        source = u.GetWindowDC(hwnd)
        memory = g.CreateCompatibleDC(source)
        bitmap = g.CreateCompatibleBitmap(source, width, height)
        if not all((source, memory, bitmap)):
            raise RuntimeError("Cannot allocate window capture resources")
        old = g.SelectObject(memory, bitmap)
        if not u.PrintWindow(hwnd, memory, 2):  # PW_RENDERFULLCONTENT, window only.
            raise RuntimeError("This application does not support window rendering")
        class Header(C.Structure):
            _fields_ = [("size", W.DWORD), ("width", W.LONG), ("height", W.LONG), ("planes", W.WORD), ("bits", W.WORD), ("compression", W.DWORD), ("image_size", W.DWORD), ("xppm", W.LONG), ("yppm", W.LONG), ("used", W.DWORD), ("important", W.DWORD)]
        header = Header(C.sizeof(Header), width, -height, 1, 32, 0, 0, 0, 0, 0, 0)
        data = C.create_string_buffer(width * height * 4)
        g.SelectObject(memory, old)
        old = None
        if g.GetDIBits(memory, bitmap, 0, height, data, C.byref(header), 0) != height:
            raise RuntimeError("Window pixel read failed")
        return (width, height), data.raw, (rect.left, rect.top, rect.right, rect.bottom)
    finally:
        if old:
            g.SelectObject(memory, old)
        if bitmap:
            g.DeleteObject(bitmap)
        if memory:
            g.DeleteDC(memory)
        if source:
            u.ReleaseDC(hwnd, source)


def _render_worker(connection):
    try:
        while True:
            hwnd = connection.recv()
            if hwnd is None:
                break
            try:
                connection.send((True, _render(hwnd)))
            except Exception as exc:
                connection.send((False, str(exc)))
    except (EOFError, BrokenPipeError):
        pass
    finally:
        connection.close()


class WindowsBackend:
    def __init__(self):
        self.u, self.k, self.g = _api()
        self._lock = threading.Lock()
        self._process = self._connection = None

    def list_windows(self):
        result = []
        callback_type = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
        def visit(hwnd, _):
            pid = W.DWORD()
            self.u.GetWindowThreadProcessId(hwnd, C.byref(pid))
            if not self.u.IsWindowVisible(hwnd) or pid.value == os.getpid() or self.u.GetWindowLongW(hwnd, -20) & 0x80:
                return True
            length = self.u.GetWindowTextLengthW(hwnd)
            if not length:
                return True
            title = C.create_unicode_buffer(length + 1)
            self.u.GetWindowTextW(hwnd, title, len(title))
            application = f"Process {pid.value}"
            handle = self.k.OpenProcess(0x1000, False, pid.value)
            if handle:
                try:
                    name, size = C.create_unicode_buffer(32768), W.DWORD(32768)
                    if self.k.QueryFullProcessImageNameW(handle, 0, name, C.byref(size)):
                        application = Path(name.value).name
                finally:
                    self.k.CloseHandle(handle)
            result.append(WindowInfo(int(hwnd), pid.value, title.value, application))
            return True
        callback = callback_type(visit)
        self.u.EnumWindows.argtypes = [callback_type, W.LPARAM]
        self.u.EnumWindows(callback, 0)
        return sorted(result, key=lambda x: (x.application.casefold(), x.title.casefold()))

    def validate(self, target, foreground=True):
        pid = W.DWORD()
        self.u.GetWindowThreadProcessId(target.hwnd, C.byref(pid))
        if not self.u.IsWindow(target.hwnd) or pid.value != target.pid or target.pid == os.getpid():
            raise RuntimeError("Selected window closed or changed identity; select it again")
        if not self.u.IsWindowVisible(target.hwnd) or self.u.IsIconic(target.hwnd):
            raise RuntimeError("Selected window is hidden or minimized")
        if self.u.IsHungAppWindow(target.hwnd):
            raise RuntimeError("Selected application is not responding")
        affinity = W.DWORD()
        if self.u.GetWindowDisplayAffinity(target.hwnd, C.byref(affinity)) and affinity.value:
            raise RuntimeError("Selected window is protected from capture")
        if foreground and self.u.GetAncestor(self.u.GetForegroundWindow(), 2) != target.hwnd:
            raise RuntimeError("Selected window is not foreground; capture skipped")
        rect = W.RECT()
        if not self.u.GetWindowRect(target.hwnd, C.byref(rect)):
            raise RuntimeError("Cannot read selected window bounds")
        return rect.left, rect.top, rect.right, rect.bottom

    def owns_point(self, target, point):
        hwnd = self.u.WindowFromPoint(W.POINT(*point))
        return self.u.GetAncestor(hwnd, 2) == target.hwnd

    def activate(self, target):
        self.validate(target, foreground=False)
        return bool(self.u.SetForegroundWindow(target.hwnd))

    def exclude(self, hwnd):
        return bool(self.u.SetWindowDisplayAffinity(hwnd, 0x11))

    def capture(self, target, foreground=True):
        with self._lock:
            before = self.validate(target, foreground)
            if self._process is None or not self._process.is_alive():
                self._dispose()
                context = mp.get_context("spawn")
                self._connection, child = context.Pipe()
                self._process = context.Process(target=_render_worker, args=(child,), daemon=True)
                self._process.start()
                child.close()
            try:
                self._connection.send(target.hwnd)
                if not self._connection.poll(4):
                    raise RuntimeError("Window rendering timed out; target may not support capture")
                success, result = self._connection.recv()
                if not success:
                    raise RuntimeError(result)
            except (OSError, EOFError, RuntimeError):
                self._dispose()
                raise
            after = self.validate(target, foreground)
            size, data, bounds = result
            if before != after or tuple(bounds) != after:
                raise RuntimeError("Window moved during capture; try again")
            image = Image.frombytes("RGB", size, data, "raw", "BGRX")
            stats = ImageStat.Stat(image.resize((64, 64)))
            if max(stats.stddev) < .3:
                raise RuntimeError("Window returned a blank image; use another supported window")
            return image, bounds

    def _dispose(self):
        if self._process:
            if self._process.is_alive():
                self._process.terminate()
            self._process.join(timeout=2)
        if self._connection:
            self._connection.close()
        self._process = self._connection = None

    def close(self):
        with self._lock:
            self._dispose()


def parse_hotkey(text):
    parts = text.upper().replace(" ", "").split("+")
    modifiers = 0x4000  # MOD_NOREPEAT
    mapping = {"CTRL": 2, "CONTROL": 2, "ALT": 1, "SHIFT": 4, "WIN": 8}
    for token in parts[:-1]:
        if token not in mapping:
            raise ValueError("Use Ctrl, Alt, Shift or Win modifiers")
        modifiers |= mapping[token]
    key = parts[-1]
    if len(key) == 1 and key.isascii() and key.isalnum():
        code = ord(key)
    elif key.startswith("F") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        code = 0x6F + int(key[1:])
    else:
        raise ValueError("Shortcut key must be a letter, digit or F1–F24")
    if modifiers == 0x4000:
        raise ValueError("Use at least one modifier")
    return modifiers, code


class NativeInput:
    def __init__(self, on_mouse, on_manual, before_click=False):
        self.on_mouse, self.on_manual = on_mouse, on_manual
        self.before_click = before_click
        self.ready = threading.Event()
        self.error = None
        self.thread = None
        self.thread_id = 0

    def start(self, shortcut="Ctrl+Shift+F8"):
        self.hotkey = parse_hotkey(shortcut)
        self.thread = threading.Thread(target=self._run, name="Windows input", daemon=True)
        self.thread.start()
        if not self.ready.wait(5):
            raise RuntimeError("Windows input thread did not start")
        if self.error:
            self.stop()
            raise RuntimeError(self.error)

    def _run(self):
        u, k, _ = _api()
        pointer_int = C.c_ssize_t
        hook_type = C.WINFUNCTYPE(pointer_int, C.c_int, W.WPARAM, W.LPARAM)
        u.SetWindowsHookExW.argtypes = [C.c_int, hook_type, W.HINSTANCE, W.DWORD]
        u.SetWindowsHookExW.restype = W.HHOOK
        u.CallNextHookEx.argtypes = [W.HHOOK, C.c_int, W.WPARAM, W.LPARAM]
        u.CallNextHookEx.restype = pointer_int
        u.UnhookWindowsHookEx.argtypes = [W.HHOOK]
        u.RegisterHotKey.argtypes = [W.HWND, C.c_int, W.UINT, W.UINT]
        u.GetMessageW.argtypes = [C.POINTER(W.MSG), W.HWND, W.UINT, W.UINT]
        class Mouse(C.Structure):
            _fields_ = [("point", W.POINT), ("data", W.DWORD), ("flags", W.DWORD), ("time", W.DWORD), ("extra", C.c_size_t)]
        down = {0x201: "left", 0x204: "right", 0x207: "middle"}
        buttons = down if self.before_click else {key+1: value for key, value in down.items()}
        self.events = queue.SimpleQueue()
        def hook(code, message, payload):
            if code >= 0 and message in buttons:
                mouse = C.cast(payload, C.POINTER(Mouse)).contents
                self.events.put(((mouse.point.x, mouse.point.y), buttons[message]))
                u.PostThreadMessageW(self.thread_id, 0x8001, 0, 0)
            return u.CallNextHookEx(None, code, message, payload)
        self.callback = hook_type(hook)
        handle = None
        registered = False
        try:
            self.thread_id = k.GetCurrentThreadId()
            msg = W.MSG()
            u.PeekMessageW(C.byref(msg), None, 0, 0, 0)
            registered = bool(u.RegisterHotKey(None, 1, *self.hotkey))
            if not registered:
                raise RuntimeError("Manual shortcut is unavailable; change it in Settings")
            handle = u.SetWindowsHookExW(14, self.callback, k.GetModuleHandleW(None), 0)
            if not handle:
                raise RuntimeError("Cannot install mouse monitoring hook")
            self.ready.set()
            while u.GetMessageW(C.byref(msg), None, 0, 0) > 0:
                if msg.message == 0x312:
                    self.on_manual()
                elif msg.message == 0x8001:
                    while not self.events.empty():
                        point, button = self.events.get()
                        self.on_mouse(point, button)
        except Exception as exc:
            self.error = str(exc)
            self.ready.set()
        finally:
            if handle:
                u.UnhookWindowsHookEx(handle)
            if registered:
                u.UnregisterHotKey(None, 1)

    def stop(self):
        if self.thread and self.thread.is_alive():
            u, _, _ = _api()
            u.PostThreadMessageW(self.thread_id, 0x12, 0, 0)
            self.thread.join(timeout=3)
            if self.thread.is_alive():
                raise RuntimeError("Input monitoring has not shut down")
