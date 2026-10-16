#!/bin/bash
# Record dataset with ElRobot

REPO_ID=${1:-"elrobot-dataset"}
FOLLOWER_PORT=${2:-/dev/ttyACM0}
LEADER_PORT=${3:-/dev/ttyACM1}

echo "=== ElRobot Dataset Recording ==="
echo "Repo: $REPO_ID | Follower: $FOLLOWER_PORT | Leader: $LEADER_PORT"

lerobot-record \
    --robot.type=elrobot_follower --robot.port=$FOLLOWER_PORT \
    --teleop.type=elrobot_leader --teleop.port=$LEADER_PORT \
    --repo-id=$REPO_ID \
    --num-episodes=50 \
    --fps=30
