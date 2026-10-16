#!/bin/bash
# ElRobot Telegrip - Web-based keyboard control

PORT=${1:-/dev/ttyACM0}
NO_ROBOT=""

if [ "$1" = "--no-robot" ] || [ "$2" = "--no-robot" ]; then
    NO_ROBOT="--no-robot"
fi

echo "=== ElRobot Telegrip (Web UI) ==="
echo "Port: $PORT"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
python "$SCRIPT_DIR/telegrip/elrobot_telegrip.py" --port $PORT $NO_ROBOT
