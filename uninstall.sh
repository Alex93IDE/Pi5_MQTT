#!/bin/bash
# Removes the service and its system config. The repo itself is left alone.
set -e

SERVICE_NAME="pi5_mqtt"

echo "==> Stopping and disabling service..."
sudo systemctl stop ${SERVICE_NAME} 2>/dev/null || true
sudo systemctl disable ${SERVICE_NAME} 2>/dev/null || true

echo "==> Removing service file..."
sudo rm -f /etc/systemd/system/${SERVICE_NAME}.service
sudo systemctl daemon-reload

echo "==> Removing sudoers rules..."
sudo rm -f /etc/sudoers.d/${SERVICE_NAME}

echo ""
echo "==> Done. The repo and the .venv were left untouched."
echo "    To reinstall: bash install.sh"
