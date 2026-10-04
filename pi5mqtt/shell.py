import subprocess
import json


def run(cmd):
    """Run a shell command and return its stripped output, or "" on failure."""
    try:
        return subprocess.check_output(
            cmd, shell=True, stderr=subprocess.DEVNULL
        ).decode().strip()
    except (subprocess.CalledProcessError, OSError, UnicodeDecodeError):
        return ""


def sudo(cmd):
    """run() as root via the sudoers rules install.sh sets up.

    -n makes sudo fail straight away instead of waiting for a password
    nobody is going to type, if a rule is missing.
    """
    return run(f"sudo -n {cmd}")


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
