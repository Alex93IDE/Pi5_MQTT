"""Runs each publisher on its own thread and its own clock.

Separate threads mean a slow collector (smartctl, systemctl) can't hold up
the once-a-second metrics. Each publisher keeps a fixed schedule rather
than sleeping after its work, so the interval doesn't creep by however long
the collection took.
"""
import json
import logging
import threading
import time
from datetime import datetime

log = logging.getLogger("scheduler")


def merged(*collectors, timestamp=True):
    """One collector out of several, their dicts combined into one payload."""
    def collect():
        d = {}
        for c in collectors:
            d.update(c())
        if timestamp:
            d["timestamp"] = datetime.now().isoformat()
        return d
    return collect


class Publisher:
    def __init__(self, topic, every, collect):
        self.topic   = topic
        self.every   = every
        self.collect = collect
        self._wake   = threading.Event()

    def publish(self, client):
        client.publish(self.topic, json.dumps(self.collect()), qos=0, retain=True)

    def trigger(self):
        """Publish now instead of waiting for the next tick."""
        self._wake.set()


class Scheduler:
    def __init__(self, client, publishers, clock=time.monotonic):
        self.client     = client
        self.publishers = list(publishers)
        self._clock     = clock
        self._stop      = threading.Event()
        self._threads   = []

    def start(self):
        for p in self.publishers:
            t = threading.Thread(target=self._run, args=(p,), name=p.topic, daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self):
        self._stop.set()
        for p in self.publishers:
            p._wake.set()
        for t in self._threads:
            t.join(timeout=5)

    def _run(self, p):
        next_run = self._clock()
        while not self._stop.is_set():
            triggered = p._wake.wait(max(0.0, next_run - self._clock()))
            if self._stop.is_set():
                break
            p._wake.clear()

            try:
                p.publish(self.client)
            except Exception as e:
                # One bad tick shouldn't stop the publisher.
                log.error("%s failed: %s", p.topic, e)

            if not triggered:
                next_run += p.every
                # Fell more than a whole interval behind (suspend, a very
                # slow collector): skip the missed ticks instead of bursting.
                if next_run < self._clock():
                    next_run = self._clock() + p.every
