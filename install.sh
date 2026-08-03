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
sudo tee /etc/sudoers.d/pi5_mqtt > /dev/null <<EOF
# Lets the pi5_mqtt service run these commands without a password
$USER ALL=(root) NOPASSWD: /usr/bin/wg show wg0 latest-handshakes
$USER ALL=(root) NOPASSWD: /usr/sbin/smartctl -A /dev/nvme0
$USER ALL=(root) NOPASSWD: /usr/bin/fail2ban-client status sshd
$USER ALL=(root) NOPASSWD: /usr/bin/cscli decisions list
EOF
sudo chmod 440 /etc/sudoers.d/pi5_mqtt

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
