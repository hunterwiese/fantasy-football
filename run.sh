#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
pip install -r "$SCRIPT_DIR/requirements.txt"
python draggable_rankings_app.py &
APP_PID=$!
# Wait briefly for server to start
sleep 2
open http://127.0.0.1:5000/
wait $APP_PID
