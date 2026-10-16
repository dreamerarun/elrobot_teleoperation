#!/usr/bin/env python
"""
ElRobot Keyboard Control - Direct joint-space teleoperation.

Controls the ElRobot 7+1 DOF arm using keyboard input.
Each joint can be moved independently with dedicated key pairs.

Usage:
    python scripts/keyboard_control.py --port /dev/ttyACM0

Key Bindings:
    Joint Control:
        Q / A  - shoulder_yaw    (joint 1) +/-
        W / S  - shoulder_pitch  (joint 2) +/-
        E / D  - elbow_yaw       (joint 3) +/-
        R / F  - elbow_pitch     (joint 4) +/-
        T / G  - wrist_pitch     (joint 5) +/-
        Y / H  - wrist_roll      (joint 6) +/-
        U / J  - wrist_yaw       (joint 7) +/-
        O / L  - gripper         (joint 8) open/close

    Speed Control:
        1-5    - Set speed (1=slow, 5=fast)

    Other:
        Z      - Go to home position
        X      - Go to zero position
        P      - Print current joint positions
        ESC    - Quit
"""

import argparse
import logging
import sys
import time
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

try:
    from lerobot.robots.elrobot_follower.config_elrobot_follower import ElRobotFollowerConfig
    from lerobot.robots.elrobot_follower.elrobot_follower import ElRobotFollower
except ImportError:
    logger.error("ElRobot driver not found. Make sure lerobot is installed with ElRobot support.")
    sys.exit(1)

# Joint names and key mappings
JOINT_NAMES = [
    "shoulder_yaw", "shoulder_pitch", "elbow_yaw", "elbow_pitch",
    "wrist_pitch", "wrist_roll", "wrist_yaw", "gripper"
]

# Key pairs: (increase_key, decrease_key) for each joint
KEY_MAP = {
    'q': ("shoulder_yaw", +1),
    'a': ("shoulder_yaw", -1),
    'w': ("shoulder_pitch", +1),
    's': ("shoulder_pitch", -1),
    'e': ("elbow_yaw", +1),
    'd': ("elbow_yaw", -1),
    'r': ("elbow_pitch", +1),
    'f': ("elbow_pitch", -1),
    't': ("wrist_pitch", +1),
    'g': ("wrist_pitch", -1),
    'y': ("wrist_roll", +1),
    'h': ("wrist_roll", -1),
    'u': ("wrist_yaw", +1),
    'j': ("wrist_yaw", -1),
    'o': ("gripper", +1),
    'l': ("gripper", -1),
}

# Home position (safe resting pose)
HOME_POSITION = {
    "shoulder_yaw.pos": 0.0,
    "shoulder_pitch.pos": 0.0,
    "elbow_yaw.pos": 0.0,
    "elbow_pitch.pos": 0.0,
    "wrist_pitch.pos": 0.0,
    "wrist_roll.pos": 0.0,
    "wrist_yaw.pos": 0.0,
    "gripper.pos": 0.0,
}

SPEED_LEVELS = {
    '1': 1.0,
    '2': 2.0,
    '3': 5.0,
    '4': 10.0,
    '5': 20.0,
}


def get_key():
    """Read a single keypress without waiting for enter."""
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            return 'ESC'
        return ch.lower()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def print_status(positions: dict, speed: float):
    """Print current joint positions."""
    print("\n" + "=" * 50)
    print(f"  ElRobot Joint Positions  (speed: {speed})")
    print("=" * 50)
    for name in JOINT_NAMES:
        key = f"{name}.pos"
        val = positions.get(key, 0.0)
        print(f"  {name:20s}: {val:8.2f}")
    print("=" * 50)


def print_controls():
    """Print control help."""
    print("\n" + "=" * 60)
    print("  ElRobot Keyboard Control")
    print("=" * 60)
    print("  Joint           | +Key | -Key")
    print("  -----------------+------+------")
    print("  shoulder_yaw     |  Q   |  A")
    print("  shoulder_pitch   |  W   |  S")
    print("  elbow_yaw        |  E   |  D")
    print("  elbow_pitch      |  R   |  F")
    print("  wrist_pitch      |  T   |  G")
    print("  wrist_roll       |  Y   |  H")
    print("  wrist_yaw        |  U   |  J")
    print("  gripper          |  O   |  L")
    print("  -----------------+------+------")
    print("  1-5: Speed level | Z: Home | X: Zero")
    print("  P: Print pos     | ESC: Quit")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="ElRobot Keyboard Control")
    parser.add_argument("--port", default="/dev/ttyACM0", help="Serial port")
    parser.add_argument("--speed", type=float, default=5.0, help="Initial step size")
    parser.add_argument("--fps", type=float, default=30.0, help="Control loop frequency")
    args = parser.parse_args()

    config = ElRobotFollowerConfig(
        port=args.port,
        use_degrees=True,
        disable_torque_on_disconnect=True,
    )

    robot = ElRobotFollower(config)

    print_controls()
    print(f"\nConnecting to ElRobot on {args.port}...")

    try:
        robot.connect()
        print("Connected! Robot is ready.")
    except Exception as e:
        logger.error(f"Failed to connect: {e}")
        sys.exit(1)

    speed = args.speed
    dt = 1.0 / args.fps

    try:
        # Read initial positions
        obs = robot.get_observation()
        current_pos = {k: v for k, v in obs.items() if k.endswith(".pos")}

        print_status(current_pos, speed)
        print("\nPress keys to move joints (see controls above)")

        while True:
            key = get_key()

            if key == 'ESC':
                print("\nShutting down...")
                break

            elif key == 'p':
                obs = robot.get_observation()
                current_pos = {k: v for k, v in obs.items() if k.endswith(".pos")}
                print_status(current_pos, speed)

            elif key == 'z':
                print("  -> Going to home position...")
                robot.send_action(HOME_POSITION)
                time.sleep(1.0)
                obs = robot.get_observation()
                current_pos = {k: v for k, v in obs.items() if k.endswith(".pos")}
                print_status(current_pos, speed)

            elif key == 'x':
                print("  -> Going to zero position...")
                zero = {f"{j}.pos": 0.0 for j in JOINT_NAMES}
                robot.send_action(zero)
                time.sleep(1.0)
                obs = robot.get_observation()
                current_pos = {k: v for k, v in obs.items() if k.endswith(".pos")}
                print_status(current_pos, speed)

            elif key in SPEED_LEVELS:
                speed = SPEED_LEVELS[key]
                print(f"  Speed set to {speed}")

            elif key in KEY_MAP:
                joint_name, direction = KEY_MAP[key]
                joint_key = f"{joint_name}.pos"

                # Read current position
                obs = robot.get_observation()
                current_pos = {k: v for k, v in obs.items() if k.endswith(".pos")}

                # Apply delta
                new_val = current_pos.get(joint_key, 0.0) + (direction * speed)
                action = dict(current_pos)
                action[joint_key] = new_val

                robot.send_action(action)
                print(f"  {joint_name}: {new_val:.2f}")

            time.sleep(dt)

    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        print("Disconnecting...")
        try:
            robot.disconnect()
        except Exception:
            pass
        print("Done.")


if __name__ == "__main__":
    main()
