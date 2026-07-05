#!/bin/bash
set -euo pipefail

APP_DIR="/opt/BotFatir"
APP_USER="${SUDO_USER:-$USER}"

echo "==> BotFatir install to $APP_DIR"

sudo apt-get update -qq
sudo apt-get install -y python3 python3-venv python3-pip git

sudo mkdir -p "$APP_DIR"
sudo chown "$APP_USER:$APP_USER" "$APP_DIR"

if [ ! -f "$APP_DIR/requirements.txt" ]; then
  echo "ERROR: Copy project files to $APP_DIR first."
  echo "Example from your PC:"
  echo "  scp -r c:/BotFatir/* user@YOUR_VPS_IP:/opt/BotFatir/"
  exit 1
fi

cd "$APP_DIR"

python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .

if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "Created .env — edit it now:"
  echo "  nano $APP_DIR/.env"
  echo "Fill TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID"
  exit 0
fi

sudo cp deploy/botfatir.service /etc/systemd/system/botfatir.service
sudo sed -i "s|User=botfatir|User=$APP_USER|" /etc/systemd/system/botfatir.service
sudo systemctl daemon-reload
sudo systemctl enable botfatir
sudo systemctl restart botfatir

echo ""
echo "Done. Check status:"
echo "  sudo systemctl status botfatir"
echo "  sudo journalctl -u botfatir -f"
