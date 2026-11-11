"""Low level global input hooks (keyboard + mouse) with optional blocking."""

from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes

from .winapi import IS_WINDOWS, kernel32, user32

WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_MOUSEWHEEL = 0x020A
WM_MOUSEHWHEEL = 0x020E
WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP = 0x020C
WM_XBUTTONDBLCLK = 0x020D

WM_QUIT = 0x0012
LLKHF_INJECTED = 0x10
LLMHF_INJECTED = 0x01

XBUTTON1 = 1
XBUTTON2 = 2

MOUSE_KINDS = {
    WM_MOUSEMOVE: "move",
    WM_LBUTTONDOWN: "left_down",
    WM_LBUTTONUP: "left_up",
    WM_RBUTTONDOWN: "right_down",
    WM_RBUTTONUP: "right_up",
    WM_MBUTTONDOWN: "middle_down",
    WM_MBUTTONUP: "middle_up",
    WM_XBUTTONDOWN: "x1_down",
    WM_XBUTTONUP: "x1_up",
    WM_XBUTTONDBLCLK: "x1_dbl",
    WM_MOUSEWHEEL: "wheel",
    WM_MOUSEHWHEEL: "hwheel",
}

KeyCallback = "callable(vk: int, down: bool, injected: bool, ts: float) -> bool"
MouseCallback = "callable(kind: str, x: int, y: int, delta: int, injected: bool, ts: float) -> bool"

if IS_WINDOWS:

    class KBDLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [
            ("vkCode", wintypes.DWORD),
            ("scanCode", wintypes.DWORD),
            ("flags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.c_void_p),
        ]

    class MSLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [
            ("pt", wintypes.POINT),
            ("mouseData", wintypes.DWORD),
            ("flags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.c_void_p),
        ]

    LRESULT = ctypes.c_ssize_t
    LowLevelProc = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

    user32.SetWindowsHookExW.argtypes = (
        ctypes.c_int, LowLevelProc, ctypes.c_void_p, wintypes.DWORD
    )
    user32.SetWindowsHookExW.restype = ctypes.c_void_p
    user32.CallNextHookEx.argtypes = (ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
    user32.CallNextHookEx.restype = LRESULT
    user32.UnhookWindowsHookEx.argtypes = (ctypes.c_void_p,)
    user32.UnhookWindowsHookEx.restype = wintypes.BOOL
    user32.GetMessageW.argtypes = (ctypes.POINTER(wintypes.MSG), ctypes.c_void_p, wintypes.UINT, wintypes.UINT)
    user32.GetMessageW.restype = ctypes.c_int
    user32.PostThreadMessageW.argtypes = (wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    kernel32.GetModuleHandleW.argtypes = (wintypes.LPCWSTR,)
    kernel32.GetModuleHandleW.restype = ctypes.c_void_p


class _HookThread(threading.Thread):
    """Owns one low level hook and pumps its message loop."""

    def __init__(self, hook_type: int, handler) -> None:
        super().__init__(daemon=True, name=f"hook-{hook_type}")
        self.hook_type = hook_type
        self.handler = handler
        self._hook: int | None = None
        self._proc = None
        self._thread_id: int | None = None
        self._ready = threading.Event()

    def run(self) -> None:  # pragma: no cover - runs on the hook thread
        if not IS_WINDOWS:
            return
        self._thread_id = kernel32.GetCurrentThreadId()
        self._proc = LowLevelProc(self._dispatch)
        self._hook = user32.SetWindowsHookExW(
            self.hook_type, self._proc, kernel32.GetModuleHandleW(None), 0
        )
        self._ready.set()
        message = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))
        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None

    def _dispatch(self, code, wparam, lparam):  # pragma: no cover - native callback
        if code >= 0:
            try:
                if self.handler(int(wparam), int(lparam)):
                    return 1
            except Exception:
                pass
        return user32.CallNextHookEx(None, code, wparam, lparam)

    def stop(self) -> None:
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        self.join(timeout=1.0)


class InputHub:
    """Single owner of the global hooks; dispatches to any number of listeners."""

    def __init__(self) -> None:
        self._key_listeners: list = []
        self._mouse_listeners: list = []
        self._lock = threading.RLock()
        self._keyboard_hook: _HookThread | None = None
        self._mouse_hook: _HookThread | None = None
        self._started = False

    # ------------------------------------------------------------ listeners
    def add_key_listener(self, callback) -> None:
        with self._lock:
            self._key_listeners.append(callback)

    def remove_key_listener(self, callback) -> None:
        with self._lock:
            if callback in self._key_listeners:
                self._key_listeners.remove(callback)

    def add_mouse_listener(self, callback) -> None:
        with self._lock:
            self._mouse_listeners.append(callback)

    def remove_mouse_listener(self, callback) -> None:
        with self._lock:
            if callback in self._mouse_listeners:
                self._mouse_listeners.remove(callback)

    # --------------------------------------------------------------- start
    def start(self) -> None:
        if self._started or not IS_WINDOWS:
            return
        self._started = True
        self._keyboard_hook = _HookThread(WH_KEYBOARD_LL, self._on_key)
        self._keyboard_hook.start()
        self._mouse_hook = _HookThread(WH_MOUSE_LL, self._on_mouse)
        self._mouse_hook.start()
        self._keyboard_hook._ready.wait(1.0)
        self._mouse_hook._ready.wait(1.0)

    def stop(self) -> None:
        for hook in (self._keyboard_hook, self._mouse_hook):
            if hook is not None:
                hook.stop()
        self._keyboard_hook = None
        self._mouse_hook = None
        self._started = False

    # ------------------------------------------------------------ dispatch
    def _on_key(self, wparam: int, lparam: int) -> bool:
        info = KBDLLHOOKSTRUCT.from_address(lparam)
        down = wparam in (WM_KEYDOWN, WM_SYSKEYDOWN)
        injected = bool(info.flags & LLKHF_INJECTED)
        vk = int(info.vkCode)
        now = time.perf_counter()
        block = False
        with self._lock:
            listeners = list(self._key_listeners)
        for callback in listeners:
            try:
                if callback(vk, down, injected, now):
                    block = True
            except Exception:
                continue
        return block

    def _on_mouse(self, wparam: int, lparam: int) -> bool:
        info = MSLLHOOKSTRUCT.from_address(lparam)
        kind = MOUSE_KINDS.get(wparam)
        if kind is None:
            return False
        injected = bool(info.flags & LLMHF_INJECTED)
        delta = ctypes.c_short((info.mouseData >> 16) & 0xFFFF).value
        now = time.perf_counter()
        x, y = int(info.pt.x), int(info.pt.y)

        # translate X mouse buttons into virtual key codes so they can be bound
        mouse_vk = None
        if wparam == WM_XBUTTONDOWN:
            xbutton = ctypes.c_short((info.mouseData >> 16) & 0xFFFF).value
            if xbutton == XBUTTON1:
                kind = "x1_down"
                mouse_vk = 0x05  # VK_XBUTTON1
            elif xbutton == XBUTTON2:
                kind = "x2_down"
                mouse_vk = 0x06  # VK_XBUTTON2
            else:
                kind = "x_down"
        elif wparam == WM_XBUTTONUP:
            xbutton = ctypes.c_short((info.mouseData >> 16) & 0xFFFF).value
            if xbutton == XBUTTON1:
                kind = "x1_up"
                mouse_vk = 0x05
            elif xbutton == XBUTTON2:
                kind = "x2_up"
                mouse_vk = 0x06
            else:
                kind = "x_up"

        block = False
        with self._lock:
            mouse_listeners = list(self._mouse_listeners)
            key_listeners = list(self._key_listeners)

        # Mouse X1/X2 buttons are also delivered to key listeners (capture / hotkeys)
        if mouse_vk is not None:
            for callback in key_listeners:
                try:
                    if callback(mouse_vk, wparam == WM_XBUTTONDOWN, injected, now):
                        block = True
                except Exception:
                    continue

        # Regular mouse events go to mouse listeners
        for callback in mouse_listeners:
            try:
                if callback(kind, x, y, delta, injected, now):
                    block = True
            except Exception:
                continue
        return block
