"""Generate a small pack of ready-to-import Viberium macros (JSON)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from viberium.core.macros import Macro, MacroStore  # noqa: E402

VK = {
    "ENTER": 13,
    "TAB": 9,
    "SPACE": 32,
    "ESC": 27,
    "CTRL": 17,
    "A": 65,
    "C": 67,
    "F5": 116,
}


def click_macro(name: str, count: int, gap: float) -> dict:
    events = []
    t = 0.0
    for _ in range(count):
        events.append({"type": "down", "t": round(t, 3), "button": "left"})
        events.append({"type": "up", "t": round(t + gap / 2, 3), "button": "left"})
        t += gap
    return {"name": name, "duration": round(t, 3), "events": events}


def key_macro(name: str, keys: list[tuple[int, float]], repeat: int = 1, gap: float = 0.12) -> dict:
    events = []
    t = 0.0
    for _ in range(repeat):
        for vk, hold in keys:
            events.append({"type": "key_down", "t": round(t, 3), "vk": vk})
            t += hold
            events.append({"type": "key_up", "t": round(t, 3), "vk": vk})
            t += gap
    return {"name": name, "duration": round(t, 3), "events": events}


def wheel_macro(name: str, count: int, delta: int = -120, gap: float = 0.15) -> dict:
    events = []
    t = 0.0
    for _ in range(count):
        events.append({"type": "wheel", "t": round(t, 3), "delta": delta})
        t += gap
    return {"name": name, "duration": round(t, 3), "events": events}


PACK = [
    click_macro("Клик 50 раз", 50, 0.1),
    key_macro("Enter 10 раз", [(VK["ENTER"], 0.05)], repeat=10, gap=0.1),
    key_macro("Tab 20 раз", [(VK["TAB"], 0.05)], repeat=20, gap=0.08),
    key_macro("Пробел 5 раз", [(VK["SPACE"], 0.05)], repeat=5, gap=0.15),
    key_macro("Ctrl+A затем Ctrl+C", [(VK["CTRL"], 0.05), (VK["A"], 0.05), (VK["CTRL"], 0.05), (VK["C"], 0.05)], gap=0.1),
    wheel_macro("Прокрутка вниз 10 раз", 10),
]


def main() -> None:
    out = ROOT / "telegram" / "macros"
    out.mkdir(parents=True, exist_ok=True)
    for data in PACK:
        macro = Macro.from_dict(data)
        path = out / f"{macro.name}.json"
        path.write_text(json.dumps(macro.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        # verify the app can read it back
        loaded = MacroStore.load_path(path)
        status = "OK" if loaded and loaded.events else "FAIL"
        print(f"{status}  {path.name}  events={len(macro.events)}  duration={macro.duration}s")


if __name__ == "__main__":
    main()
