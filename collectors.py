import re
import time
import psutil
from datetime import datetime
from helpers import run, svc_active, docker_running, get_pironman5_config
from config import (
    WG_INTERFACE, NVME_DEVICE, F2B_JAIL, FAN_INPUT, CS_ENABLE,
    SERVICES, DOCKER_SERVICES,
)


# ── Fast data (every 1s) ───────────────────────────────────
def get_fast_data():
    d = {}

    d["cpu_pct"]   = psutil.cpu_percent(interval=0.1)
    d["cpu_freq"]  = round(psutil.cpu_freq().current, 1) if psutil.cpu_freq() else 0

    ram = psutil.virtual_memory()
    d["ram_pct"]   = ram.percent
    d["ram_used"]  = ram.used  // (1024**2)
    d["ram_total"] = ram.total // (1024**2)

    try:
        t = psutil.sensors_temperatures()
        temps = t.get("cpu_thermal", t.get("coretemp", []))
        d["cpu_temp"] = round(temps[0].current, 1) if temps else 0
    except:
        d["cpu_temp"] = 0

    d["fan_rpm"] = int(run(f"cat {FAN_INPUT}") or "0") if FAN_INPUT else 0

    s = int(time.time() - psutil.boot_time())
    days, s = divmod(s, 86400)
    hrs,  s = divmod(s, 3600)
    mins    = s // 60
    d["uptime"] = f"{days}d {hrs}h {mins}m"

    d["ip"] = run("hostname -I | awk '{print $1}'") or "?.?.?.?"

    disk = psutil.disk_usage("/")
    d["disk_pct"]   = disk.percent
    d["disk_used"]  = round(disk.used  / (1024**3), 1)
    d["disk_total"] = round(disk.total / (1024**3), 1)

    wg_out = run(
        f"sudo wg show {WG_INTERFACE} latest-handshakes 2>/dev/null"
    ) if WG_INTERFACE else ""
    now    = int(time.time())
    active = total = 0
    for line in wg_out.splitlines():
        parts = line.split()
        if len(parts) == 2:
            total += 1
            if int(parts[1]) != 0 and now - int(parts[1]) < 60:
                active += 1
    d["wg_active"] = active
    d["wg_total"]  = total

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
    for line in sm.splitlines():
        if "Temperature:" in line and "Sensor" not in line:
            d["nvme_temp"] = float(line.split()[1])
            break
    else:
        d["nvme_temp"] = 0

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

    for alias, unit in SERVICES:
        d[f"svc_{alias}"] = svc_active(unit)
    for alias, container in DOCKER_SERVICES:
        d[f"svc_{alias}"] = docker_running(container)

    ufw_out = run("sudo ufw status numbered 2>/dev/null")
    ufw_lines = ufw_out.splitlines()
    d["ufw_status"] = "active" if ufw_lines and "active" in ufw_lines[0].lower() else "inactive"
    _ufw_re = re.compile(
        r'^\[\s*(\d+)\]\s+(.+?)\s+(ALLOW|DENY|REJECT|LIMIT)\s+(IN|OUT|FWD)\s+(.+)$'
    )
    rules = []
    for line in ufw_lines:
        m = _ufw_re.match(line.strip())
        if not m:
            continue
        rules.append({
            "num":    int(m.group(1)),
            "to":     m.group(2).strip(),
            "action": m.group(3) + " " + m.group(4),
            "from":   m.group(5).strip(),
        })
    d["ufw_rules"] = rules

    d["timestamp"] = datetime.now().isoformat()
    return d
