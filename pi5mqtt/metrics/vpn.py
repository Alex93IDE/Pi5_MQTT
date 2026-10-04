"""WireGuard peers."""
import time
from ..config import WG_INTERFACE
from ..shell import sudo


def parse_wg_handshakes(text, now, window=60):
    """`wg show <if> latest-handshakes` output -> (active, total) peers.

    A peer counts as active if it shook hands within the last `window`
    seconds — WireGuard re-handshakes every two minutes while traffic flows.
    """
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


def collect():
    out = sudo(f"wg show {WG_INTERFACE} latest-handshakes") if WG_INTERFACE else ""
    active, total = parse_wg_handshakes(out, int(time.time()))
    return {"wg_active": active, "wg_total": total}
