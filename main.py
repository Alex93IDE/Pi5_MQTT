#!/usr/bin/env python3
import sys
import time
import json
import signal
import logging
from config import TOPIC_FAST, TOPIC_SLOW, INTERVAL_FAST, INTERVAL_SLOW
from client import create_client, shutdown
from collectors import get_fast_data, get_slow_data
from server import start_server
from services import publish_all as publish_services

log = logging.getLogger("main")


def main():
    # journald adds its own timestamps.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    # systemctl stop sends SIGTERM; turn it into a normal exit so the
    # finally block below gets to announce we're going offline.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    start_server()
    client = create_client()
    time.sleep(1)

    last_slow = 0

    log.info("Publisher started. Ctrl+C to exit.")
    try:
        while True:
            try:
                fast = get_fast_data()
                client.publish(TOPIC_FAST, json.dumps(fast), qos=0, retain=True)

                now = time.time()
                if now - last_slow >= INTERVAL_SLOW:
                    slow = get_slow_data()
                    client.publish(TOPIC_SLOW, json.dumps(slow), qos=0, retain=True)
                    publish_services(client)
                    last_slow = now

            except Exception as e:
                # One bad tick shouldn't stop the publisher.
                log.error("Tick failed: %s", e)

            time.sleep(INTERVAL_FAST)
    except KeyboardInterrupt:
        pass
    finally:
        log.info("Shutting down")
        shutdown(client)


if __name__ == "__main__":
    main()
