import unittest
from unittest.mock import MagicMock, patch
import client as client_module
from config import TOPIC_STATUS


class OnlineStatus(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(client_module.mqtt, "Client")
        self.mqtt_client = patcher.start().return_value
        self.addCleanup(patcher.stop)
        self.client = client_module.create_client()

    def test_broker_announces_offline_if_we_vanish(self):
        self.mqtt_client.will_set.assert_called_once_with(TOPIC_STATUS, "offline", qos=1, retain=True)

    def test_announces_online_on_connect(self):
        self.mqtt_client.on_connect(self.mqtt_client, None, None, 0)
        self.mqtt_client.publish.assert_any_call(TOPIC_STATUS, "online", qos=1, retain=True)

    def test_failed_connect_does_not_claim_online(self):
        with self.assertLogs("mqtt", level="ERROR"):
            self.mqtt_client.on_connect(self.mqtt_client, None, None, 5)
        self.mqtt_client.publish.assert_not_called()

    def test_clean_shutdown_announces_offline(self):
        client_module.shutdown(self.client)
        self.mqtt_client.publish.assert_called_with(TOPIC_STATUS, "offline", qos=1, retain=True)
        self.mqtt_client.disconnect.assert_called_once()

    def test_bad_message_does_not_raise(self):
        msg = MagicMock(topic="pi5/control/pironman", payload=b"\xff not json")
        with self.assertLogs("mqtt", level="WARNING"):
            self.mqtt_client.on_message(self.mqtt_client, None, msg)


if __name__ == "__main__":
    unittest.main()
