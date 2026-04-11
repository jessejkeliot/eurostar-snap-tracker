#!/bin/bash

# =======================================================
# Eurostar Snap Tracker - Systemd Linux Deployment Script
# =======================================================
# This script configures GCP e2-micro (or any Ubuntu/Debian server)
# to keep all three Eurostar python services running permanently in the background.

if [ "$EUID" -ne 0 ]; then
  echo "🚨 Please run this script as root: 'sudo ./install_services_linux.sh'"
  exit 1
fi

PROJECT_DIR=$(pwd)
APP_USER=$SUDO_USER
if [ -z "$APP_USER" ]; then
    APP_USER=$(whoami)
fi

USER_HOME=$(eval echo ~$APP_USER)

# Fallback: check if the user is using a venv like suggested in the readme
if [ -d "$USER_HOME/venv" ]; then
    PYTHON_PATH="$USER_HOME/venv/bin/python3"
    GUNICORN_PATH="$USER_HOME/venv/bin/gunicorn"
else
    PYTHON_PATH=$(which python3)
    GUNICORN_PATH=$(which gunicorn)
fi

echo "⚙️  User: $APP_USER"
echo "⚙️  Project Dir: $PROJECT_DIR"
echo "⚙️  Python Path: $PYTHON_PATH"

echo "Creating Systemd service files..."

# 1. API Service (Gunicorn HTTP handler)
cat > /etc/systemd/system/whatsnap-api.service <<EOF
[Unit]
Description=WhatSnap Bot Gunicorn API
After=network.target

[Service]
User=$APP_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$GUNICORN_PATH -w 2 -b 0.0.0.0:8080 handler:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 2. Scraper Cron Service
cat > /etc/systemd/system/whatsnap-cron.service <<EOF
[Unit]
Description=WhatSnap Bot Scheduler (Cron)
After=network.target

[Service]
User=$APP_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PYTHON_PATH pycron.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 3. Email Poller Service
cat > /etc/systemd/system/whatsnap-poller.service <<EOF
[Unit]
Description=WhatSnap Bot Email Poller
After=network.target

[Service]
User=$APP_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PYTHON_PATH email_poller.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "Reloading systemd daemon..."
systemctl daemon-reload

echo "Enabling services to start on boot..."
systemctl enable whatsnap-api.service
systemctl enable whatsnap-cron.service
systemctl enable whatsnap-poller.service

echo "Starting services now..."
systemctl restart whatsnap-api.service
systemctl restart whatsnap-cron.service
systemctl restart whatsnap-poller.service

echo "======================================"
echo "✅ All services installed and started!"
echo "To check the logs, run:"
echo "sudo journalctl -u whatsnap-api -f"
echo "sudo journalctl -u whatsnap-cron -f"
echo "sudo journalctl -u whatsnap-poller -f"
echo "======================================"
