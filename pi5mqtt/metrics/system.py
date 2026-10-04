"""CPU, memory, disk, network and uptime — cheap enough to read every second."""
import os
import time
import psutil
from ..config import FAN_INPUT, NET_INTERFACE
from ..shell import run, read_file


def default_route_interface(route_table):
    """Interface of the default route, from /proc/net/route contents."""
    for line in route_table.splitlines()[1:]:
        fields = line.split()
        if len(fields) > 1 and fields[1] == "00000000":
            return fields[0]
    return ""


def format_uptime(seconds):
    days, s = divmod(int(seconds), 86400)
    hrs,  s = divmod(s, 3600)
    return f"{days}d {hrs}h {s // 60}m"


# ── Network throughput ─────────────────────────────────────
# Rates need two samples, so the previous one lives between calls.
_net_prev = None


def _net_interface():
    return NET_INTERFACE or default_route_interface(read_file("/proc/net/route"))


def net_rates():
    """(interface, rx bytes/s, tx bytes/s) since the previous call."""
    global _net_prev
    iface = _net_interface()
    counters = psutil.net_io_counters(pernic=True).get(iface)
    if counters is None:
        _net_prev = None
        return iface, 0, 0

    now = time.monotonic()
    sample = (iface, now, counters.bytes_recv, counters.bytes_sent)
    prev, _net_prev = _net_prev, sample
    # First call, or the default route moved to another interface.
    if prev is None or prev[0] != iface or now <= prev[1]:
        return iface, 0, 0

    elapsed = now - prev[1]
    rx = max(0, counters.bytes_recv - prev[2]) / elapsed
    tx = max(0, counters.bytes_sent - prev[3]) / elapsed
    return iface, int(rx), int(tx)


def _cpu_temp():
    try:
        t = psutil.sensors_temperatures()
    except (AttributeError, OSError):
        return 0
    temps = t.get("cpu_thermal", t.get("coretemp", []))
    return round(temps[0].current, 1) if temps else 0


def collect():
    d = {}

    # Non-blocking: measured over the time since the previous call.
    d["cpu_pct"]   = psutil.cpu_percent(interval=None)
    d["cpu_cores"] = psutil.cpu_percent(interval=None, percpu=True)
    freq = psutil.cpu_freq()
    d["cpu_freq"]  = round(freq.current, 1) if freq else 0
    d["load_avg"]  = [round(x, 2) for x in os.getloadavg()]
    d["cpu_temp"]  = _cpu_temp()

    ram = psutil.virtual_memory()
    d["ram_pct"]   = ram.percent
    d["ram_used"]  = ram.used  // (1024**2)
    d["ram_total"] = ram.total // (1024**2)

    disk = psutil.disk_usage("/")
    d["disk_pct"]   = disk.percent
    d["disk_used"]  = round(disk.used  / (1024**3), 1)
    d["disk_total"] = round(disk.total / (1024**3), 1)

    rpm = read_file(FAN_INPUT) if FAN_INPUT else ""
    d["fan_rpm"] = int(rpm) if rpm.isdigit() else 0

    d["uptime"] = format_uptime(time.time() - psutil.boot_time())
    d["ip"]     = run("hostname -I | awk '{print $1}'") or "?.?.?.?"

    d["net_iface"], d["net_rx"], d["net_tx"] = net_rates()
    return d
