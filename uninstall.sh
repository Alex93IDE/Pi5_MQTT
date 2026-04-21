#!/bin/bash
# Elimina el servicio y configuración del sistema. El código del repo no se toca.
set -e

SERVICE_NAME="pi5_mqtt"

echo "==> Deteniendo y deshabilitando servicio..."
sudo systemctl stop ${SERVICE_NAME} 2>/dev/null || true
sudo systemctl disable ${SERVICE_NAME} 2>/dev/null || true

echo "==> Eliminando archivo de servicio..."
sudo rm -f /etc/systemd/system/${SERVICE_NAME}.service
sudo systemctl daemon-reload

echo "==> Eliminando reglas sudoers..."
sudo rm -f /etc/sudoers.d/${SERVICE_NAME}

echo ""
echo "==> Listo. El repo y el .venv no se han tocado."
echo "    Para reinstalar: bash install.sh"
