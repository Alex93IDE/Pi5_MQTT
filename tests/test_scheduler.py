import json
import threading
import time
import unittest
from unittest.mock import MagicMock
from pi5mqtt.scheduler import Publisher, Scheduler, merged


class Merged(unittest.TestCase):
    def test_combines_and_stamps(self):
        d = merged(lambda: {"a": 1}, lambda: {"b": 2})()
        self.assertEqual((d["a"], d["b"]), (1, 2))
        self.assertIn("timestamp", d)

    def test_without_timestamp(self):
        self.assertEqual(merged(lambda: {"a": 1}, timestamp=False)(), {"a": 1})


class Recorder:
    """A fake MQTT client that remembers when each topic was published."""

    def __init__(self):
        self.calls = []
        self.lock = threading.Lock()

    def publish(self, topic, payload, qos, retain):
        with self.lock:
            self.calls.append((time.monotonic(), topic, json.loads(payload), retain))

    def times(self, topic):
        with self.lock:
            return [t for t, tp, _, _ in self.calls if tp == topic]


class SchedulerTest(unittest.TestCase):
    def run_for(self, seconds, publishers, client):
        s = Scheduler(client, publishers)
        s.start()
        time.sleep(seconds)
        s.stop()
        return s

    def test_slow_collector_does_not_hold_up_fast_one(self):
        client = Recorder()
        fast = Publisher("fast", 0.05, lambda: {"x": 1})
        slow = Publisher("slow", 10, lambda: time.sleep(0.5) or {"y": 2})
        self.run_for(0.4, [fast, slow], client)
        # In a single loop, the blocked slow collector would allow ~1 fast tick.
        self.assertGreaterEqual(len(client.times("fast")), 6)

    def test_interval_does_not_drift_with_work_time(self):
        client = Recorder()
        # Each collection takes 30 ms of a 100 ms interval.
        p = Publisher("t", 0.1, lambda: time.sleep(0.03) or {})
        self.run_for(1.05, [p], client)
        times = client.times("t")
        # Sleeping *after* the work would give ~8 ticks (130 ms apart).
        self.assertGreaterEqual(len(times), 10)
        self.assertAlmostEqual((times[-1] - times[0]) / (len(times) - 1), 0.1, delta=0.02)

    def test_trigger_publishes_immediately(self):
        client = Recorder()
        p = Publisher("t", 60, lambda: {})
        s = Scheduler(client, [p])
        s.start()
        time.sleep(0.1)          # the first, scheduled publish
        p.trigger()
        time.sleep(0.1)
        s.stop()
        self.assertEqual(len(client.times("t")), 2)

    def test_failing_collector_keeps_running(self):
        client = Recorder()
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) % 2:
                raise RuntimeError("boom")
            return {}

        p = Publisher("t", 0.05, flaky)
        with self.assertLogs("scheduler", level="ERROR"):
            self.run_for(0.3, [p], client)
        self.assertGreaterEqual(len(calls), 4)
        self.assertGreaterEqual(len(client.times("t")), 2)

    def test_publishes_retained_json(self):
        client = MagicMock()
        Publisher("t", 1, lambda: {"a": 1}).publish(client)
        client.publish.assert_called_once_with("t", '{"a": 1}', qos=0, retain=True)

    def test_stop_is_prompt(self):
        s = Scheduler(Recorder(), [Publisher("t", 60, lambda: {})])
        s.start()
        start = time.monotonic()
        s.stop()
        self.assertLess(time.monotonic() - start, 1)


if __name__ == "__main__":
    unittest.main()
