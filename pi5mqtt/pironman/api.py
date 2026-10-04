"""The Pironman5 case software's local HTTP API."""
import json
import logging
import urllib.request
from ..config import API

log = logging.getLogger("pironman")


def get_config():
    """The case's current settings, or {} if the API isn't answering."""
    try:
        with urllib.request.urlopen(f"{API}/get-config", timeout=2) as r:
            data = json.load(r)
    except (OSError, ValueError):
        return {}
    if isinstance(data, dict) and data.get("status"):
        return data.get("data", {}).get("system", {})
    return {}


def post(endpoint, body):
    """POST JSON to the API. No shell involved."""
    req = urllib.request.Request(
        f"{API}/{endpoint}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=5).close()
    except OSError as e:
        log.error("%s failed: %s", endpoint, e)


def collect():
    """Case state for the fast payload. Defaults when the API is down."""
    cfg = get_config()
    return {
        "rgb_enable":     cfg.get("rgb_enable", False),
        "rgb_color":      cfg.get("rgb_color", "#000000"),
        "rgb_style":      cfg.get("rgb_style", ""),
        "rgb_brightness": cfg.get("rgb_brightness", 0),
        "rgb_speed":      cfg.get("rgb_speed", 0),
        "oled_enable":    cfg.get("oled_enable", False),
        "fan_mode":       cfg.get("gpio_fan_mode", 1),
    }
