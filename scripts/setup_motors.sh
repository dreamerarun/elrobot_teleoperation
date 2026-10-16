#!/bin/bash
# Setup motor IDs for ElRobot (connect one servo at a time)
# Follower arm (12V power): IDs 1-8
# Leader arm (7.4V power): IDs 1-8

DEVICE=${1:-follower}
PORT=${2:-/dev/ttyACM0}

if [ "$DEVICE" = "follower" ]; then
    echo "=== ElRobot Follower Motor Setup ==="
    echo "Connect 12V/4A power supply to the driver board"
    lerobot-setup-motors --robot.type=elrobot_follower --robot.port=$PORT
elif [ "$DEVICE" = "leader" ]; then
    echo "=== ElRobot Leader Motor Setup ==="
    echo "Connect 7.4V power supply to the driver board"
    lerobot-setup-motors --teleop.type=elrobot_leader --teleop.port=$PORT
else
    echo "Usage: $0 [follower|leader] [port]"
    exit 1
fi
