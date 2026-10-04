"""Fail2ban and CrowdSec ban counters, and the ufw ruleset."""
import re
from ..config import F2B_JAIL, CS_ENABLE
from ..shell import sudo

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


def _f2b_bans():
    if not F2B_JAIL:
        return "0"
    out = sudo(f"fail2ban-client status {F2B_JAIL}")
    for line in out.splitlines():
        if "Currently banned" in line:
            return line.split()[-1]
    return "0"


def _cs_bans():
    if not CS_ENABLE:
        return "0"
    out = sudo("cscli decisions list")
    return str(sum(1 for line in out.splitlines() if "ban" in line))


def collect():
    status, rules = parse_ufw(sudo("ufw status numbered"))
    return {
        "f2b_bans":   _f2b_bans(),
        "cs_bans":    _cs_bans(),
        "ufw_status": status,
        "ufw_rules":  rules,
    }
