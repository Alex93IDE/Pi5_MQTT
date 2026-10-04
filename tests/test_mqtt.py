import unittest
from unittest.mock import MagicMock, patch
from pi5mqtt import mqtt as mqtt_module
from pi5mqtt.config import TOPIC_STATUS


class Client(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(mqtt_module.mqtt, "Client")
        self.paho = patcher.start().return_value
        self.addCleanup(patcher.stop)
        self.handler = MagicMock()
        self.client = mqtt_module.create_client({"pi5/control/x": self.handler})

    def message(self, topic, payload):
        self.paho.on_message(self.paho, None, MagicMock(topic=topic, payload=payload))

    def test_connects_in_background(self):
        # Starting before the broker is up must not crash the daemon.
        self.paho.connect_async.assert_called_once()
        self.paho.connect.assert_not_called()

    def test_broker_announces_offline_if_we_vanish(self):
        self.paho.will_set.assert_called_once_with(TOPIC_STATUS, "offline", qos=1, retain=True)

    def test_on_connect_announces_online_and_subscribes(self):
        self.paho.on_connect(self.paho, None, None, 0)
        self.paho.publish.assert_any_call(TOPIC_STATUS, "online", qos=1, retain=True)
        self.paho.subscribe.assert_called_once_with([("pi5/control/x", 0)])

    def test_failed_connect_does_not_claim_online(self):
        with self.assertLogs("mqtt", level="ERROR"):
            self.paho.on_connect(self.paho, None, None, 5)
        self.paho.publish.assert_not_called()

    def test_clean_shutdown_announces_offline(self):
        mqtt_module.shutdown(self.client)
        self.paho.publish.assert_called_with(TOPIC_STATUS, "offline", qos=1, retain=True)
        self.paho.disconnect.assert_called_once()

    def test_routes_json_to_its_handler(self):
        self.message("pi5/control/x", b'{"action": "rgb_on"}')
        self.handler.assert_called_once_with({"action": "rgb_on"})

    def test_ignores_bad_messages(self):
        for payload in (b"\xff not json", b"not json", b"[1, 2]", b'"text"'):
            with self.subTest(payload=payload):
                with self.assertLogs("mqtt", level="WARNING"):
                    self.message("pi5/control/x", payload)
        self.handler.assert_not_called()

    def test_ignores_unrouted_topics(self):
        self.message("pi5/other", b"{}")
        self.handler.assert_not_called()

    def test_handler_crash_is_contained(self):
        self.handler.side_effect = RuntimeError("boom")
        with self.assertLogs("mqtt", level="ERROR"):
            self.message("pi5/control/x", b"{}")


if __name__ == "__main__":
    unittest.main()
