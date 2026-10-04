import os
from dotenv import load_dotenv

# The repo root: .env, favorites.json and public/ live here, one level
# above this package.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

load_dotenv(os.path.join(BASE_DIR, ".env"))


MQTT_HOST     = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT     = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER     = os.getenv("MQTT_USER", "pi5")
MQTT_PASS     = os.getenv("MQTT_PASS", "")
TOPIC_FAST    = os.getenv("TOPIC_FAST", "pi5/fast")
TOPIC_SLOW    = os.getenv("TOPIC_SLOW", "pi5/slow")
TOPIC_CTRL    = os.getenv("TOPIC_CTRL", "pi5/control/pironman")
TOPIC_SERVICES      = os.getenv("TOPIC_SERVICES", "pi5/services")
TOPIC_DOCKER        = os.getenv("TOPIC_DOCKER", "pi5/docker")
TOPIC_CTRL_SERVICES = os.getenv("TOPIC_CTRL_SERVICES", "pi5/control/services")
TOPIC_STATUS        = os.getenv("TOPIC_STATUS", "pi5/status")
API           = os.getenv("PIRONMAN_API", "http://localhost:34001/api/v1.0")
INTERVAL_FAST = float(os.getenv("INTERVAL_FAST", 1))
INTERVAL_SLOW = float(os.getenv("INTERVAL_SLOW", 30))

# Optional static server for the dashboard. Leave HTTP_PORT empty to disable.
HTTP_HOST     = os.getenv("HTTP_HOST", "0.0.0.0")
HTTP_PORT     = int(os.getenv("HTTP_PORT") or 0)
WEB_ROOT      = os.path.join(BASE_DIR, os.getenv("WEB_ROOT", "public"))

FAVORITES_FILE = os.path.join(BASE_DIR, "favorites.json")

# Host-specific bits. Leave any of these empty to skip that metric entirely.
WG_INTERFACE    = os.getenv("WG_INTERFACE", "wg0")
NVME_DEVICE     = os.getenv("NVME_DEVICE", "/dev/nvme0")
F2B_JAIL        = os.getenv("F2B_JAIL", "sshd")
FAN_INPUT       = os.getenv("FAN_INPUT", "/sys/class/hwmon/hwmon0/fan1_input")
CS_ENABLE       = os.getenv("CS_ENABLE", "false").lower() == "true"
# Interface to measure throughput on. Empty follows the default route.
NET_INTERFACE   = os.getenv("NET_INTERFACE", "")
