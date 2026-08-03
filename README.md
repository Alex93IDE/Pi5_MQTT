# Pi5 MQTT Publisher

A small daemon that keeps an eye on my Raspberry Pi 5 (in a Pironman5 case) and lets me poke at it over MQTT.

It pushes system metrics to two topics — the cheap stuff every second, the slow stuff every 30 — and listens on a third one for commands, so I can turn the RGB off from my phone instead of SSHing in every time.

I wrote it for my own setup, but it's simple enough that adapting it should be painless. Everything worth changing lives in `.env`.

## What it publishes

**`pi5/fast`** — once a second: CPU load, frequency and temperature, RAM, disk, fan RPM, uptime, LAN IP, how many WireGuard peers are actually connected, and the current Pironman5 state (RGB colour/style/brightness, OLED, fan mode).

**`pi5/slow`** — every 30 seconds, because these are slow or expensive to read: NVMe health from SMART (temperature, spare, wear, power-on hours, unsafe shutdowns, media errors), fail2ban and CrowdSec ban counts, whether a handful of services are alive, and the full UFW ruleset parsed into JSON.

Both payloads go out with `retain=True`, so anything that subscribes gets the last known state right away instead of waiting for the next tick.

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

Under the hood these are just `curl` calls to the Pironman5 API on `localhost:34001`.

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

That creates a virtualenv, installs the Python dependencies, drops a narrow sudoers rule so the service can read `wg`, `smartctl`, `fail2ban-client` and `cscli` without a password, and sets up a systemd unit called `pi5_mqtt` that starts on boot.

Worth knowing: that sudoers file whitelists those four exact commands and nothing else. If you'd rather not have it at all, delete those lines from `install.sh` — the affected fields will just come back as zeros instead of breaking anything.

To update later:

```bash
git pull
bash update.sh
```

And if you want it gone, `bash uninstall.sh` removes the service and the sudoers rule but leaves the repo and the virtualenv alone.

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

`.env` is gitignored, so your password stays on the Pi.

## A note on exposure

The `pi5/slow` payload includes your full firewall ruleset, and `pi5/fast` includes the Pi's LAN IP. That's genuinely useful on a dashboard and completely fine on a broker you control, but don't point this at a broker that's reachable from the open internet without TLS and authentication in front of it.

## What it expects to find

The collectors shell out to a fair number of tools. Anything missing just yields a zero or `false` rather than crashing, so you can ignore whatever you don't run:

- `mosquitto` — the MQTT broker
- `smartmontools` — NVMe health
- `fail2ban`, `crowdsec` + `crowdsec-firewall-bouncer` — ban counts
- `wireguard` — peer handshakes
- `ufw` — firewall rules
- `docker` — for the AdGuard Home container check
- `cloudflared`, `wgdashboard`, `softkey`, `bitflex` — service status checks, all optional
- the Pironman5 API on `localhost:34001`

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
