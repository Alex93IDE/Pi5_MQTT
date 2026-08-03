# Pi5 MQTT Publisher

A small daemon that monitors a Raspberry Pi 5 (in a Pironman5 case) and exposes it over MQTT.

It publishes system metrics to two topics — the cheap stuff every second, the slower stuff every 30 — and listens on a third one for commands, so you can toggle the case RGB from a dashboard or a phone instead of SSHing in every time.

I built it for my own setup, but it's small enough that adapting it should be painless. Everything worth changing lives in `.env`.

## What it publishes

**`pi5/fast`** — once a second: CPU load, frequency and temperature, RAM, disk usage, fan RPM, uptime, local IP, active VPN peer count, and the current Pironman5 state (RGB colour, style, brightness and speed; OLED; fan mode).

**`pi5/slow`** — every 30 seconds, because these are slower or more expensive to read: NVMe health from SMART, ban counters from the host's intrusion-prevention tools, systemd status for a handful of services, and the firewall ruleset parsed into JSON.

Both payloads go out with `retain=True`, so anything that subscribes gets the last known state right away instead of waiting for the next tick.

Payload shapes are defined in `collectors.py` — that's the place to add, drop or rename fields to match your own machine.

## Control commands

Publish a JSON object to `pi5/control/pironman` with an `action` field:

| action | extra fields | what it does |
|---|---|---|
| `oled_on` / `oled_off` | — | toggle the OLED |
| `rgb_on` / `rgb_off` | — | toggle the RGB strip |
| `rgb_color` | `color` (hex, e.g. `#ff0000`) | set the colour |
| `rgb_style` | `style` (e.g. `breathing`) | set the animation |
| `rgb_brightness` | `value` (0-100) | set brightness |
| `rgb_speed` | `value` (0-100) | set animation speed |
| `fan_mode` | `mode` (0-4) | 0 = always on, 1 = performance, 2 = cool, 3 = balance, 4 = silent |

For example:

```json
{"action": "rgb_color", "color": "#00ff00"}
```

Under the hood these are HTTP calls to the Pironman5 API, which the case software runs locally.

## Requirements

A Raspberry Pi running a systemd-based distro, Python 3.9+, and an MQTT broker it can reach. The three Python dependencies are in `requirements.txt`.

Beyond that, the collectors shell out to ordinary Linux tooling — SMART, systemd, the firewall, the VPN. Whatever isn't installed simply reports zero or `false` instead of crashing, so you can run it on a bare Pi and fill in the gaps later. The Pironman5 controls need the case software running; without it the RGB and fan fields stay at their defaults.

## Getting it running

Clone it onto the Pi:

```bash
git clone <repo-url> ~/Pi5_mqtt
cd ~/Pi5_mqtt
```

Set up your config — at minimum you'll want to fill in `MQTT_PASS`:

```bash
cp .env.example .env
nano .env
```

Then run the installer:

```bash
bash install.sh
```

That creates a virtualenv, installs the Python dependencies, adds a sudoers rule so the service can read a few root-only metrics without a password, and sets up a systemd unit called `pi5_mqtt` that starts on boot.

**About that sudoers rule:** it whitelists four specific read-only commands and nothing else — no wildcards, no shell. You can see exactly which ones near the top of `install.sh`, and I'd encourage you to read them before running anything with `sudo`. If you'd rather not grant that at all, delete those lines; the affected fields just come back as zeros.

To update later:

```bash
git pull
bash update.sh
```

And `bash uninstall.sh` removes the service and the sudoers rule, leaving the repo and the virtualenv alone.

## Configuration

| variable | default | |
|---|---|---|
| `MQTT_HOST` | `localhost` | broker host |
| `MQTT_PORT` | `1883` | broker port |
| `MQTT_USER` | `pi5` | MQTT username |
| `MQTT_PASS` | — | MQTT password |
| `PIRONMAN_API` | `http://localhost:34001/api/v1.0` | Pironman5 API base URL |
| `TOPIC_FAST` | `pi5/fast` | fast metrics topic |
| `TOPIC_SLOW` | `pi5/slow` | slow metrics topic |
| `TOPIC_CTRL` | `pi5/control/pironman` | control topic |
| `INTERVAL_FAST` | `1` | fast loop interval, in seconds |
| `INTERVAL_SLOW` | `30` | slow loop interval, in seconds |

Then the host-specific half. **Leave any of these empty and that metric is skipped entirely** — no command runs, no sudoers rule is granted, the field just reports zero:

| variable | default | |
|---|---|---|
| `WG_INTERFACE` | `wg0` | VPN interface to count peers on |
| `NVME_DEVICE` | `/dev/nvme0` | drive to read SMART data from |
| `F2B_JAIL` | `sshd` | jail to read the ban counter from |
| `FAN_INPUT` | `/sys/class/hwmon/hwmon0/fan1_input` | sysfs path for fan RPM |
| `CS_ENABLE` | `false` | whether to query CrowdSec decisions |
| `SERVICES` | — | systemd units to report on |
| `DOCKER_SERVICES` | — | Docker containers to report on |

`SERVICES` and `DOCKER_SERVICES` take comma-separated `alias:unit` pairs. The alias becomes the payload key, so `mqtt:mosquitto` publishes `svc_mqtt`, which means you can rename a field without touching the code. A bare name is its own alias:

```
SERVICES=mqtt:mosquitto,vpn:wg-quick@wg0,tailscaled
DOCKER_SERVICES=dns:pihole
```

`.env` is gitignored, so both your credentials and the inventory of what runs on your machine stay on the machine.

## Security notes

Worth reading before you point this at anything:

- **The payload describes your machine.** It includes the local IP, the firewall ruleset and which services are up. That's the whole point on a private dashboard, but it's a gift to anyone else. Only publish to a broker you control, with authentication on, and use TLS if it's reachable beyond your LAN or VPN.
- **The control topic has no authorisation of its own.** Anyone who can publish to it can drive the case hardware. Broker-level ACLs are what keeps that honest.
- **Nothing here should face the internet directly.** There's no auth layer in this code, by design — it assumes it's sitting behind a broker that has one.

## Layout

```
main.py          entry point, runs the two loops
config.py        reads .env
client.py        MQTT connection and callbacks
collectors.py    gathers the fast and slow payloads
control.py       handles incoming commands
helpers.py       small shell/systemd/API utilities
install.sh       first-time setup
update.sh        run after git pull
uninstall.sh     removes the service and sudoers rule
```

## License

MIT — see [LICENSE](LICENSE). Do what you like with it.
