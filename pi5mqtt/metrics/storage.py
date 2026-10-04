"""NVMe health from SMART."""
from ..config import NVME_DEVICE
from ..shell import sudo

# Payload key -> the line smartctl prints it on.
_FIELDS = {
    "nvme_spare":  "Available Spare:",
    "nvme_used":   "Percentage Used:",
    "nvme_hours":  "Power On Hours:",
    "nvme_unsafe": "Unsafe Shutdowns:",
    "nvme_errors": "Media and Data Integrity Errors:",
}


def parse_smart(text):
    """`smartctl -A` output for an NVMe drive -> payload fields.

    Values stay as smartctl prints them ("100%", "3,234"); anything missing
    is "?" and a missing temperature is 0.
    """
    lines = text.splitlines()
    d = {"nvme_temp": 0}
    for line in lines:
        # "Temperature Sensor 1:" lines are per-sensor; the plain one is the drive.
        if "Temperature:" in line and "Sensor" not in line:
            try:
                d["nvme_temp"] = float(line.split()[1])
            except (IndexError, ValueError):
                pass
            break

    for key, label in _FIELDS.items():
        d[key] = next((l.split()[-1] for l in lines if label in l), "?")
    return d


def collect():
    return parse_smart(sudo(f"smartctl -A {NVME_DEVICE}") if NVME_DEVICE else "")
