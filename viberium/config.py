"""Application settings: defaults, persistence and profiles."""

from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .core.vkeys import normalize_vk

APP_NAME = "Viberium"
APP_VERSION = "1.2.1"
GITHUB_URL = "https://github.com/mmeell65/Viberium-Autoclicker"
LICENSE_URL = f"{GITHUB_URL}/blob/main/LICENSE"
TELEGRAM_URL = "https://t.me/viberium_autoclicker"

DEFAULTS: dict[str, Any] = {
    "language": "ru",
    "theme": "dark",           # dark | light
    "mouse": {
        "button": "left",          # left | right | middle
        "click_type": "single",    # single | double | triple
        "interval_ms": 100,
        "randomize": 0,            # percent of the interval
        "hold_ms": 0,              # how long the button stays pressed
        "position_mode": "cursor", # cursor | fixed
        "fixed_x": 0,
        "fixed_y": 0,
        "jitter_px": 0,
        "limit_clicks": 0,         # 0 = unlimited
        "limit_seconds": 0,        # 0 = unlimited
        "stop_on_move": False,
        "start_delay_ms": 0,
        "ignore_modifiers": False, # отпускать Shift/Ctrl/Alt на время клика
    },
    "keyboard": {
        "key": 32,                 # virtual-key code (space by default)
        "keys": [[32]],             # several key combinations, in sequence order
        "key_mode": "simultaneous", # simultaneous | sequence
        "sequence_delay_ms": 25,
        "interval_ms": 100,
        "randomize": 0,
        "hold_ms": 0,
        "limit_presses": 0,
        "limit_seconds": 0,
        "start_delay_ms": 0,
    },
    "hotkeys": {
        "mouse": {              # горячие клавиши автокликера мыши
            "toggle": [],       # пусто — не назначено
            "hold": [],         # пусто — не назначено
            "emergency": [0x77],# F8 — экстренный стоп (всегда назначен)
        },
        "keyboard": {           # горячие клавиши автокликера клавиатуры
            "toggle": [],
            "hold": [],
            "emergency": [0x77],# F8 — экстренный стоп (всегда назначен)
        },
        "macros": {             # горячие клавиши макросов
            "play": [],         # пусто — не назначено
            "record": [],       # пусто — не назначено
            "per_macro": {},    # {"<макрос>": {"play": [], "record": []}}
        },
        "global": {             # работают на любой странице
            "record": [],       # старт / стоп записи макроса
        },
        "hold_enabled": True,
        "block_keys": True,
        # Одно целевое окно для всех вкладок (мышь, клавиатура, макросы).
        # Пусто — кликер работает в любом окне. При закрытии приложения
        # сбрасывается (см. MainWindow._clear_target).
        "target_process": "",
    },
    "general": {
        "minimize_to_tray": True,
        "always_on_top": False,
        "autostart": False,
        "start_minimized": False,
    },
    "macro": {
        "speed": 1.0,
        "loops": 1,
        "record_moves": False,  # записывать ли движение курсора
        "hide_on_record": True, # сворачивать окно при старте записи
    },
    "version": 5,  # 5 = одно целевое окно для всех вкладок
}


def appdata_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / APP_NAME


LEGACY_APP_NAME = "ClickForge"


def _migrate_legacy(target: Path) -> None:
    """Переносит настройки из старой папки ClickForge (после переименования)."""
    base = os.environ.get("APPDATA") or str(Path.home())
    legacy = Path(base) / LEGACY_APP_NAME
    if not legacy.exists() or target.exists():
        return
    try:
        import shutil

        shutil.copytree(legacy, target)
    except OSError:
        pass


def _normalize_keyboard(section: dict) -> None:
    """Normalize key combinations and migrate a legacy single key."""
    if not isinstance(section, dict):
        return
    raw_keys = section.get("keys")
    if raw_keys is None:
        raw_keys = [[section.get("key", 32)]]
    if not isinstance(raw_keys, (list, tuple)):
        raw_keys = [raw_keys]
    combinations: list[list[int]] = []
    for item in raw_keys:
        values = item if isinstance(item, (list, tuple)) else [item]
        combo: list[int] = []
        for value in values:
            vk = normalize_vk(value)
            if vk > 0 and vk not in combo:
                combo.append(vk)
        if combo:
            combinations.append(combo)
    section["keys"] = combinations
    if combinations:
        section["key"] = combinations[0][-1]


def _normalize_hotkeys(section: dict) -> None:
    """Collapse left/right modifier codes in saved hotkey bindings.

    Walks every nested level, so per-macro bindings
    ({"macros": {"per_macro": {"<macro>": {"play": [...]}}}}) are covered too.
    """
    if not isinstance(section, dict):
        return
    for name, value in list(section.items()):
        if isinstance(value, dict):
            _normalize_hotkeys(value)
            continue
        if not isinstance(value, (list, tuple)):
            continue
        if not all(isinstance(item, (int, str)) for item in value):
            _normalize_hotkeys(value)
            continue
        normalized: list[int] = []
        for item in value:
            vk = normalize_vk(item)
            if vk > 0 and vk not in normalized:
                normalized.append(vk)
        section[name] = normalized


def _migrate_target(raw: dict) -> None:
    """Переносит старое раздельное окно (mouse/keyboard) в общий ключ."""
    hotkeys = raw.get("hotkeys")
    if not isinstance(hotkeys, dict):
        hotkeys = {}
        raw["hotkeys"] = hotkeys
    if not hotkeys.get("target_process"):
        for section in ("mouse", "keyboard"):
            value = (raw.get(section) or {}).get("target_process") if isinstance(raw.get(section), dict) else None
            if value:
                hotkeys["target_process"] = value
                break
    # Старые раздельные ключи больше не используются
    for section in ("mouse", "keyboard"):
        if isinstance(raw.get(section), dict):
            raw[section].pop("target_process", None)


def _deep_merge(base: dict, patch: dict) -> dict:
    for key, value in patch.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


class Settings:
    """Nested settings store backed by a JSON file."""

    def __init__(self, directory: Path | None = None) -> None:
        self.dir = directory or appdata_dir()
        if directory is None:
            _migrate_legacy(self.dir)
        self.path = self.dir / "config.json"
        self.profiles_dir = self.dir / "profiles"
        self.data: dict[str, Any] = copy.deepcopy(DEFAULTS)
        self.load()

    # ------------------------------------------------------------------ data
    def __getitem__(self, section: str) -> dict[str, Any]:
        return self.data.setdefault(section, {})

    def get(self, section: str, key: str, default: Any = None) -> Any:
        return self.data.get(section, {}).get(key, default)

    def get_value(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, section: str, key: str, value: Any, save: bool = True) -> None:
        self.data.setdefault(section, {})[key] = value
        if save:
            self.save()

    # ------------------------------------------------------------------- io
    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                outdated = raw.get("version") != DEFAULTS["version"]
                if outdated:
                    # Old config format: the version bump brings new defaults,
                    # saved keys on known actions are kept as they are.
                    raw["version"] = DEFAULTS["version"]
                _normalize_hotkeys(raw.get("hotkeys"))
                _normalize_keyboard(raw.get("keyboard"))
                _migrate_target(raw)
                self.data = _deep_merge(copy.deepcopy(DEFAULTS), raw)
                if outdated:
                    self.save()
        except (OSError, ValueError):
            self.data = copy.deepcopy(DEFAULTS)

    def save(self) -> None:
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(self.data, ensure_ascii=False, indent=2)
            fd, tmp = tempfile.mkstemp(dir=str(self.dir), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
            os.replace(tmp, self.path)
        except OSError:
            pass

    def reset(self) -> None:
        self.data = copy.deepcopy(DEFAULTS)
        self.save()

    # ------------------------------------------------------------- profiles
    def profile_names(self) -> list[str]:
        if not self.profiles_dir.exists():
            return []
        return sorted(path.stem for path in self.profiles_dir.glob("*.json"))

    def save_profile(self, name: str) -> None:
        safe = _safe_name(name)
        if not safe:
            return
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        # The target process is always picked manually — never stored in a profile
        snapshot = copy.deepcopy(self.data)
        if isinstance(snapshot.get("hotkeys"), dict):
            snapshot["hotkeys"].pop("target_process", None)
        payload = json.dumps(snapshot, ensure_ascii=False, indent=2)
        (self.profiles_dir / f"{safe}.json").write_text(payload, encoding="utf-8")

    def load_profile(self, name: str) -> bool:
        path = self.profiles_dir / f"{_safe_name(name)}.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        if not isinstance(raw, dict):
            return False
        language = self.data.get("language", "ru")
        # Keep the currently selected process — a profile never changes it
        current_target = (self.data.get("hotkeys") or {}).get("target_process", "")
        if isinstance(raw.get("hotkeys"), dict):
            raw["hotkeys"].pop("target_process", None)
        for section in ("mouse", "keyboard"):
            if isinstance(raw.get(section), dict):
                raw[section].pop("target_process", None)
        _normalize_hotkeys(raw.get("hotkeys"))
        _normalize_keyboard(raw.get("keyboard"))
        self.data = _deep_merge(copy.deepcopy(DEFAULTS), raw)
        self.data["language"] = language
        self.data.setdefault("hotkeys", {})["target_process"] = current_target
        self.save()
        return True

    def delete_profile(self, name: str) -> None:
        try:
            (self.profiles_dir / f"{_safe_name(name)}.json").unlink()
        except OSError:
            pass


def _safe_name(name: str) -> str:
    cleaned = "".join(ch for ch in name.strip() if ch.isalnum() or ch in " -_()")
    return cleaned[:60].strip()
