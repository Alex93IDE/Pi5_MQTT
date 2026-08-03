import json
import paho.mqtt.client as mqtt
from config import MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PASS, TOPIC_CTRL
from control import handle_control


def create_client():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASS)

    def on_connect(c, userdata, flags, rc, properties=None):
        if rc == 0:
            print("[mqtt] Connected to broker")
            c.subscribe(TOPIC_CTRL)
        else:
            print(f"[mqtt] Connection error: {rc}")

    def on_disconnect(c, userdata, flags, rc, properties=None):
        print(f"[mqtt] Disconnected ({rc}), reconnecting...")

    def on_message(c, userdata, msg):
        try:
            handle_control(json.loads(msg.payload.decode()))
        except Exception as e:
            print(f"[ctrl] {e}")

    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()
    return client
