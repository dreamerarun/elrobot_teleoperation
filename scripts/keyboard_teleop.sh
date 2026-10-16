#!/bin/bash
# ElRobot direct keyboard control (terminal-based, no browser needed)

PORT=${1:-/dev/ttyACM0}
SPEED=${2:-5.0}

echo "=== ElRobot Keyboard Control ==="
echo "Port: $PORT | Speed: $SPEED"
echo ""

python "$(dirname "$0")/keyboard_control.py" --port $PORT --speed $SPEED
