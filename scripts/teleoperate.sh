#!/bin/bash
# Teleoperate ElRobot: leader controls follower

FOLLOWER_PORT=${1:-/dev/ttyACM0}
LEADER_PORT=${2:-/dev/ttyACM1}

echo "=== ElRobot Teleoperation ==="
echo "Follower: $FOLLOWER_PORT | Leader: $LEADER_PORT"

lerobot-teleoperate \
    --robot.type=elrobot_follower --robot.port=$FOLLOWER_PORT \
    --teleop.type=elrobot_leader --teleop.port=$LEADER_PORT
