#!/bin/bash
# Calibrate ElRobot arms

DEVICE=${1:-follower}
PORT=${2:-/dev/ttyACM0}

if [ "$DEVICE" = "follower" ]; then
    echo "=== Calibrating ElRobot Follower ==="
    lerobot-calibrate --robot.type=elrobot_follower --robot.port=$PORT
elif [ "$DEVICE" = "leader" ]; then
    echo "=== Calibrating ElRobot Leader ==="
    lerobot-calibrate --teleop.type=elrobot_leader --teleop.port=$PORT
else
    echo "Usage: $0 [follower|leader] [port]"
    exit 1
fi
