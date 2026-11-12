"""Thin ctypes wrapper around Win32 input APIs."""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes

from ..i18n import tr
from .vkeys import normalize_vk

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
else:  # pragma: no cover - the app targets Windows, this only keeps imports safe
    user32 = None
    kernel32 = None

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

# ---------------------------------------------------------------- structures
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

EXTENDED_KEYS = {
    0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28,  # pgup pgdn end home arrows
    0x2D, 0x2E,                                      # insert delete
    0x5B, 0x5C, 0x5D,                                # win, win, apps
    0x6F, 0x90, 0x91,                                # numpad divide, numlock, scrolllock
    0xA3, 0xA5,                                      # right ctrl / right alt
}

if IS_WINDOWS:

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", wintypes.LONG),
            ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [
            ("uMsg", wintypes.DWORD),
            ("wParamL", wintypes.WORD),
            ("wParamH", wintypes.WORD),
        ]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

    user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    user32.SendInput.restype = wintypes.UINT
    user32.SetCursorPos.argtypes = (ctypes.c_int, ctypes.c_int)
    user32.SetCursorPos.restype = wintypes.BOOL
    user32.GetCursorPos.argtypes = (ctypes.POINTER(wintypes.POINT),)
    user32.GetCursorPos.restype = wintypes.BOOL
    user32.GetSystemMetrics.argtypes = (ctypes.c_int,)
    user32.GetSystemMetrics.restype = ctypes.c_int

_BUTTON_FLAGS = {
    "left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
    "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
    "middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
}


# --------------------------------------------------------------------- setup
def enable_dpi_awareness() -> None:
    """Opt into per-monitor DPI awareness so coordinates match the screen."""
    if not IS_WINDOWS:
        return
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # PER_MONITOR_AWARE_V2
        return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.WinDLL("shcore").SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def cursor_pos() -> tuple[int, int]:
    point = wintypes.POINT()
    if IS_WINDOWS and user32.GetCursorPos(ctypes.byref(point)):
        return int(point.x), int(point.y)
    return 0, 0


def set_cursor_pos(x: int, y: int) -> None:
    if IS_WINDOWS:
        user32.SetCursorPos(int(x), int(y))


def get_foreground_window_title() -> str:
    """Возвращает заголовок активного окна (или пустую строку)."""
    if not IS_WINDOWS:
        return ""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd) + 1
    buffer = ctypes.create_unicode_buffer(length)
    user32.GetWindowTextW(hwnd, buffer, length)
    return buffer.value


def get_open_windows() -> list[tuple[int, str]]:
    """Возвращает список открытых окон: [(hwnd, title), ...] с непустым заголовком."""
    if not IS_WINDOWS:
        return []
    result: list[tuple[int, str]] = []

    def callback(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd) + 1
            if length > 1:
                buffer = ctypes.create_unicode_buffer(length)
                user32.GetWindowTextW(hwnd, buffer, length)
                title = buffer.value.strip()
                if title:
                    result.append((hwnd, title))
        return True

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
    user32.EnumWindows.restype = ctypes.c_bool
    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return result






def screen_size() -> tuple[int, int]:
    if not IS_WINDOWS:
        return 1920, 1080
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


# ------------------------------------------------------------------- sending
def _send(*inputs: "INPUT") -> None:
    if not IS_WINDOWS:
        return
    count = len(inputs)
    array = (INPUT * count)(*inputs)
    user32.SendInput(count, array, ctypes.sizeof(INPUT))


def _mouse_input(flags: int) -> "INPUT":
    item = INPUT()
    item.type = INPUT_MOUSE
    item.mi = MOUSEINPUT(0, 0, 0, flags, 0, 0)
    return item


def _key_input(vk: int, up: bool) -> "INPUT":
    item = INPUT()
    item.type = INPUT_KEYBOARD
    flags = KEYEVENTF_KEYUP if up else 0
    if vk in EXTENDED_KEYS:
        flags |= KEYEVENTF_EXTENDEDKEY
    scan = user32.MapVirtualKeyW(vk, 0) if IS_WINDOWS else 0
    item.ki = KEYBDINPUT(vk, scan, flags, 0, 0)
    return item


def mouse_down(button: str = "left") -> None:
    down, _ = _BUTTON_FLAGS.get(button, _BUTTON_FLAGS["left"])
    _send(_mouse_input(down))


def mouse_up(button: str = "left") -> None:
    _, up = _BUTTON_FLAGS.get(button, _BUTTON_FLAGS["left"])
    _send(_mouse_input(up))


def mouse_wheel(delta: int) -> None:
    """Scroll the wheel; `delta` uses the Win32 convention (120 = one notch)."""
    if not IS_WINDOWS:
        return
    item = INPUT()
    item.type = INPUT_MOUSE
    item.mi = MOUSEINPUT(0, 0, int(delta) & 0xFFFFFFFF, 0x0800, 0, 0)  # MOUSEEVENTF_WHEEL
    _send(item)


def click(button: str = "left", hold: float = 0.0) -> None:
    mouse_down(button)
    if hold > 0:
        time.sleep(hold)
    mouse_up(button)


def key_down(vk: int) -> None:
    _send(_key_input(int(vk), False))


def key_up(vk: int) -> None:
    _send(_key_input(int(vk), True))


def press_key(vk: int, hold: float = 0.0) -> None:
    key_down(vk)
    if hold > 0:
        time.sleep(hold)
    key_up(vk)


def vk_name(vk: int) -> str:
    code = normalize_vk(vk)
    return VK_NAMES.get(code, f"VK{code:02X}")


# ----------------------------------------------------------------- key names
_MODIFIERS = {
    0x10: "Shift", 0x11: "Ctrl", 0x12: "Alt", 0x5B: "Win", 0x5C: "Win",
    0xA0: "Shift", 0xA1: "Shift",
    0xA2: "Ctrl", 0xA3: "Ctrl",
    0xA4: "Alt", 0xA5: "Alt",
}

VK_NAMES: dict[int, str] = {
    **_MODIFIERS,
    0x05: "XButton1",   # side button back
    0x06: "XButton2",   # side button forward
    0x08: "Backspace", 0x09: "Tab", 0x0D: "Enter", 0x13: "Pause", 0x14: "CapsLock",
    0x1B: "Esc", 0x20: "Space", 0x21: "PgUp", 0x22: "PgDn", 0x23: "End", 0x24: "Home",
    0x25: "←", 0x26: "↑", 0x27: "→", 0x28: "↓", 0x2C: "PrtSc", 0x2D: "Insert",
    0x2E: "Delete", 0x90: "NumLock", 0x91: "ScrollLock",
    0xBA: ";", 0xBB: "=", 0xBC: ",", 0xBD: "-", 0xBE: ".", 0xBF: "/", 0xC0: "`",
    0xDB: "[", 0xDC: "\\", 0xDD: "]", 0xDE: "'",
}
for _i in range(26):
    VK_NAMES[0x41 + _i] = chr(0x41 + _i)
for _i in range(10):
    VK_NAMES[0x30 + _i] = str(_i)
for _i in range(1, 25):
    VK_NAMES[0x6F + _i] = f"F{_i}"
for _i in range(10):
    VK_NAMES[0x60 + _i] = f"Num{_i}"
VK_NAMES.update({0x6A: "Num*", 0x6B: "Num+", 0x6D: "Num-", 0x6E: "Num.", 0x6F: "Num/"})


def combo_label(vks: list[int] | tuple[int, ...] | None) -> str:
    if not vks:
        return ""
    codes: list[int] = []
    for value in vks:
        code = normalize_vk(value)
        if code not in codes:
            codes.append(code)
    order = {0x11: 0, 0x10: 1, 0x12: 2, 0x5B: 3, 0x5C: 3}
    ordered = sorted(codes, key=lambda code: (order.get(code, 9), code))
    names = []
    for code in ordered:
        name = VK_NAMES.get(code, f"VK{code:02X}")
        if code == 0x05:
            name = tr("mouse.x1")
        elif code == 0x06:
            name = tr("mouse.x2")
        names.append(name)
    return " + ".join(names)
