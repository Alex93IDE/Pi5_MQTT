# Pi5 MQTT Publisher

A small daemon that monitors a Raspberry Pi 5 (in a Pironman5 case) and exposes it over MQTT.

It publishes system metrics — the cheap stuff every second, the slower stuff every 30 — plus the full list of systemd services and Docker containers, and listens for commands, so you can toggle the case RGB or pick which services to feature from a dashboard or a phone instead of SSHing in every time. It can also serve that dashboard itself.

I built it for my own setup, but it's small enough that adapting it should be painless. Everything worth changing lives in `.env`.

## What it publishes

**`pi5/fast`** — once a second: CPU load, frequency and temperature, RAM, disk usage, fan RPM, uptime, local IP, active VPN peer count, and the current Pironman5 state (RGB colour, style, brightness and speed; OLED; fan mode).

**`pi5/slow`** — every 30 seconds, because these are slower or more expensive to read: NVMe health from SMART, ban counters from the host's intrusion-prevention tools, and the firewall ruleset parsed into JSON.

**`pi5/services`** — every 30 seconds: every systemd service unit, running or not, as a list:

```json
[{"name": "mosquitto.service", "active": "active", "sub": "running", "enabled": "enabled", "description": "Mosquitto MQTT Broker", "favorite": true}]
```

Most of the list will be `inactive` — timer jobs between runs, on-demand and boot-only units — and that's normal. `enabled` is the unit file state (`enabled`, `disabled`, `static`, `masked`, …, or empty when there's no unit file), so a dashboard can tell a unit that's meant to be idle from an `enabled` one that isn't running.

**`pi5/docker`** — every 30 seconds: every Docker container, running or not. An empty list if Docker isn't installed or the service user can't reach it:

```json
[{"name": "pihole", "image": "pihole/pihole", "state": "running", "status": "Up 3 days", "favorite": false}]
```

Every topic goes out with `retain=True`, so anything that subscribes gets the last known state right away instead of waiting for the next tick.

Payload shapes are defined in `collectors.py` and `services.py` — that's the place to add, drop or rename fields to match your own machine.

## Control commands

Publish a JSON object to `pi5/control/pironman` with an `action` field:

| action | extra fields | what it does |
|---|---|---|
| `oled_on` / `oled_off` | — | toggle the OLED |
| `rgb_on` / `rgb_off` | — | toggle the RGB strip |
| `rgb_color` | `color`: `#rrggbb`, e.g. `#ff0000` | set the colour |
| `rgb_style` | `style`: lowercase name, e.g. `breathing` | set the animation |
| `rgb_brightness` | `value`: integer 0-100 | set brightness |
| `rgb_speed` | `value`: integer 0-100 | set animation speed |
| `fan_mode` | `mode`: integer 0-4 | 0 = always on, 1 = performance, 2 = cool, 3 = balance, 4 = silent |

For example:

```json
{"action": "rgb_color", "color": "#00ff00"}
```

The extra fields are required and checked before anything is sent: a malformed colour, an out-of-range number or a string where a number belongs is logged and dropped, never passed on. Valid commands become JSON POSTs to the Pironman5 API, which the case software runs locally — no shell is involved, so nothing in a payload can end up executed.

### Favourites

Each entry in `pi5/services` and `pi5/docker` carries a `favorite` flag, so a dashboard can pick which ones to feature. To change one, publish to `pi5/control/services`:

```json
{"action": "favorite", "source": "systemd", "name": "mosquitto.service", "value": true}
```

`source` is `systemd` or `docker`, and `name` has to match an entry that currently exists. The daemon saves the change to `favorites.json` next to the code (gitignored, survives restarts and updates) and republishes that topic straight away, so the new flag shows up within a moment instead of on the next 30-second tick.

## Requirements

A Raspberry Pi running a systemd-based distro, Python 3.9+, and an MQTT broker it can reach. The three Python dependencies are in `requirements.txt`.

Beyond that, the collectors shell out to ordinary Linux tooling — SMART, systemd, the firewall, the VPN. Whatever isn't installed simply reports zero, `false` or an empty list instead of crashing, so you can run it on a bare Pi and fill in the gaps later. The Pironman5 controls need the case software running; without it the RGB and fan fields stay at their defaults.

Two things worth knowing for the service lists: `pi5/services` needs systemd 246 or newer (Raspberry Pi OS Bookworm ships 252), and `pi5/docker` only fills in if the user the service runs as can talk to Docker — usually that means `sudo usermod -aG docker $USER` and a restart of the service.

## Getting it running

Clone it onto the Pi:

```bash
git clone https://github.com/Alex93IDE/Pi5_MQTT.git ~/Pi5_mqtt
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

**About that sudoers rule:** it whitelists five specific read-only commands and nothing else — no wildcards, no shell. You can see exactly which ones near the top of `install.sh`, and I'd encourage you to read them before running anything with `sudo`. If you'd rather not grant that at all, delete those lines; the affected fields just come back as zeros.

To update later:

```bash
git pull
bash update.sh
```

And `bash uninstall.sh` removes the service and the sudoers rule, leaving the repo, the virtualenv and your `favorites.json` alone.

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
| `TOPIC_SERVICES` | `pi5/services` | systemd services topic |
| `TOPIC_DOCKER` | `pi5/docker` | Docker containers topic |
| `TOPIC_CTRL_SERVICES` | `pi5/control/services` | favourites control topic |
| `INTERVAL_FAST` | `1` | fast loop interval, in seconds |
| `INTERVAL_SLOW` | `30` | slow loop interval, in seconds |
| `HTTP_HOST` | `0.0.0.0` | interface the dashboard server listens on |
| `HTTP_PORT` | — | port to serve the dashboard on; empty disables it |
| `WEB_ROOT` | `public` | folder the dashboard is served from |

Then the host-specific half. **Leave any of these empty and that metric is skipped entirely** — no command runs, no sudoers rule is granted, the field just reports zero:

| variable | default | |
|---|---|---|
| `WG_INTERFACE` | `wg0` | VPN interface to count peers on |
| `NVME_DEVICE` | `/dev/nvme0` | drive to read SMART data from |
| `F2B_JAIL` | `sshd` | jail to read the ban counter from |
| `FAN_INPUT` | `/sys/class/hwmon/hwmon0/fan1_input` | sysfs path for fan RPM |
| `CS_ENABLE` | `false` | whether to query CrowdSec decisions |

`.env` is gitignored, so your credentials stay on the machine.

## Serving the dashboard

The daemon can also serve [Pi5 Dashboard](https://github.com/Alex93IDE/Pi5_Dashboard) itself, so you don't need nginx for a LAN or VPN setup. Set `HTTP_PORT` in `.env`, then point the dashboard's `DEPLOY_TARGET` at this repo's `public/` folder and run `npm run deploy` there:

```
DEPLOY_TARGET=user@pi:~/Pi5_mqtt/public/
```

No restart needed after a deploy — files are read on every request. Unknown routes fall back to `index.html`, so reloading the page on any route works. The browser still talks to the broker over its WebSocket listener; this only hands out the files.

It's plain HTTP with no auth, so keep it on your LAN or VPN and let ufw decide who gets in. The examples use port 3010, as in `.env.example`; the browser also needs to reach the broker's WebSocket port, so open that one to the same networks:

```bash
sudo ufw allow from 192.168.1.0/24 to any port 3010 proto tcp comment 'pi5_dash'
sudo ufw allow in on wg0 to any port 3010 proto tcp comment 'pi5_dash'
sudo ufw allow from 192.168.1.0/24 to any port 9001 proto tcp comment 'mqtt ws'
sudo ufw allow in on wg0 to any port 9001 proto tcp comment 'mqtt ws'
```

## Security notes

Worth reading before you point this at anything:

- **The payload describes your machine.** It includes the local IP, the firewall ruleset and the full list of services and containers on the machine. That's the whole point on a private dashboard, but it's a gift to anyone else. Only publish to a broker you control, with authentication on, and use TLS if it's reachable beyond your LAN or VPN.
- **The control topics have no authorisation of their own.** Anyone who can publish to them can drive the case hardware or change favourites. Broker-level ACLs are what keeps that honest.
- **Nothing here should face the internet directly.** There's no auth layer in this code, by design — it assumes it's sitting behind a broker that has one.

## Layout

```
main.py          entry point, runs the fast and slow loops
config.py        reads .env
client.py        MQTT connection and callbacks
collectors.py    gathers the fast and slow payloads
control.py       handles incoming commands
services.py      systemd/Docker topics and favourites
server.py        optional static server for the dashboard
helpers.py       small shell and API utilities
install.sh       first-time setup
update.sh        run after git pull
uninstall.sh     removes the service and sudoers rule
```

## License

MIT — see [LICENSE](LICENSE). Do what you like with it.
