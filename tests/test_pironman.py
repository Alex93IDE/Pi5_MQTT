import json
import unittest
from unittest.mock import patch
from pi5mqtt.pironman import control, api


class HandleControl(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(api, "post")
        self.post = patcher.start()
        self.addCleanup(patcher.stop)

    def send(self, raw):
        # Go through json.loads like a real MQTT message does.
        control.handle(json.loads(raw))

    def test_valid_commands(self):
        cases = [
            ('{"action": "oled_on"}',                           ("set-oled-enable", {"enable": True})),
            ('{"action": "rgb_off"}',                           ("set-rgb-enable", {"enable": False})),
            ('{"action": "rgb_color", "color": "#00Ff00"}',     ("set-rgb-color", {"color": "#00Ff00"})),
            ('{"action": "rgb_style", "style": "hue_cycle"}',   ("set-rgb-style", {"style": "hue_cycle"})),
            ('{"action": "rgb_brightness", "value": 0}',        ("set-rgb-brightness", {"brightness": 0})),
            ('{"action": "rgb_speed", "value": 100.0}',         ("set-rgb-speed", {"speed": 100})),
            ('{"action": "fan_mode", "mode": 4}',               ("set-fan-mode", {"fan_mode": 4})),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.post.reset_mock()
                self.send(raw)
                self.post.assert_called_once_with(*expected)

    def test_rejected_commands_send_nothing(self):
        cases = [
            # The shell injection this module used to be open to.
            '{"action": "rgb_color", "color": "\'; touch /tmp/pwned; echo \'"}',
            '{"action": "rgb_color", "color": "#fff"}',
            '{"action": "rgb_color"}',
            '{"action": "rgb_style", "style": "a;b"}',
            '{"action": "rgb_style", "style": "Breathing"}',
            '{"action": "rgb_brightness", "value": "50"}',
            '{"action": "rgb_brightness", "value": 101}',
            '{"action": "rgb_brightness", "value": -1}',
            '{"action": "rgb_brightness", "value": 50.5}',
            '{"action": "rgb_brightness", "value": true}',
            '{"action": "rgb_speed", "value": Infinity}',
            '{"action": "rgb_speed", "value": NaN}',
            '{"action": "fan_mode", "mode": 5}',
            '{"action": "fan_mode"}',
            '{"action": "reboot"}',
            '{}',
        ]
        for raw in cases:
            with self.subTest(raw=raw):
                with self.assertLogs("ctrl", level="WARNING"):
                    self.send(raw)
                self.post.assert_not_called()


class PironmanState(unittest.TestCase):
    def test_defaults_when_api_is_down(self):
        with patch.object(api, "get_config", return_value={}):
            state = api.collect()
        self.assertEqual(state["rgb_enable"], False)
        self.assertEqual(state["fan_mode"], 1)

    def test_maps_api_fields(self):
        cfg = {"rgb_enable": True, "rgb_color": "#ff0000", "gpio_fan_mode": 3}
        with patch.object(api, "get_config", return_value=cfg):
            state = api.collect()
        self.assertEqual((state["rgb_enable"], state["rgb_color"], state["fan_mode"]), (True, "#ff0000", 3))


if __name__ == "__main__":
    unittest.main()
