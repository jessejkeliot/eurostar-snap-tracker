#!/bin/bash

# This script opens three new Terminal windows on macOS 
# and runs each of the required services concurrently.

# Uses the python3 executable currently active (e.g. your active venv)
PYTHON_PATH=$(which python3)
PROJECT_DIR=$(pwd)

echo "Starting Eurostar Snap Tracker services in new Terminal windows..."

# Start handler.py using gunicorn (2 workers for lightweight concurrency)
osascript -e "tell application \"Terminal\"
    do script \"cd '$PROJECT_DIR' && '$PYTHON_PATH' -m gunicorn -w 2 -b 0.0.0.0:8080 handler:app\"
    activate
end tell"

# Start pycron.py
osascript -e "tell application \"Terminal\"
    do script \"cd '$PROJECT_DIR' && '$PYTHON_PATH' pycron.py\"
    activate
end tell"

# Start email_poller.py
osascript -e "tell application \"Terminal\"
    do script \"cd '$PROJECT_DIR' && '$PYTHON_PATH' email_poller.py\"
    activate
end tell"

echo "All three services have been launched!"
