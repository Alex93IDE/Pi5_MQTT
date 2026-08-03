import os
from dotenv import load_dotenv

load_dotenv()


def _services(raw):
    """Parse "alias:unit,alias:unit" into [(alias, unit), ...].

    The alias becomes the payload key (svc_<alias>), so you can rename a
    field without touching the code. A bare "unit" is its own alias.
    """
    out = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        alias, _, unit = item.partition(":")
        out.append((alias, unit or alias))
    return out


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

# Host-specific bits. Leave any of these empty to skip that metric entirely.
WG_INTERFACE    = os.getenv("WG_INTERFACE", "wg0")
NVME_DEVICE     = os.getenv("NVME_DEVICE", "/dev/nvme0")
F2B_JAIL        = os.getenv("F2B_JAIL", "sshd")
FAN_INPUT       = os.getenv("FAN_INPUT", "/sys/class/hwmon/hwmon0/fan1_input")
CS_ENABLE       = os.getenv("CS_ENABLE", "false").lower() == "true"

# Which services to report on, as alias:unit pairs. Empty means none.
SERVICES        = _services(os.getenv("SERVICES", ""))
DOCKER_SERVICES = _services(os.getenv("DOCKER_SERVICES", ""))
