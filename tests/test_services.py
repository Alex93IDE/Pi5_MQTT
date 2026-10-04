import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import services

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
    """Isolates every test from the real favorites.json and systemctl."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.fav_file = os.path.join(tmp.name, "favorites.json")
        for p in (
            patch.object(services, "FAVORITES_FILE", self.fav_file),
            patch.object(services, "_favorites", {"systemd": set(), "docker": set()}),
            patch.object(services, "run_json", fake_run_json),
            patch.object(services, "run", return_value=""),
        ):
            p.start()
            self.addCleanup(p.stop)


class GetSystemd(ServicesTestCase):
    def test_lists_installed_units_with_state(self):
        by_name = {s["name"]: s for s in services.get_systemd()}
        self.assertNotIn("ghost.service", by_name)
        self.assertEqual(by_name["mosquitto.service"]["enabled"], "enabled")
        self.assertFalse(by_name["mosquitto.service"]["favorite"])

    def test_instance_falls_back_to_template_state(self):
        by_name = {s["name"]: s for s in services.get_systemd()}
        self.assertEqual(by_name["getty@tty1.service"]["enabled"], "enabled")

    def test_systemctl_unavailable(self):
        with patch.object(services, "run_json", return_value=None):
            self.assertEqual(services.get_systemd(), [])


class GetDocker(ServicesTestCase):
    def test_parses_one_container_per_line(self):
        out = (
            '{"Names": "pihole", "Image": "pihole/pihole", "State": "running", "Status": "Up 3 days"}\n'
            "not json\n"
            '{"Names": "old", "Image": "busybox", "State": "exited", "Status": "Exited (0)"}\n'
        )
        with patch.object(services, "run", return_value=out):
            containers = services.get_docker()
        self.assertEqual([c["name"] for c in containers], ["pihole", "old"])
        self.assertEqual(containers[0]["state"], "running")

    def test_no_docker(self):
        self.assertEqual(services.get_docker(), [])


class Favorites(ServicesTestCase):
    def favorite(self, **payload):
        client = MagicMock()
        services.handle_services_control(client, {"action": "favorite", **payload})
        return client

    def test_star_saves_and_republishes(self):
        client = self.favorite(source="systemd", name="mosquitto.service", value=True)

        with open(self.fav_file) as f:
            self.assertEqual(json.load(f), {"systemd": ["mosquitto.service"], "docker": []})

        client.publish.assert_called_once()
        topic, payload = client.publish.call_args.args
        self.assertEqual(topic, services.TOPIC_SERVICES)
        starred = [s["name"] for s in json.loads(payload) if s["favorite"]]
        self.assertEqual(starred, ["mosquitto.service"])

    def test_unstar(self):
        self.favorite(source="systemd", name="mosquitto.service", value=True)
        self.favorite(source="systemd", name="mosquitto.service", value=False)
        with open(self.fav_file) as f:
            self.assertEqual(json.load(f)["systemd"], [])

    def test_survives_reload(self):
        self.favorite(source="systemd", name="mosquitto.service", value=True)
        self.assertEqual(services._load_favorites()["systemd"], {"mosquitto.service"})

    def test_rejected(self):
        cases = [
            {"source": "systemd", "name": "nope.service", "value": True},
            {"source": "systemd", "name": "mosquitto.service", "value": "true"},
            {"source": "apt", "name": "mosquitto.service", "value": True},
            {"source": "systemd", "name": ["mosquitto.service"], "value": True},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertLogs("services", level="WARNING"):
                    client = self.favorite(**payload)
                client.publish.assert_not_called()
        self.assertFalse(os.path.exists(self.fav_file))

    def test_corrupt_file_starts_empty(self):
        with open(self.fav_file, "w") as f:
            f.write("{not json")
        self.assertEqual(services._load_favorites(), {"systemd": set(), "docker": set()})


if __name__ == "__main__":
    unittest.main()
