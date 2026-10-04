import re
import json
import urllib.request
from config import API

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_STYLE     = re.compile(r"^[a-z_]{1,32}$")


def _post(endpoint, body):
    """POST JSON to the Pironman5 API. No shell involved."""
    req = urllib.request.Request(
        f"{API}/{endpoint}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=5).close()
    except OSError as e:
        print(f"[ctrl] {endpoint} failed: {e}")


def _int_in(value, lo, hi):
    """value as an int if it's a whole number in [lo, hi], else None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != int(value):
        return None
    value = int(value)
    return value if lo <= value <= hi else None


def handle_control(payload):
    a = payload.get("action")

    if a in ("oled_on", "oled_off"):
        _post("set-oled-enable", {"enable": a == "oled_on"})
    elif a in ("rgb_on", "rgb_off"):
        _post("set-rgb-enable", {"enable": a == "rgb_on"})

    elif a == "rgb_color":
        color = payload.get("color")
        if not isinstance(color, str) or not _HEX_COLOR.match(color):
            print(f"[ctrl] Bad color: {color!r}")
            return
        _post("set-rgb-color", {"color": color})

    elif a == "rgb_style":
        style = payload.get("style")
        if not isinstance(style, str) or not _STYLE.match(style):
            print(f"[ctrl] Bad style: {style!r}")
            return
        _post("set-rgb-style", {"style": style})

    elif a in ("rgb_brightness", "rgb_speed"):
        value = _int_in(payload.get("value"), 0, 100)
        if value is None:
            print(f"[ctrl] Bad {a} value: {payload.get('value')!r}")
            return
        key = "brightness" if a == "rgb_brightness" else "speed"
        _post(f"set-rgb-{key}", {key: value})

    elif a == "fan_mode":
        # 0=Always On, 1=Performance, 2=Cool, 3=Balance, 4=Silent
        mode = _int_in(payload.get("mode"), 0, 4)
        if mode is None:
            print(f"[ctrl] Bad fan mode: {payload.get('mode')!r}")
            return
        _post("set-fan-mode", {"fan_mode": mode})

    else:
        print(f"[ctrl] Unknown action: {a!r}")
