import os
from dotenv import load_dotenv

load_dotenv()

MQTT_HOST     = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT     = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER     = os.getenv("MQTT_USER", "pi5")
MQTT_PASS     = os.getenv("MQTT_PASS", "")
TOPIC_FAST    = os.getenv("TOPIC_FAST", "pi5/fast")
TOPIC_SLOW    = os.getenv("TOPIC_SLOW", "pi5/slow")
TOPIC_CTRL    = os.getenv("TOPIC_CTRL", "pi5/control/pironman")
API           = os.getenv("PIRONMAN_API", "http://localhost:34001/api/v1.0")
INTERVAL_FAST = int(os.getenv("INTERVAL_FAST", 1))
INTERVAL_SLOW = int(os.getenv("INTERVAL_SLOW", 30))
