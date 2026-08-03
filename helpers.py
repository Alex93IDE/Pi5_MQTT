import subprocess
import json
from config import API


def run(cmd):
    try:
        return subprocess.check_output(
            cmd, shell=True, stderr=subprocess.DEVNULL
        ).decode().strip()
    except:
        return ""


def svc_active(name):
    return run(f"systemctl is-active {name}") == "active"


def docker_running(name):
    """True if the named Docker container is up"""
    cmd = "docker inspect -f '{{.State.Running}}' " + name + " 2>/dev/null"
    return run(cmd) == "true"


def run_json(cmd):
    """Like run() but returns the parsed JSON, or None on failure"""
    try:
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode().strip()
        return json.loads(result)
    except:
        return None


def get_pironman5_config():
    """Read the current Pironman5 configuration"""
    data = run_json(f"curl -s {API}/get-config")
    if data and data.get("status"):
        return data["data"]["system"]
    return {}
