#!/bin/bash
# First-time setup on the Pi. Run this once.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="pi5_mqtt"
VENV="$SCRIPT_DIR/.venv"

echo "==> Directory: $SCRIPT_DIR"

echo ""
echo "==> Checking .env..."
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo "    Created .env from .env.example — edit it before continuing."
    exit 1
fi

echo ""
echo "==> Creating virtualenv..."
python3 -m venv "$VENV"

echo ""
echo "==> Installing Python dependencies..."
"$VENV/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "==> Setting up sudoers (NOPASSWD for system commands)..."

# Read a single key out of .env without sourcing it (the file holds a password).
env_get() {
    local val
    val="$(grep -E "^$1=" "$SCRIPT_DIR/.env" | tail -n1 | cut -d= -f2-)"
    echo "${val:-$2}"
}

WG_INTERFACE="$(env_get WG_INTERFACE wg0)"
NVME_DEVICE="$(env_get NVME_DEVICE /dev/nvme0)"
F2B_JAIL="$(env_get F2B_JAIL sshd)"
CS_ENABLE="$(env_get CS_ENABLE false)"

# Only grant what this host actually collects — each metric left empty in
# .env gets no rule at all.
{
    echo "# Lets the pi5_mqtt service run these commands without a password"
    [ -n "$WG_INTERFACE" ] && echo "$USER ALL=(root) NOPASSWD: /usr/bin/wg show $WG_INTERFACE latest-handshakes"
    [ -n "$NVME_DEVICE" ]  && echo "$USER ALL=(root) NOPASSWD: /usr/sbin/smartctl -A $NVME_DEVICE"
    [ -n "$F2B_JAIL" ]     && echo "$USER ALL=(root) NOPASSWD: /usr/bin/fail2ban-client status $F2B_JAIL"
    [ "$CS_ENABLE" = "true" ] && echo "$USER ALL=(root) NOPASSWD: /usr/bin/cscli decisions list"
    true
} | sudo tee /etc/sudoers.d/pi5_mqtt > /dev/null
sudo chmod 440 /etc/sudoers.d/pi5_mqtt

echo "    Granted:"
sudo grep -c NOPASSWD /etc/sudoers.d/pi5_mqtt | xargs -I{} echo "    {} command(s) — see /etc/sudoers.d/pi5_mqtt"

echo ""
echo "==> Creating systemd service..."
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=Pi5 MQTT Publisher
After=network.target mosquitto.service
Wants=mosquitto.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=$VENV/bin/python $SCRIPT_DIR/main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl start ${SERVICE_NAME}

echo ""
echo "==> Done! Service status:"
sudo systemctl status ${SERVICE_NAME} --no-pager
