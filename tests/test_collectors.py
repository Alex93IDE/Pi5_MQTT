import unittest
from collectors import parse_ufw, parse_wg_handshakes, default_route_interface

UFW_ACTIVE = """Status: active

     To                         Action      From
     --                         ------      ----
[ 1] 22/tcp                     ALLOW IN    192.168.1.0/24             # SSH
[ 2] 53                         ALLOW IN    Anywhere
[10] 9001/tcp                   ALLOW IN    10.8.0.0/24                # mqtt ws
[11] 22/tcp (v6)                DENY IN     Anywhere (v6)
"""


class ParseUfw(unittest.TestCase):
    def test_active_with_rules(self):
        status, rules = parse_ufw(UFW_ACTIVE)
        self.assertEqual(status, "active")
        self.assertEqual(len(rules), 4)
        self.assertEqual(rules[0], {
            "num": 1, "to": "22/tcp", "action": "ALLOW IN", "from": "192.168.1.0/24             # SSH",
        })
        self.assertEqual(rules[2]["num"], 10)
        self.assertEqual(rules[3]["to"], "22/tcp (v6)")
        self.assertEqual(rules[3]["action"], "DENY IN")

    def test_inactive_is_not_mistaken_for_active(self):
        # "inactive" contains "active" — this used to be reported as active.
        self.assertEqual(parse_ufw("Status: inactive\n"), ("inactive", []))

    def test_no_output(self):
        # ufw missing, or sudo refused.
        self.assertEqual(parse_ufw(""), ("inactive", []))


class ParseWireguard(unittest.TestCase):
    def test_counts_recent_handshakes_only(self):
        out = "peerA=\t995\npeerB=\t900\npeerC=\t0\n"
        self.assertEqual(parse_wg_handshakes(out, now=1000), (1, 3))

    def test_ignores_garbage(self):
        self.assertEqual(parse_wg_handshakes("not a peer line\nx y z\npeer=\tabc\n", now=1000), (0, 0))

    def test_empty(self):
        self.assertEqual(parse_wg_handshakes("", now=1000), (0, 0))


class DefaultRoute(unittest.TestCase):
    ROUTES = (
        "Iface\tDestination\tGateway \tFlags\n"
        "wg0\t0008000A\t00000000\t0001\n"
        "eth0\t00000000\t0101A8C0\t0003\n"
        "eth0\t0001A8C0\t00000000\t0001\n"
    )

    def test_finds_default_route(self):
        self.assertEqual(default_route_interface(self.ROUTES), "eth0")

    def test_no_default_route(self):
        self.assertEqual(default_route_interface("Iface\tDestination\nwg0\t0008000A\n"), "")
        self.assertEqual(default_route_interface(""), "")


if __name__ == "__main__":
    unittest.main()
