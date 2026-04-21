#!/usr/bin/env python3
import time
import json
from config import TOPIC_FAST, TOPIC_SLOW, INTERVAL_FAST, INTERVAL_SLOW
from client import create_client
from collectors import get_fast_data, get_slow_data


def main():
    client = create_client()
    time.sleep(1)

    last_slow = 0

    print("Publisher iniciado. Ctrl+C para salir.")
    while True:
        try:
            fast = get_fast_data()
            client.publish(TOPIC_FAST, json.dumps(fast), qos=0, retain=True)

            now = time.time()
            if now - last_slow >= INTERVAL_SLOW:
                slow = get_slow_data()
                client.publish(TOPIC_SLOW, json.dumps(slow), qos=0, retain=True)
                last_slow = now

        except Exception as e:
            print(f"[main] {e}")

        time.sleep(INTERVAL_FAST)


if __name__ == "__main__":
    main()
