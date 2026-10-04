"""Every Docker container on the machine."""
import json
from ..shell import run
from . import favorites


def parse_ps(text, favs=frozenset()):
    """`docker ps -a --format '{{json .}}'` output -> container list."""
    containers = []
    for line in text.splitlines():
        try:
            c = json.loads(line)
        except ValueError:
            continue
        name = c.get("Names", "")
        containers.append({
            "name":     name,
            "image":    c.get("Image", ""),
            "state":    c.get("State", ""),
            "status":   c.get("Status", ""),
            "favorite": name in favs,
        })
    return containers


def collect():
    """Every container, running or not. Empty if Docker isn't there."""
    out = run("docker ps -a --format '{{json .}}' 2>/dev/null")
    return parse_ps(out, favorites.store.names("docker"))
