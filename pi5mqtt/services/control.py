"""Starring and unstarring services from the dashboard."""
import logging
from . import favorites, systemd, docker

log = logging.getLogger("services")

_COLLECTORS = {"systemd": systemd.collect, "docker": docker.collect}


def handle(payload):
    """{"action": "favorite", "source": "systemd"|"docker", "name": ..., "value": bool}

    Returns the source that changed, so the caller can republish it
    straight away, or None if nothing did.
    """
    if payload.get("action") != "favorite":
        log.warning("Unknown action: %r", payload.get("action"))
        return None

    source = payload.get("source")
    name   = payload.get("name")
    value  = payload.get("value")
    if source not in _COLLECTORS or not isinstance(name, str) or not isinstance(value, bool):
        log.warning("Bad favorite command: %s", payload)
        return None

    # Only accept names that actually exist, so the file can't fill with junk.
    if not any(item["name"] == name for item in _COLLECTORS[source]()):
        log.warning("Unknown %s name: %s", source, name)
        return None

    favorites.store.set(source, name, value)
    return source
