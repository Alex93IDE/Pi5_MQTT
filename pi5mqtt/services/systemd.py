"""Every systemd service on the machine."""
from ..shell import run_json
from . import favorites


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


def collect():
    """Every service unit systemd knows about, running or not."""
    units = run_json("systemctl list-units --type=service --all --output=json") or []
    states = _unit_file_states()
    favs = favorites.store.names("systemd")
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
