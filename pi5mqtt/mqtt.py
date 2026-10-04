import json
import logging
import paho.mqtt.client as mqtt
from .config import MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PASS, TOPIC_STATUS

log = logging.getLogger("mqtt")


def create_client(routes):
    """Connect to the broker and dispatch incoming messages.

    `routes` maps each control topic to a handler that takes the decoded
    JSON object. The connection is made in the background and retried
    until the broker answers, so starting before Mosquitto is fine.
    """
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    # If the daemon dies or the Pi drops off the network, the broker
    # publishes this for us — otherwise the retained metrics would keep
    # looking current forever.
    client.will_set(TOPIC_STATUS, "offline", qos=1, retain=True)
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    def on_connect(c, userdata, flags, rc, properties=None):
        if rc == 0:
            log.info("Connected to broker")
            c.publish(TOPIC_STATUS, "online", qos=1, retain=True)
            if routes:
                c.subscribe([(topic, 0) for topic in routes])
        else:
            log.error("Connection error: %s", rc)

    def on_disconnect(c, userdata, flags, rc, properties=None):
        if rc == 0:
            log.info("Disconnected")   # we asked to, on shutdown
        else:
            log.warning("Disconnected (%s), reconnecting...", rc)

    def on_message(c, userdata, msg):
        handler = routes.get(msg.topic)
        if handler is None:
            return
        try:
            payload = json.loads(msg.payload.decode())
        except (UnicodeDecodeError, ValueError):
            log.warning("Ignoring non-JSON message on %s", msg.topic)
            return
        if not isinstance(payload, dict):
            log.warning("Ignoring non-object message on %s", msg.topic)
            return
        try:
            handler(payload)
        except Exception:
            # A bug in a handler must not take down paho's network thread.
            log.exception("Handler for %s failed", msg.topic)

    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message
    client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=60)
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
