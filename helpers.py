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


def run_json(cmd):
    """Como run() pero retorna el JSON parseado o None"""
    try:
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode().strip()
        return json.loads(result)
    except:
        return None


def get_pironman5_config():
    """Lee la config actual del pironman5"""
    data = run_json(f"curl -s {API}/get-config")
    if data and data.get("status"):
        return data["data"]["system"]
    return {}
