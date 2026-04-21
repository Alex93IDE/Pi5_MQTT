#!/bin/bash
# Primera instalación en la Pi. Ejecutar una sola vez.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="pi5_mqtt"
VENV="$SCRIPT_DIR/.venv"

echo "==> Directorio: $SCRIPT_DIR"

echo ""
echo "==> Verificando .env..."
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo "    Creado .env desde .env.example — edítalo antes de continuar."
    exit 1
fi

echo ""
echo "==> Creando entorno virtual..."
python3 -m venv "$VENV"

echo ""
echo "==> Instalando dependencias Python..."
"$VENV/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"

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
echo "==> Instalación completa! Estado del servicio:"
sudo systemctl status ${SERVICE_NAME} --no-pager
