"""Commands from the control topic, validated before they reach the case."""
import logging
import math
import re
from . import api

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_STYLE     = re.compile(r"^[a-z_]{1,32}$")

log = logging.getLogger("ctrl")


def _int_in(value, lo, hi):
    """value as an int if it's a whole number in [lo, hi], else None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    # json.loads accepts Infinity and NaN, which int() can't take.
    if isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()):
        return None
    value = int(value)
    return value if lo <= value <= hi else None


def handle(payload):
    a = payload.get("action")

    if a in ("oled_on", "oled_off"):
        api.post("set-oled-enable", {"enable": a == "oled_on"})
    elif a in ("rgb_on", "rgb_off"):
        api.post("set-rgb-enable", {"enable": a == "rgb_on"})

    elif a == "rgb_color":
        color = payload.get("color")
        if not isinstance(color, str) or not _HEX_COLOR.match(color):
            log.warning("Bad color: %r", color)
            return
        api.post("set-rgb-color", {"color": color})

    elif a == "rgb_style":
        style = payload.get("style")
        if not isinstance(style, str) or not _STYLE.match(style):
            log.warning("Bad style: %r", style)
            return
        api.post("set-rgb-style", {"style": style})

    elif a in ("rgb_brightness", "rgb_speed"):
        value = _int_in(payload.get("value"), 0, 100)
        if value is None:
            log.warning("Bad %s value: %r", a, payload.get("value"))
            return
        key = "brightness" if a == "rgb_brightness" else "speed"
        api.post(f"set-rgb-{key}", {key: value})

    elif a == "fan_mode":
        # 0=Always On, 1=Performance, 2=Cool, 3=Balance, 4=Silent
        mode = _int_in(payload.get("mode"), 0, 4)
        if mode is None:
            log.warning("Bad fan mode: %r", payload.get("mode"))
            return
        api.post("set-fan-mode", {"fan_mode": mode})

    else:
        log.warning("Unknown action: %r", a)
