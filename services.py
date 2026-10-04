import os
import json
import threading
from helpers import run, run_json
from config import TOPIC_SERVICES, TOPIC_DOCKER

FAVORITES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "favorites.json")
SOURCES = ("systemd", "docker")

# The control callback runs on paho's thread, the loop on the main one.
_lock = threading.Lock()


# ── Favorites ──────────────────────────────────────────────
def _load_favorites():
    try:
        with open(FAVORITES_FILE) as f:
            data = json.load(f)
        return {src: set(data.get(src, [])) for src in SOURCES}
    except (OSError, ValueError):
        return {src: set() for src in SOURCES}


def _save_favorites(favs):
    tmp = FAVORITES_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump({src: sorted(favs[src]) for src in SOURCES}, f, indent=2)
    os.replace(tmp, FAVORITES_FILE)


_favorites = _load_favorites()


# ── Collectors ─────────────────────────────────────────────
def _unit_file_states():
    """unit file -> enabled/disabled/static/masked/..."""
    files = run_json("systemctl list-unit-files --type=service --output=json") or []
    return {f["unit_file"]: f.get("state", "") for f in files}


def _enabled(states, unit):
    if unit in states:
        return states[unit]
    # Instances like getty@tty1.service only have a template unit file.
    prefix, at, _ = unit.partition("@")
    return states.get(f"{prefix}@.service", "") if at else ""


def get_systemd():
    """Every service unit systemd knows about, running or not."""
    units = run_json("systemctl list-units --type=service --all --output=json") or []
    states = _unit_file_states()
    with _lock:
        favs = set(_favorites["systemd"])
    return [
        {
            "name":        u["unit"],
            "active":      u.get("active", ""),
            "sub":         u.get("sub", ""),
            "enabled":     _enabled(states, u["unit"]),
            "description": u.get("description", ""),
            "favorite":    u["unit"] in favs,
        }
        for u in units
        # Units something references but that aren't installed.
        if u.get("load") != "not-found"
    ]


def get_docker():
    """Every container, running or not. Empty if Docker isn't there."""
    out = run("docker ps -a --format '{{json .}}' 2>/dev/null")
    with _lock:
        favs = set(_favorites["docker"])
    containers = []
    for line in out.splitlines():
        try:
            c = json.loads(line)
        except ValueError:
            continue
        containers.append({
            "name":     c.get("Names", ""),
            "image":    c.get("Image", ""),
            "state":    c.get("State", ""),
            "status":   c.get("Status", ""),
            "favorite": c.get("Names", "") in favs,
        })
    return containers


_COLLECTORS = {"systemd": (TOPIC_SERVICES, get_systemd), "docker": (TOPIC_DOCKER, get_docker)}


def publish(client, source):
    topic, collect = _COLLECTORS[source]
    client.publish(topic, json.dumps(collect()), qos=0, retain=True)


def publish_all(client):
    for source in SOURCES:
        publish(client, source)


# ── Control ────────────────────────────────────────────────
def handle_services_control(client, payload):
    """{"action": "favorite", "source": "systemd"|"docker", "name": ..., "value": bool}"""
    if payload.get("action") != "favorite":
        return

    source = payload.get("source")
    name   = payload.get("name")
    value  = payload.get("value")
    if source not in SOURCES or not isinstance(name, str) or not isinstance(value, bool):
        print(f"[services] Bad favorite command: {payload}")
        return

    # Only accept names that actually exist, so the file can't fill with junk.
    _, collect = _COLLECTORS[source]
    if not any(item["name"] == name for item in collect()):
        print(f"[services] Unknown {source} name: {name}")
        return

    with _lock:
        if value:
            _favorites[source].add(name)
        else:
            _favorites[source].discard(name)
        _save_favorites(_favorites)

    # Publish straight away so the dashboard sees the change without
    # waiting for the next slow tick.
    publish(client, source)
