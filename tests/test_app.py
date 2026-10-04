import unittest
from unittest.mock import patch
from pi5mqtt import app
from pi5mqtt.config import (
    TOPIC_FAST, TOPIC_SLOW, TOPIC_SERVICES, TOPIC_DOCKER, TOPIC_CTRL, TOPIC_CTRL_SERVICES,
)


class Wiring(unittest.TestCase):
    def test_every_topic_has_a_publisher(self):
        topics = {p.topic for p in app.build_publishers().values()}
        self.assertEqual(topics, {TOPIC_FAST, TOPIC_SLOW, TOPIC_SERVICES, TOPIC_DOCKER})

    def test_control_topics_are_routed(self):
        routes = app.build_routes(app.build_publishers())
        self.assertEqual(set(routes), {TOPIC_CTRL, TOPIC_CTRL_SERVICES})

    def test_favorite_change_republishes_that_source(self):
        publishers = app.build_publishers()
        routes = app.build_routes(publishers)
        with patch.object(app.services_control, "handle", return_value="docker"), \
             patch.object(publishers["docker"], "trigger") as docker_trigger, \
             patch.object(publishers["systemd"], "trigger") as systemd_trigger:
            routes[TOPIC_CTRL_SERVICES]({"action": "favorite"})
        docker_trigger.assert_called_once()
        systemd_trigger.assert_not_called()

    def test_rejected_favorite_republishes_nothing(self):
        publishers = app.build_publishers()
        routes = app.build_routes(publishers)
        with patch.object(app.services_control, "handle", return_value=None), \
             patch.object(publishers["systemd"], "trigger") as trigger:
            routes[TOPIC_CTRL_SERVICES]({})
        trigger.assert_not_called()


if __name__ == "__main__":
    unittest.main()
