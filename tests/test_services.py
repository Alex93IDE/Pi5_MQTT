import json
import os
import tempfile
import unittest
from unittest.mock import patch
from pi5mqtt.services import favorites, systemd, docker, control

UNITS = [
    {"unit": "mosquitto.service", "load": "loaded", "active": "active", "sub": "running", "description": "Mosquitto"},
    {"unit": "getty@tty1.service", "load": "loaded", "active": "active", "sub": "running", "description": "Getty"},
    {"unit": "ghost.service", "load": "not-found", "active": "inactive", "sub": "dead", "description": "ghost"},
]
UNIT_FILES = [
    {"unit_file": "mosquitto.service", "state": "enabled"},
    {"unit_file": "getty@.service", "state": "enabled"},
]


def fake_run_json(cmd):
    return UNIT_FILES if "list-unit-files" in cmd else UNITS


class ServicesTestCase(unittest.TestCase):
    """Isolates every test from the real favorites.json, systemctl and Docker."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.fav_file = os.path.join(tmp.name, "favorites.json")
        for p in (
            patch.object(favorites, "store", favorites.Favorites(self.fav_file)),
            patch.object(systemd, "run_json", fake_run_json),
            patch.object(docker, "run", return_value=""),
        ):
            p.start()
            self.addCleanup(p.stop)


class Systemd(ServicesTestCase):
    def test_lists_installed_units_with_state(self):
        by_name = {s["name"]: s for s in systemd.collect()}
        self.assertNotIn("ghost.service", by_name)
        self.assertEqual(by_name["mosquitto.service"]["enabled"], "enabled")
        self.assertFalse(by_name["mosquitto.service"]["favorite"])

    def test_instance_falls_back_to_template_state(self):
        by_name = {s["name"]: s for s in systemd.collect()}
        self.assertEqual(by_name["getty@tty1.service"]["enabled"], "enabled")

    def test_systemctl_unavailable(self):
        with patch.object(systemd, "run_json", return_value=None):
            self.assertEqual(systemd.collect(), [])


class Docker(unittest.TestCase):
    def test_parses_one_container_per_line(self):
        out = (
            '{"Names": "pihole", "Image": "pihole/pihole", "State": "running", "Status": "Up 3 days"}\n'
            "not json\n"
            '{"Names": "old", "Image": "busybox", "State": "exited", "Status": "Exited (0)"}\n'
        )
        containers = docker.parse_ps(out, favs={"old"})
        self.assertEqual([c["name"] for c in containers], ["pihole", "old"])
        self.assertEqual([c["favorite"] for c in containers], [False, True])
        self.assertEqual(containers[0]["state"], "running")

    def test_no_docker(self):
        self.assertEqual(docker.parse_ps(""), [])


class FavoritesStore(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = os.path.join(tmp.name, "favorites.json")

    def test_set_saves_and_survives_reload(self):
        favorites.Favorites(self.path).set("systemd", "a.service", True)
        with open(self.path) as f:
            self.assertEqual(json.load(f), {"systemd": ["a.service"], "docker": []})
        self.assertEqual(favorites.Favorites(self.path).names("systemd"), {"a.service"})

    def test_unset(self):
        store = favorites.Favorites(self.path)
        store.set("docker", "pihole", True)
        store.set("docker", "pihole", False)
        self.assertEqual(favorites.Favorites(self.path).names("docker"), set())

    def test_corrupt_or_odd_file_starts_empty(self):
        for content in ("{not json", "[1, 2]"):
            with self.subTest(content=content):
                with open(self.path, "w") as f:
                    f.write(content)
                self.assertEqual(favorites.Favorites(self.path).names("systemd"), set())

    def test_names_is_a_copy(self):
        store = favorites.Favorites(self.path)
        store.names("systemd").add("sneaky")
        self.assertEqual(store.names("systemd"), set())


class FavoriteCommand(ServicesTestCase):
    def test_star_returns_changed_source(self):
        changed = control.handle({"action": "favorite", "source": "systemd", "name": "mosquitto.service", "value": True})
        self.assertEqual(changed, "systemd")
        starred = [s["name"] for s in systemd.collect() if s["favorite"]]
        self.assertEqual(starred, ["mosquitto.service"])

    def test_rejected(self):
        cases = [
            {"action": "favorite", "source": "systemd", "name": "nope.service", "value": True},
            {"action": "favorite", "source": "systemd", "name": "mosquitto.service", "value": "true"},
            {"action": "favorite", "source": "apt", "name": "mosquitto.service", "value": True},
            {"action": "favorite", "source": "systemd", "name": ["mosquitto.service"], "value": True},
            {"action": "restart", "source": "systemd", "name": "mosquitto.service"},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertLogs("services", level="WARNING"):
                    self.assertIsNone(control.handle(payload))
        self.assertFalse(os.path.exists(self.fav_file))


if __name__ == "__main__":
    unittest.main()
