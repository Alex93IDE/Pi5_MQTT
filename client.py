import json
import logging
import paho.mqtt.client as mqtt
from config import (
    MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PASS,
    TOPIC_CTRL, TOPIC_CTRL_SERVICES, TOPIC_STATUS,
)
from control import handle_control
from services import handle_services_control

log = logging.getLogger("mqtt")


def create_client():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    # If the daemon dies or the Pi drops off the network, the broker
    # publishes this for us — otherwise the retained metrics would keep
    # looking current forever.
    client.will_set(TOPIC_STATUS, "offline", qos=1, retain=True)

    def on_connect(c, userdata, flags, rc, properties=None):
        if rc == 0:
            log.info("Connected to broker")
            c.publish(TOPIC_STATUS, "online", qos=1, retain=True)
            c.subscribe([(TOPIC_CTRL, 0), (TOPIC_CTRL_SERVICES, 0)])
        else:
            log.error("Connection error: %s", rc)

    def on_disconnect(c, userdata, flags, rc, properties=None):
        log.warning("Disconnected (%s), reconnecting...", rc)

    def on_message(c, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
        except (UnicodeDecodeError, ValueError):
            log.warning("Ignoring non-JSON message on %s", msg.topic)
            return
        if not isinstance(payload, dict):
            log.warning("Ignoring non-object message on %s", msg.topic)
            return
        try:
            if msg.topic == TOPIC_CTRL_SERVICES:
                handle_services_control(c, payload)
            else:
                handle_control(payload)
        except Exception:
            # A bug in a handler must not take down paho's network thread.
            log.exception("Control handler failed")

    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()
    return client


def shutdown(client):
    """Clean exit: say so before leaving, since the will only fires on a crash."""
    info = client.publish(TOPIC_STATUS, "offline", qos=1, retain=True)
    try:
        info.wait_for_publish(timeout=2)
    except (RuntimeError, ValueError):
        pass
    client.disconnect()
    client.loop_stop()
