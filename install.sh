#!/bin/bash
# Primera instalación en la Pi. Ejecutar una sola vez.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="pi5_mqtt"
PYTHON=$(command -v python3)

echo "==> Directorio: $SCRIPT_DIR"
echo "==> Python: $PYTHON"

echo ""
echo "==> Verificando .env..."
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo "    Creado .env desde .env.example — edítalo antes de continuar."
    exit 1
fi

echo ""
echo "==> Instalando dependencias Python..."
pip3 install -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "==> Creando servicio systemd..."
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=Pi5 MQTT Publisher
After=network.target mosquitto.service
Wants=mosquitto.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=$PYTHON $SCRIPT_DIR/main.py
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
echo "==> Instalación completa! Estado del servicio:"
sudo systemctl status ${SERVICE_NAME} --no-pager
