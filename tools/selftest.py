"""Self-test for the engine, hotkeys, macros and settings (no real clicks)."""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QCoreApplication  # noqa: E402

from viberium.config import Settings  # noqa: E402
from viberium.core import winapi  # noqa: E402
from viberium.core.engine import ClickEngine, normalize_keyboard_combinations  # noqa: E402
from viberium.core.hooks import InputHub  # noqa: E402
from viberium.core.hotkeys import HotkeyManager  # noqa: E402
from viberium.core.macros import Macro, MacroPlayer, MacroStore  # noqa: E402
from viberium.i18n import tr  # noqa: E402

calls: list[tuple] = []


def patch_winapi() -> None:
    winapi.mouse_down = lambda button="left": calls.append(("mouse_down", button))
    winapi.mouse_up = lambda button="left": calls.append(("mouse_up", button))
    winapi.key_down = lambda vk: calls.append(("key_down", vk))
    winapi.key_up = lambda vk: calls.append(("key_up", vk))
    winapi.set_cursor_pos = lambda x, y: calls.append(("move", x, y))
    winapi.mouse_wheel = lambda delta: calls.append(("wheel", delta))
    winapi.cursor_pos = lambda: (100, 100)


def pump(app: QCoreApplication, predicate, timeout: float = 5.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def check(name: str, condition: bool, detail: str = "") -> None:
    status = "OK " if condition else "FAIL"
    print(f"[{status}] {name}{(' — ' + detail) if detail else ''}")
    if not condition:
        raise SystemExit(1)


def main() -> None:
    app = QCoreApplication(sys.argv)
    patch_winapi()

    tmp = Path(tempfile.mkdtemp(prefix="viberium-test-"))
    settings = Settings(directory=tmp)

    # ---------------------------------------------------------------- engine
    engine = ClickEngine()
    finished: list[tuple] = []
    stats: list[tuple] = []
    engine.finished.connect(lambda mode, reason: finished.append((mode, reason)))
    engine.stats.connect(lambda *args: stats.append(args))

    calls.clear()
    assert engine.start_mouse({**settings["mouse"], "interval_ms": 15, "limit_clicks": 10})
    check("engine started", engine.is_running("mouse"))
    pump(app, lambda: finished, 5)
    check("mouse finished by limit", finished and finished[0] == ("mouse", "limit"), str(finished))
    downs = [call for call in calls if call[0] == "mouse_down"]
    check("mouse click count", len(downs) == 10, f"{len(downs)} clicks")
    check("stats delivered", bool(stats), str(stats[-1] if stats else "none"))

    finished.clear()
    calls.clear()
    engine.start_keyboard({**settings["keyboard"], "key": 0x41, "interval_ms": 15, "limit_presses": 5})
    pump(app, lambda: finished, 5)
    check("keyboard finished by limit", finished and finished[0] == ("keyboard", "limit"), str(finished))
    check("key presses", len([c for c in calls if c[0] == "key_down"]) == 5)

    # multiple keys and combinations
    check(
        "keyboard normalize legacy",
        normalize_keyboard_combinations({"key": 0x41}) == [[0x41]],
    )
    check(
        "keyboard normalize combos",
        normalize_keyboard_combinations({"keys": [[0x11, 0x53], [0x0D], [0]]}) == [[0x11, 0x53], [0x0D]],
    )
    check(
        "keyboard normalize dedupes",
        normalize_keyboard_combinations({"keys": [[0x11, 0x11, 0x53]]}) == [[0x11, 0x53]],
    )
    check(
        "keyboard normalize modifiers",
        normalize_keyboard_combinations({"keys": [[0xA2, 0x53]]}) == [[0x11, 0x53]],
    )

    finished.clear()
    calls.clear()
    engine.start_keyboard(
        {
            **settings["keyboard"],
            "keys": [[0x41], [0x42]],
            "key_mode": "simultaneous",
            "interval_ms": 15,
            "limit_presses": 2,
        }
    )
    pump(app, lambda: finished, 5)
    downs = [c[1] for c in calls if c[0] == "key_down"]
    check("simultaneous presses together", downs == [0x41, 0x42, 0x41, 0x42], str(downs))

    finished.clear()
    calls.clear()
    engine.start_keyboard(
        {
            **settings["keyboard"],
            "keys": [[0x11, 0x53], [0x0D]],
            "key_mode": "sequence",
            "sequence_delay_ms": 5,
            "interval_ms": 15,
            "limit_presses": 2,
        }
    )
    pump(app, lambda: finished, 5)
    downs = [c[1] for c in calls if c[0] == "key_down"]
    ups = [c[1] for c in calls if c[0] == "key_up"]
    check("sequence order", downs == [0x11, 0x53, 0x0D], str(downs))
    check("sequence releases in reverse", ups == [0x53, 0x11, 0x0D], str(ups))

    # double click and hold
    finished.clear()
    calls.clear()
    engine.start_mouse(
        {**settings["mouse"], "interval_ms": 20, "click_type": "double", "hold_ms": 5, "limit_clicks": 4}
    )
    pump(app, lambda: finished, 5)
    check("double clicks", len([c for c in calls if c[0] == "mouse_down"]) == 4)

    # stop in the middle
    finished.clear()
    engine.start_mouse({**settings["mouse"], "interval_ms": 50, "limit_clicks": 0})
    time.sleep(0.12)
    engine.stop()
    pump(app, lambda: finished, 5)
    check("manual stop", finished and finished[0][1] == "stopped", str(finished))

    # --------------------------------------------------------------- hotkeys
    hub = InputHub()
    hotkeys = HotkeyManager(settings, hub)

    # Assign default test bindings since defaults are now empty
    settings.data["hotkeys"]["mouse"]["toggle"] = [0x75]   # F6
    settings.data["hotkeys"]["mouse"]["hold"] = [0x76]     # F7
    settings.data["hotkeys"]["mouse"]["emergency"] = [0x77]# F8
    hotkeys.reload()

    events: list[str] = []
    hotkeys.toggle_triggered.connect(lambda: events.append("toggle"))
    hotkeys.hold_started.connect(lambda: events.append("hold_start"))
    hotkeys.hold_ended.connect(lambda: events.append("hold_end"))
    hotkeys.emergency_triggered.connect(lambda: events.append("emergency"))

    toggle_vk = settings["hotkeys"]["mouse"]["toggle"][0]
    hold_vk = settings["hotkeys"]["mouse"]["hold"][0]
    emergency_vk = settings["hotkeys"]["mouse"]["emergency"][0]

    blocked = hotkeys._handle_key(toggle_vk, True, False, 0.0)
    check("toggle fires", events == ["toggle"], str(events))
    check("toggle blocked", blocked is True)
    hotkeys._handle_key(toggle_vk, True, False, 0.1)
    check("key repeat ignored", events == ["toggle"], str(events))
    hotkeys._handle_key(toggle_vk, False, False, 0.2)

    events.clear()
    hotkeys._handle_key(hold_vk, True, False, 0.0)
    check("hold starts", events == ["hold_start"], str(events))
    hotkeys._handle_key(hold_vk, False, False, 0.1)
    check("hold ends", events == ["hold_start", "hold_end"], str(events))

    events.clear()
    hotkeys._handle_key(emergency_vk, True, False, 0.0)
    check("emergency fires", events == ["emergency"], str(events))
    hotkeys._handle_key(emergency_vk, False, False, 0.1)

    events.clear()
    hotkeys._handle_key(0x41, True, False, 0.0)
    check("unbound key passes", events == [] and hotkeys._handle_key(0x41, True, False, 0.0) is False)
    hotkeys._handle_key(0x41, False, False, 0.1)

    # combo binding: ctrl + alt + k
    settings.data["hotkeys"]["mouse"]["toggle"] = [0x11, 0x12, 0x4B]
    hotkeys.reload()
    hotkeys._handle_key(0x11, True, False, 0.0)
    hotkeys._handle_key(0x12, True, False, 0.0)
    check("combo not fired early", events == [])
    hotkeys._handle_key(0x4B, True, False, 0.0)
    check("combo fires", events == ["toggle"], str(events))

    # capture mode
    captured: list = []
    hotkeys.captured.connect(lambda keys: captured.append(keys))
    hotkeys.begin_capture(None)
    hotkeys._handle_key(0x11, True, False, 0.0)
    hotkeys._handle_key(0x53, True, False, 0.0)
    check("capture returns combo", captured == [[0x11, 0x53]], str(captured))

    # low-level hooks report left/right modifier codes; everything must normalize
    captured.clear()
    events.clear()
    hotkeys.release_all()
    settings.data["hotkeys"]["mouse"]["toggle"] = [0x11, 0x53]
    hotkeys.reload()
    hotkeys._handle_key(0xA2, True, False, 0.0)
    check("raw modifier does not fire alone", events == [])
    hotkeys._handle_key(0x53, True, False, 0.0)
    check("raw modifier combo fires", events == ["toggle"], str(events))
    hotkeys._handle_key(0x53, False, False, 0.1)
    hotkeys._handle_key(0xA2, False, False, 0.1)

    captured.clear()
    hotkeys.begin_capture(None)
    hotkeys._handle_key(0xA2, True, False, 0.0)
    hotkeys._handle_key(0xA0, True, False, 0.0)
    check("capture waits for main key", captured == [], str(captured))
    hotkeys._handle_key(0x41, True, False, 0.0)
    check("capture normalizes modifiers", captured == [[0x11, 0x10, 0x41]], str(captured))

    # ----------------------------------------------------------------- macros
    calls.clear()
    macro = Macro(
        name="test",
        events=[
            {"t": 0.0, "type": "move", "x": 10, "y": 20},
            {"t": 0.0, "type": "down", "button": "left"},
            {"t": 0.05, "type": "up", "button": "left"},
            {"t": 0.1, "type": "key_down", "vk": 0x41},
            {"t": 0.1, "type": "key_up", "vk": 0x41},
        ],
        duration=0.1,
    )
    player = MacroPlayer()
    played: list[bool] = []
    player.finished.connect(lambda: played.append(True))
    start = time.perf_counter()
    check("player starts", player.play(macro, speed=5.0, loops=2))
    pump(app, lambda: played, 5)
    elapsed = time.perf_counter() - start
    check("player finished", bool(played))
    check("player replayed twice", len([c for c in calls if c[0] == "mouse_down"]) == 2, str(calls))
    check("player speed respected", elapsed < 0.6, f"{elapsed:.2f}s")

    store = MacroStore(tmp / "macros")
    store.save(macro)
    check("macro stored", store.names() == ["test"], str(store.names()))
    loaded = store.load("test")
    check("macro loaded", loaded is not None and len(loaded.events) == 5)

    # --------------------------------------------------------------- settings
    settings.set("mouse", "interval_ms", 250)
    settings.save()
    again = Settings(directory=tmp)
    check("settings persisted", again.get("mouse", "interval_ms") == 250)
    again.save_profile("Профиль 1")
    check("profile saved", again.profile_names() == ["Профиль 1"], str(again.profile_names()))
    again.set("mouse", "interval_ms", 999)
    check("profile loaded", again.load_profile("Профиль 1") and again.get("mouse", "interval_ms") == 250)
    # A profile must never carry the target process
    again.set("mouse", "target_process", "Some Window")
    again.save_profile("Профиль 2")
    profile_data = json.loads((tmp / "profiles" / "Профиль 2.json").read_text(encoding="utf-8"))
    check("profile has no target_process", "target_process" not in profile_data.get("mouse", {}))
    again.set("mouse", "target_process", "Current Window")
    again.load_profile("Профиль 2")
    check("profile keeps current process", again.get("mouse", "target_process") == "Current Window")
    again.delete_profile("Профиль 2")
    again.delete_profile("Профиль 1")
    check("profile deleted", again.profile_names() == [])

    migration_dir = tmp / "migration"
    migration_dir.mkdir()
    (migration_dir / "config.json").write_text(
        json.dumps(
            {
                "version": 3,
                "keyboard": {"key": 0x53, "keys": [[0xA2, 0x53]]},
                "hotkeys": {"mouse": {"toggle": [0xA3, 0x41]}},
            }
        ),
        encoding="utf-8",
    )
    migrated = Settings(directory=migration_dir)
    check(
        "config normalizes keyboard modifiers",
        migrated["keyboard"]["keys"] == [[0x11, 0x53]],
        str(migrated["keyboard"]["keys"]),
    )
    check(
        "config normalizes hotkey modifiers",
        migrated["hotkeys"]["mouse"]["toggle"] == [0x11, 0x41],
        str(migrated["hotkeys"]["mouse"]["toggle"]),
    )

    # -------------------------------------------------------------------- i18n
    tr.set_language("ru")
    ru_text = tr("btn.start")
    tr.set_language("en")
    en_text = tr("btn.start")
    check("i18n switches", (ru_text, en_text) == ("Старт", "Start"), f"{ru_text} / {en_text}")
    check("i18n formats", tr("settings.version", v="1.0.0") == "Version 1.0.0")
    check("vk names", winapi.combo_label([0x11, 0x53]) == "Ctrl + S", winapi.combo_label([0x11, 0x53]))
    check(
        "vk modifier aliases",
        winapi.vk_name(0xA2) == "Ctrl" and winapi.vk_name(0xA4) == "Alt",
        f"{winapi.vk_name(0xA2)} / {winapi.vk_name(0xA4)}",
    )
    check(
        "combo label normalizes modifiers",
        winapi.combo_label([0xA2, 0x53]) == "Ctrl + S",
        winapi.combo_label([0xA2, 0x53]),
    )

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
