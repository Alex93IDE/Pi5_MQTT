#!/bin/bash
# Ejecutar después de git pull para aplicar cambios.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="pi5_mqtt"
VENV="$SCRIPT_DIR/.venv"

echo "==> Actualizando dependencias Python..."
"$VENV/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"

echo "==> Reiniciando servicio..."
sudo systemctl restart ${SERVICE_NAME}

echo ""
echo "==> Actualización completa! Estado del servicio:"
sudo systemctl status ${SERVICE_NAME} --no-pager
