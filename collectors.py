import os
import re
import time
import psutil
from datetime import datetime
from helpers import run, read_file, get_pironman5_config
from config import (
    WG_INTERFACE, NVME_DEVICE, F2B_JAIL, FAN_INPUT, CS_ENABLE, NET_INTERFACE,
)


# ── Parsers (pure, so they can be tested without the hardware) ─
_UFW_RULE = re.compile(
    r'^\[\s*(\d+)\]\s+(.+?)\s+(ALLOW|DENY|REJECT|LIMIT)\s+(IN|OUT|FWD)\s+(.+)$'
)


def parse_ufw(text):
    """`ufw status numbered` output -> (status, rules)."""
    lines = text.splitlines()
    # "Status: inactive" contains "active", so compare the word itself.
    status = "inactive"
    if lines and lines[0].lower().startswith("status:"):
        status = lines[0].split(":", 1)[1].strip().lower()
    rules = []
    for line in lines:
        m = _UFW_RULE.match(line.strip())
        if not m:
            continue
        rules.append({
            "num":    int(m.group(1)),
            "to":     m.group(2).strip(),
            "action": m.group(3) + " " + m.group(4),
            "from":   m.group(5).strip(),
        })
    return status, rules


def parse_wg_handshakes(text, now, window=60):
    """`wg show <if> latest-handshakes` output -> (active, total) peers."""
    active = total = 0
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 2 or not parts[1].isdigit():
            continue
        total += 1
        ts = int(parts[1])
        if ts != 0 and now - ts < window:
            active += 1
    return active, total


def default_route_interface(route_table):
    """Interface of the default route, from /proc/net/route contents."""
    for line in route_table.splitlines()[1:]:
        fields = line.split()
        if len(fields) > 1 and fields[1] == "00000000":
            return fields[0]
    return ""


# ── Network throughput ─────────────────────────────────────
# Rates need two samples, so the previous one lives between ticks.
_net_prev = None


def _net_interface():
    return NET_INTERFACE or default_route_interface(read_file("/proc/net/route"))


def get_net_rates():
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
    # First tick, or the default route moved to another interface.
    if prev is None or prev[0] != iface or now <= prev[1]:
        return iface, 0, 0

    elapsed = now - prev[1]
    rx = max(0, counters.bytes_recv - prev[2]) / elapsed
    tx = max(0, counters.bytes_sent - prev[3]) / elapsed
    return iface, int(rx), int(tx)


# ── Fast data (every 1s) ───────────────────────────────────
def get_fast_data():
    d = {}

    # Non-blocking: measured over the time since the previous tick.
    d["cpu_pct"]   = psutil.cpu_percent(interval=None)
    d["cpu_cores"] = psutil.cpu_percent(interval=None, percpu=True)
    freq = psutil.cpu_freq()
    d["cpu_freq"]  = round(freq.current, 1) if freq else 0
    d["load_avg"]  = [round(x, 2) for x in os.getloadavg()]

    ram = psutil.virtual_memory()
    d["ram_pct"]   = ram.percent
    d["ram_used"]  = ram.used  // (1024**2)
    d["ram_total"] = ram.total // (1024**2)

    try:
        t = psutil.sensors_temperatures()
        temps = t.get("cpu_thermal", t.get("coretemp", []))
        d["cpu_temp"] = round(temps[0].current, 1) if temps else 0
    except (AttributeError, OSError):
        d["cpu_temp"] = 0

    rpm = read_file(FAN_INPUT) if FAN_INPUT else ""
    d["fan_rpm"] = int(rpm) if rpm.isdigit() else 0

    s = int(time.time() - psutil.boot_time())
    days, s = divmod(s, 86400)
    hrs,  s = divmod(s, 3600)
    mins    = s // 60
    d["uptime"] = f"{days}d {hrs}h {mins}m"

    d["ip"] = run("hostname -I | awk '{print $1}'") or "?.?.?.?"

    iface, rx, tx = get_net_rates()
    d["net_iface"] = iface
    d["net_rx"]    = rx
    d["net_tx"]    = tx

    disk = psutil.disk_usage("/")
    d["disk_pct"]   = disk.percent
    d["disk_used"]  = round(disk.used  / (1024**3), 1)
    d["disk_total"] = round(disk.total / (1024**3), 1)

    wg_out = run(
        f"sudo wg show {WG_INTERFACE} latest-handshakes 2>/dev/null"
    ) if WG_INTERFACE else ""
    d["wg_active"], d["wg_total"] = parse_wg_handshakes(wg_out, int(time.time()))

    pm_cfg = get_pironman5_config()
    d["rgb_enable"]     = pm_cfg.get("rgb_enable", False)
    d["rgb_color"]      = pm_cfg.get("rgb_color", "#000000")
    d["rgb_style"]      = pm_cfg.get("rgb_style", "")
    d["rgb_brightness"] = pm_cfg.get("rgb_brightness", 0)
    d["rgb_speed"]      = pm_cfg.get("rgb_speed", 0)
    d["oled_enable"]    = pm_cfg.get("oled_enable", False)
    d["fan_mode"]       = pm_cfg.get("gpio_fan_mode", 1)

    d["timestamp"] = datetime.now().isoformat()
    return d


# ── Slow data (every 30s) ──────────────────────────────────
def get_slow_data():
    d = {}

    sm = run(f"sudo smartctl -A {NVME_DEVICE}") if NVME_DEVICE else ""
    d["nvme_temp"] = 0
    for line in sm.splitlines():
        if "Temperature:" in line and "Sensor" not in line:
            try:
                d["nvme_temp"] = float(line.split()[1])
            except (IndexError, ValueError):
                pass
            break

    def sm_val(keyword):
        for line in sm.splitlines():
            if keyword in line:
                return line.split()[-1]
        return "?"

    d["nvme_spare"]  = sm_val("Available Spare:")
    d["nvme_used"]   = sm_val("Percentage Used:")
    d["nvme_hours"]  = sm_val("Power On Hours:")
    d["nvme_unsafe"] = sm_val("Unsafe Shutdowns:")
    d["nvme_errors"] = sm_val("Media and Data Integrity Errors:")

    d["f2b_bans"] = (run(
        f"sudo fail2ban-client status {F2B_JAIL} 2>/dev/null"
        " | grep 'Currently banned' | awk '{print $NF}'"
    ) or "0") if F2B_JAIL else "0"
    d["cs_bans"] = (run(
        "sudo cscli decisions list 2>/dev/null | grep -c ban"
    ) or "0") if CS_ENABLE else "0"

    d["ufw_status"], d["ufw_rules"] = parse_ufw(run("sudo ufw status numbered 2>/dev/null"))

    d["timestamp"] = datetime.now().isoformat()
    return d
