#!/bin/bash
# Ejecutar después de git pull para aplicar cambios.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="pi5_mqtt"

echo "==> Actualizando dependencias Python..."
pip3 install -r "$SCRIPT_DIR/requirements.txt"

echo "==> Reiniciando servicio..."
sudo systemctl restart ${SERVICE_NAME}

echo ""
echo "==> Actualización completa! Estado del servicio:"
sudo systemctl status ${SERVICE_NAME} --no-pager
