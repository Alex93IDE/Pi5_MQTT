"""What gets published where, and who handles which command.

This is the one place to touch when adding a topic: write a function that
returns the payload, then add a Publisher for it below.
"""
import logging
import signal
import threading
from .config import (
    TOPIC_FAST, TOPIC_SLOW, TOPIC_SERVICES, TOPIC_DOCKER,
    TOPIC_CTRL, TOPIC_CTRL_SERVICES, INTERVAL_FAST, INTERVAL_SLOW,
)
from .metrics import system, vpn, storage, security
from .pironman import api as pironman, control as pironman_control
from .services import systemd, docker, control as services_control
from .scheduler import Publisher, Scheduler, merged
from .mqtt import create_client, shutdown
from .web import start_server
from . import __version__

log = logging.getLogger("main")


def build_publishers():
    return {
        "fast":    Publisher(TOPIC_FAST, INTERVAL_FAST, merged(system.collect, vpn.collect, pironman.collect)),
        "slow":    Publisher(TOPIC_SLOW, INTERVAL_SLOW, merged(storage.collect, security.collect)),
        "systemd": Publisher(TOPIC_SERVICES, INTERVAL_SLOW, systemd.collect),
        "docker":  Publisher(TOPIC_DOCKER, INTERVAL_SLOW, docker.collect),
    }


def build_routes(publishers):
    def on_favorite(payload):
        changed = services_control.handle(payload)
        if changed:
            # Show the new star within a moment, not on the next slow tick.
            publishers[changed].trigger()

    return {
        TOPIC_CTRL:          pironman_control.handle,
        TOPIC_CTRL_SERVICES: on_favorite,
    }


def main():
    # journald adds its own timestamps.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")

    stop = threading.Event()
    # systemctl stop sends SIGTERM; Ctrl+C sends SIGINT. Both end up below.
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT,  lambda *_: stop.set())

    start_server()
    publishers = build_publishers()
    client     = create_client(build_routes(publishers))
    scheduler  = Scheduler(client, publishers.values())
    scheduler.start()
    log.info("Publisher v%s started. Ctrl+C to exit.", __version__)

    while not stop.wait(1):
        pass

    log.info("Shutting down")
    scheduler.stop()
    shutdown(client)
