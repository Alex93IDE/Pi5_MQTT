#!/bin/bash
# Run this after a git pull to apply changes.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="pi5_mqtt"
VENV="$SCRIPT_DIR/.venv"

echo "==> Updating Python dependencies..."
"$VENV/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"

echo "==> Restarting service..."
sudo systemctl restart ${SERVICE_NAME}

echo ""
echo "==> Done! Service status:"
sudo systemctl status ${SERVICE_NAME} --no-pager
