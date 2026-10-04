import subprocess
import json
import urllib.request
from config import API


def run(cmd):
    """Run a shell command and return its stripped output, or "" on failure."""
    try:
        return subprocess.check_output(
            cmd, shell=True, stderr=subprocess.DEVNULL
        ).decode().strip()
    except (subprocess.CalledProcessError, OSError, UnicodeDecodeError):
        return ""


def run_json(cmd):
    """Like run() but returns the parsed JSON, or None on failure"""
    try:
        return json.loads(run(cmd))
    except ValueError:
        return None


def read_file(path):
    """Contents of a small text file (sysfs, procfs), or "" if unreadable."""
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return ""


def get_pironman5_config():
    """Read the current Pironman5 configuration"""
    try:
        with urllib.request.urlopen(f"{API}/get-config", timeout=2) as r:
            data = json.load(r)
    except (OSError, ValueError):
        return {}
    if isinstance(data, dict) and data.get("status"):
        return data.get("data", {}).get("system", {})
    return {}
