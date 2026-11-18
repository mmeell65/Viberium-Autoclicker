"""Virtual-key helpers shared by hooks, hotkeys and settings."""

from __future__ import annotations

# Generic modifier virtual-key codes.
MODIFIER_VKS = frozenset({0x10, 0x11, 0x12, 0x5B, 0x5C})

# Low-level hooks report left/right specific modifiers; collapse them to generic
# codes so combinations like Ctrl+S are captured and matched consistently.
_MODIFIER_ALIASES = {
    0xA0: 0x10,  # VK_LSHIFT
    0xA1: 0x10,  # VK_RSHIFT
    0xA2: 0x11,  # VK_LCONTROL
    0xA3: 0x11,  # VK_RCONTROL
    0xA4: 0x12,  # VK_LMENU (Alt)
    0xA5: 0x12,  # VK_RMENU (Alt)
}


def normalize_vk(vk: int) -> int:
    """Collapse left/right modifier keys into their generic virtual-key codes."""
    try:
        code = int(vk)
    except (TypeError, ValueError):
        return 0
    return _MODIFIER_ALIASES.get(code, code)
