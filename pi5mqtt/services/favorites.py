"""Which services and containers the user has starred, kept on disk."""
import json
import os
import threading
from ..config import FAVORITES_FILE

SOURCES = ("systemd", "docker")


class Favorites:
    def __init__(self, path):
        self.path = path
        # Written from the MQTT thread, read from the publisher threads.
        self._lock = threading.Lock()
        self._names = self._load()

    def _load(self):
        try:
            with open(self.path) as f:
                data = json.load(f)
            return {src: set(data.get(src, [])) for src in SOURCES}
        except (OSError, ValueError, AttributeError):
            return {src: set() for src in SOURCES}

    def _save(self):
        # Write-then-rename, so a power cut can't leave half a file.
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump({src: sorted(self._names[src]) for src in SOURCES}, f, indent=2)
        os.replace(tmp, self.path)

    def names(self, source):
        with self._lock:
            return set(self._names[source])

    def set(self, source, name, value):
        with self._lock:
            if value:
                self._names[source].add(name)
            else:
                self._names[source].discard(name)
            self._save()


store = Favorites(FAVORITES_FILE)
