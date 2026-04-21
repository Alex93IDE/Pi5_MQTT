import time
import psutil
from datetime import datetime
from helpers import run, svc_active, get_pironman5_config


# ── Datos rápidos (cada 1s) ────────────────────────────────
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

    d["fan_rpm"] = int(run("cat /sys/class/hwmon/hwmon0/fan1_input") or "0")

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

    wg_out = run("sudo wg show wg0 latest-handshakes 2>/dev/null")
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


# ── Datos lentos (cada 30s) ────────────────────────────────
def get_slow_data():
    d = {}

    sm = run("sudo smartctl -A /dev/nvme0")
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

    d["f2b_bans"] = run(
        "sudo fail2ban-client status sshd 2>/dev/null"
        " | grep 'Currently banned' | awk '{print $NF}'"
    ) or "0"
    d["cs_bans"] = run(
        "sudo cscli decisions list 2>/dev/null | grep -c ban"
    ) or "0"

    d["svc_wgdash"]  = svc_active("wgdashboard")
    d["svc_adguard"] = (
        run("docker inspect -f '{{.State.Running}}' adguardhome 2>/dev/null") == "true"
    )
    d["svc_cloud"]   = svc_active("cloudflared")
    d["svc_f2b"]     = svc_active("fail2ban")
    d["svc_cs"]      = svc_active("crowdsec")
    d["svc_bouncer"] = svc_active("crowdsec-firewall-bouncer")
    d["svc_softkey"] = svc_active("softkey")
    d["svc_mqtt"]    = svc_active("mosquitto")

    d["timestamp"] = datetime.now().isoformat()
    return d
