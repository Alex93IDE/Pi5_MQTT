# Pi5 MQTT Publisher

A small daemon that monitors a Raspberry Pi 5 in a Pironman5 case and publishes its state over MQTT. It can also control the case (RGB, fan, OLED) from a dashboard or a phone.

It pairs with [Pi5 Dashboard](https://github.com/Alex93IDE/Pi5_Dashboard), which it can optionally serve itself.

## Features

- System metrics every second: CPU, RAM, disk, network, temperature, fan, uptime
- NVMe health, Fail2ban/CrowdSec bans and firewall rules every 30 seconds
- Lists of systemd services and Docker containers, with favourites
- Pironman5 control: RGB colour, style, brightness and speed, fan mode, OLED
- Online/offline status through MQTT last will
- Optional built-in web server for the dashboard

## Requirements

- Raspberry Pi with a systemd-based distro (Raspberry Pi OS Bookworm or later)
- Python 3.9+
- An MQTT broker

Optional: Pironman5 software, Docker, WireGuard, Fail2ban, CrowdSec, smartmontools. Anything missing just reports empty or zero values.

## Installation

```bash
git clone https://github.com/Alex93IDE/Pi5_MQTT.git ~/Pi5_mqtt
cd ~/Pi5_mqtt
cp .env.example .env   # fill in at least MQTT_PASS
bash install.sh
```

`install.sh` creates a virtualenv, a systemd service (`pi5_mqtt`) and a sudoers rule for a few read-only commands, listed at the top of the script.

Update with `git pull && bash update.sh`. Remove with `bash uninstall.sh`.

## Usage

The daemon publishes to these topics:

| topic | every | content |
|---|---|---|
| `pi5/fast` | 1 s | system metrics and Pironman5 state |
| `pi5/slow` | 30 s | NVMe health, bans, firewall rules |
| `pi5/services` | 30 s | systemd services |
| `pi5/docker` | 30 s | Docker containers |
| `pi5/status` | — | `online` / `offline` |

And listens for commands:

```jsonc
// pi5/control/pironman
{"action": "rgb_color", "color": "#00ff00"}

// pi5/control/services
{"action": "favorite", "source": "systemd", "name": "mosquitto.service", "value": true}
```

Case actions: `oled_on`, `oled_off`, `rgb_on`, `rgb_off`, `rgb_color`, `rgb_style`, `rgb_brightness`, `rgb_speed`, `fan_mode`. Invalid values are logged and ignored.

Logs: `journalctl -u pi5_mqtt -f`

## Configuration

All settings live in `.env`. See `.env.example` for the full list: broker, topics, intervals, dashboard port and host-specific metrics.

## Tests

```bash
.venv/bin/python -m unittest
```

## Security

The payload describes your machine, and the control topics have no authentication of their own. Use a broker you control, with authentication and ACLs, and keep it on your LAN or VPN.

## Project status

A personal project, actively used on my own Pi. Versions follow [SemVer](https://semver.org); the daemon logs its version on startup.

## License

MIT — see [LICENSE](LICENSE).
