#!/bin/bash
set -e

if [[ "$EUID" -ne 0 ]]; then
    echo "This script must be run as root. Please use sudo." >&2
    exit 1
fi

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

apt update
apt install -y python3 python3-pip python3-venv

SERVICE_USER=rpi

if [ ! -d "venv" ]; then
  sudo -u "$SERVICE_USER" python3 -m venv venv
fi

sudo -u "$SERVICE_USER" bash -c "
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
"

echo "Python packages installed successfully"
echo "Setting up systemd service"

SERVICE_NAME=datacollector.service
SERVICE_PATH=/etc/systemd/system/$SERVICE_NAME

if [ -f "$SERVICE_PATH" ]; then
  echo "Service file already exists, skipping install"
else
    cp "$SERVICE_NAME" $SERVICE_PATH
fi

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

echo "Service started successfully"
echo "Setup complete"