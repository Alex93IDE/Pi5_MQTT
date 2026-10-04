# Pi5 MQTT Publisher

A small daemon that monitors a Raspberry Pi 5 (in a Pironman5 case) and exposes it over MQTT.

It publishes system metrics — the cheap stuff every second, the slower stuff every 30 — along with everything systemd and Docker are running. It also listens for commands, so you can change the case lighting or pick your favourite services from a dashboard or a phone instead of SSHing in every time.

If you use [the dashboard](https://github.com/Alex93IDE/Pi5_Dashboard) that goes with it, the daemon can serve that too, so there's nothing else to set up.

I built it for my own setup, but it's small enough that adapting it should be painless. Everything worth changing lives in `.env`.

## What it publishes

**`pi5/fast`** — once a second: CPU load (overall and per core), frequency, temperature and load average, RAM, disk usage, network traffic, fan RPM, uptime, local IP, active VPN peer count, and the current Pironman5 state (RGB colour, style, brightness and speed; OLED; fan mode).

Network traffic is `net_rx` and `net_tx`, in bytes per second, measured on whichever interface your internet goes through (`net_iface` says which one). Set `NET_INTERFACE` if you'd rather watch a different one.

**`pi5/slow`** — every 30 seconds, because these are slower or more expensive to read: NVMe health from SMART, ban counters from the host's intrusion-prevention tools, and the firewall ruleset parsed into JSON.

**`pi5/services`** — every 30 seconds: every systemd service on the machine, whether it's running or not. Each one looks like this:

```json
{
  "name": "mosquitto.service",
  "active": "active",
  "sub": "running",
  "enabled": "enabled",
  "description": "Mosquitto MQTT Broker",
  "favorite": true
}
```

Don't be alarmed when most of the list says `inactive`. Plenty of services only run for a moment — a nightly cleanup, something that fires at boot, something that waits until it's needed — and sit idle the rest of the time. The one to watch for is `failed`. `enabled` tells you whether the service is set to start on its own, which helps when you want to hide the noise.

**`pi5/docker`** — every 30 seconds: every container, running or stopped. If Docker isn't installed, it's just an empty list.

```json
{
  "name": "pihole",
  "image": "pihole/pihole",
  "state": "running",
  "status": "Up 3 days",
  "favorite": false
}
```

**`pi5/status`** — `online` or `offline`. Because everything above is retained, a dashboard would otherwise keep showing the last numbers it got even if the Pi had been unplugged an hour ago. This topic is how it can tell. The daemon sets it to `online` when it connects, and if it crashes or the Pi drops off the network, the broker flips it to `offline` on its own. Stopping the service cleanly does the same.

Everything is published as retained, so a dashboard that connects gets the latest numbers straight away instead of staring at blanks until the next update.

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

Every value is checked before it goes anywhere. A colour that isn't a real colour, or a brightness of 500, gets ignored and noted in the log rather than sent to the case. The valid ones are passed on to the Pironman5 software running on the Pi.

### Favourites

Out of a hundred-odd services you probably care about five. Mark those as favourites and a dashboard can show them up front and tuck the rest away. To star one, publish to `pi5/control/services`:

```json
{"action": "favorite", "source": "systemd", "name": "mosquitto.service", "value": true}
```

Use `"source": "docker"` for containers, and `"value": false` to unstar. Favourites are saved on the Pi in `favorites.json`, so they survive restarts and updates, and every browser sees the same ones. The change shows up within a moment — no waiting for the next 30-second update.

## Requirements

A Raspberry Pi running a systemd-based distro, Python 3.9+, and an MQTT broker it can reach. The three Python dependencies are in `requirements.txt`.

Beyond that, the collectors shell out to ordinary Linux tooling — SMART, systemd, the firewall, the VPN. Whatever isn't installed simply reports zero, `false` or an empty list instead of crashing, so you can run it on a bare Pi and fill in the gaps later. The Pironman5 controls need the case software running; without it the RGB and fan fields stay at their defaults.

If the Docker list comes back empty even though you have containers, the daemon probably isn't allowed to talk to Docker. Add your user to the `docker` group and restart the service:

```bash
sudo usermod -aG docker $USER
sudo systemctl restart pi5_mqtt
```

The service list needs a reasonably recent systemd — anything from Raspberry Pi OS Bookworm onwards is fine.

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

To see what it's up to — connections, rejected commands, anything that went wrong:

```bash
journalctl -u pi5_mqtt -f
```

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
| `TOPIC_STATUS` | `pi5/status` | online/offline topic |
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
| `NET_INTERFACE` | — | interface to measure traffic on; empty follows your internet connection |

`.env` is gitignored, so your credentials stay on the machine.

## Serving the dashboard

You don't need nginx or a separate web server to run [Pi5 Dashboard](https://github.com/Alex93IDE/Pi5_Dashboard) — the daemon can hand it out itself. Pick a port in `.env`:

```
HTTP_PORT=3010
```

Then, in the dashboard project, point the deploy at this repo's `public/` folder and run `npm run deploy`:

```
DEPLOY_TARGET=user@pi:~/Pi5_mqtt/public/
```

That's it — open `http://<your-pi>:3010`. Later deploys show up on the next page reload, no restart needed.

This is meant for your home network or your VPN, not the internet: there's no password on the page itself. Open the port only to the networks you trust. The dashboard also talks to the broker directly from your browser, so its WebSocket port (9001 here) needs the same treatment:

```bash
sudo ufw allow from 192.168.1.0/24 to any port 3010 proto tcp comment 'pi5_dash'
sudo ufw allow in on wg0 to any port 3010 proto tcp comment 'pi5_dash'
sudo ufw allow from 192.168.1.0/24 to any port 9001 proto tcp comment 'mqtt ws'
sudo ufw allow in on wg0 to any port 9001 proto tcp comment 'mqtt ws'
```

## Security notes

Worth reading before you point this at anything:

- **The payload describes your machine.** It includes the local IP, the firewall ruleset and every service and container you run. That's the whole point on a private dashboard, but it's a gift to anyone else. Only publish to a broker you control, with authentication on, and use TLS if it's reachable beyond your LAN or VPN.
- **The control topics have no authorisation of their own.** Anyone who can publish to them can drive the case hardware or change favourites. Broker-level ACLs are what keeps that honest.
- **Nothing here should face the internet directly.** There's no auth layer in this code, by design — it assumes it's sitting behind a broker that has one.

## Running the tests

The tests need nothing beyond the normal dependencies, and none of them touch your real system — no MQTT broker, no systemd, no hardware:

```bash
.venv/bin/python -m unittest
```

They cover the parts that are easy to break without noticing: reading the firewall and VPN output, rejecting bad control commands, saving favourites, and making sure the dashboard server never hands out files from outside `public/`.

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
tests/           unit tests
```

## License

MIT — see [LICENSE](LICENSE). Do what you like with it.
