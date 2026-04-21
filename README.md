# Pi5 MQTT Publisher

Servicio para monitorizar y controlar una Raspberry Pi 5 con caja Pironman5 a través de MQTT.

Publica métricas del sistema cada segundo (`pi5/fast`) y cada 30 segundos (`pi5/slow`), y escucha comandos de control en `pi5/control/pironman`.

## Estructura

```
Pi5_mqtt/
├── main.py          # Entry point
├── config.py        # Configuración (lee .env)
├── helpers.py       # Funciones utilitarias de sistema
├── control.py       # Manejador de comandos MQTT entrantes
├── client.py        # Cliente MQTT (conexión y callbacks)
├── collectors.py    # Recolección de datos (fast y slow)
├── requirements.txt
├── .env             # Credenciales (NO se sube al repo)
├── .env.example     # Plantilla de configuración
├── install.sh       # Instalación inicial en la Pi
└── update.sh        # Actualización tras git pull
```

## Instalación en la Pi

### 1. Clonar el repositorio

```bash
git clone <url-del-repo> ~/Pi5_mqtt
cd ~/Pi5_mqtt
```

### 2. Configurar credenciales

```bash
cp .env.example .env
nano .env   # Editar MQTT_PASS y cualquier otro valor necesario
```

### 3. Instalar

```bash
bash install.sh
```

Esto instala las dependencias Python, crea el servicio systemd `pi5_mqtt` y lo habilita para arrancar automáticamente con el sistema.

## Actualización

```bash
git pull
bash update.sh
```

Actualiza dependencias si cambiaron y reinicia el servicio.

## Topics MQTT

| Topic | Intervalo | Descripción |
|---|---|---|
| `pi5/fast` | 1 s | CPU, RAM, disco, temperatura, WireGuard, Pironman5 |
| `pi5/slow` | 30 s | NVMe, bans (fail2ban/CrowdSec), estado de servicios |
| `pi5/control/pironman` | — | Comandos de control entrantes |

## Comandos de control

Publicar un JSON en `pi5/control/pironman` con el campo `action`:

| action | Parámetros extra | Descripción |
|---|---|---|
| `oled_on` / `oled_off` | — | Activar/desactivar OLED |
| `rgb_on` / `rgb_off` | — | Activar/desactivar RGB |
| `rgb_color` | `color` (hex, ej. `#ff0000`) | Cambiar color RGB |
| `rgb_style` | `style` (ej. `breathing`) | Cambiar estilo RGB |
| `rgb_brightness` | `value` (0-100) | Cambiar brillo RGB |
| `rgb_speed` | `value` (0-100) | Cambiar velocidad RGB |
| `fan_mode` | `mode` (0-4) | Modo ventilador: 0=Always On, 1=Performance, 2=Cool, 3=Balance, 4=Silent |

Ejemplo:
```json
{"action": "rgb_color", "color": "#00ff00"}
```

## Dependencias del sistema

El script asume que están instalados en la Pi:

- `mosquitto` — broker MQTT
- `smartmontools` — métricas NVMe (`smartctl`)
- `fail2ban` — bans SSH
- `crowdsec` + `crowdsec-firewall-bouncer`
- `wireguard` — VPN
- `docker` — para AdGuard Home
- `cloudflared`, `wgdashboard`, `softkey` — servicios opcionales
- API de Pironman5 corriendo en `localhost:34001`

## Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `MQTT_HOST` | `localhost` | Host del broker MQTT |
| `MQTT_PORT` | `1883` | Puerto del broker |
| `MQTT_USER` | `pi5` | Usuario MQTT |
| `MQTT_PASS` | — | Contraseña MQTT |
| `PIRONMAN_API` | `http://localhost:34001/api/v1.0` | URL API Pironman5 |
| `TOPIC_FAST` | `pi5/fast` | Topic datos rápidos |
| `TOPIC_SLOW` | `pi5/slow` | Topic datos lentos |
| `TOPIC_CTRL` | `pi5/control/pironman` | Topic de control |
| `INTERVAL_FAST` | `1` | Intervalo fast en segundos |
| `INTERVAL_SLOW` | `30` | Intervalo slow en segundos |
