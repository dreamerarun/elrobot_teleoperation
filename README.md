# ElRobot - LeRobot Integration

Integration of the [norma-core ElRobot](https://github.com/norma-core/norma-core) 7+1 DOF robotic arm with [HuggingFace LeRobot](https://github.com/huggingface/lerobot) for teleoperation, data collection, and policy training.

## Robot Specifications

| Spec | Value |
|------|-------|
| DOF | 7 arm (revolute) + 1 gripper (parallel jaw) |
| Servos | 8x Feetech ST3215 |
| Protocol | Feetech Serial Bus (TTL) |
| Follower Power | 12V / 4A DC |
| Leader Power | 7.4V / 3A DC |
| Interface | USB Serial (driver board) |

## Joint Mapping

| Motor ID | Joint Name | Description |
|----------|------------|-------------|
| 1 | shoulder_yaw | Base rotation |
| 2 | shoulder_pitch | Shoulder up/down |
| 3 | elbow_yaw | Elbow rotation |
| 4 | elbow_pitch | Elbow bend |
| 5 | wrist_pitch | Wrist up/down |
| 6 | wrist_roll | Wrist rotation (continuous) |
| 7 | wrist_yaw | Wrist side-to-side |
| 8 | gripper | Parallel jaw open/close |

---

## Installation

### Step 1: Prerequisites

Make sure you have the following before starting:

- **Hardware:**
  - ElRobot 3D-printed parts assembled per [norma-core manual](https://github.com/norma-core/norma-core/tree/main/hardware/elrobot)
  - 8x Feetech ST3215 servos per arm
  - Feetech Serial Bus Driver Board per arm
  - 12V/4A power supply (follower arm)
  - 7.4V/3A power supply (leader arm)
  - USB cables

- **Software:**
  - Ubuntu 20.04+ (or another Linux distro)
  - Python 3.10+
  - `pip` package manager
  - `git`

### Step 2: Clone This Repository

```bash
cd ~
git clone https://github.com/norma-core/elrobot_project.git
cd elrobot_project
```

### Step 3: Install LeRobot with Feetech Support

LeRobot is the core framework that drives the ElRobot arm. Install it in editable mode with the Feetech servo extras:

```bash
cd ~
git clone https://github.com/huggingface/lerobot.git
cd lerobot
pip install -e ".[feetech]"
```

> **Note:** This installs the `lerobot` package along with CLI tools (`lerobot-calibrate`, `lerobot-teleoperate`, `lerobot-record`, `lerobot-train`, etc.) and the Feetech motor driver dependencies.

### Step 4: Install Additional Python Dependencies

```bash
pip install websockets   # Required for Telegrip Web UI
pip install pyserial     # Required for scan_bus.py
pip install numpy        # Required for keyboard control & telegrip
```

### Step 5: Copy ElRobot Drivers into LeRobot

The `elrobot_follower/` and `elrobot_leader/` directories contain the robot and teleoperator drivers. They need to be placed inside the LeRobot package so that LeRobot can discover them:

```bash
# Copy the follower (robot) driver
cp -r ~/elrobot_project/elrobot_follower ~/lerobot/lerobot/robots/elrobot_follower

# Copy the leader (teleoperator) driver
cp -r ~/elrobot_project/elrobot_leader ~/lerobot/lerobot/teleoperators/elrobot_leader
```

Verify the drivers are registered:

```bash
python -c "from lerobot.robots.elrobot_follower.config_elrobot_follower import ElRobotFollowerConfig; print('Follower driver OK')"
python -c "from lerobot.teleoperators.elrobot_leader.config_elrobot_leader import ElRobotLeaderConfig; print('Leader driver OK')"
```

### Step 6: Set Script Permissions

```bash
cd ~/elrobot_project
chmod +x scripts/*.sh
```

### Step 7: Verify USB Serial Ports

Connect the driver board(s) to the PC via USB and check that the serial ports are detected:

```bash
ls /dev/ttyACM*
# Expected: /dev/ttyACM0 (follower), /dev/ttyACM1 (leader)
```

> **Tip:** If no port appears, check the USB cable, driver board power, and run `dmesg | tail` to debug.

If you get permission errors accessing the port, add your user to the `dialout` group:

```bash
sudo usermod -aG dialout $USER
# Log out and log back in for the change to take effect
```

### Step 8: Scan the Bus (Optional Debug)

Check if servos are detected and at which baud rate:

```bash
python scripts/scan_bus.py --port /dev/ttyACM0
```

This scans all motor IDs (0-252) across common baud rates and reports what it finds.

---

## Setup

Once installation is complete, follow these steps to configure the robot.

### Setup Motor IDs

Connect **one servo at a time** to the driver board. Each servo is assigned a unique ID (1-8) matching the [Joint Mapping](#joint-mapping) table.

**Follower arm** (connect 12V/4A power supply):

```bash
./scripts/setup_motors.sh follower /dev/ttyACM0
```

**Leader arm** (connect 7.4V/3A power supply):

```bash
./scripts/setup_motors.sh leader /dev/ttyACM1
```

Or call the LeRobot CLI directly:

```bash
lerobot-setup-motors --robot.type=elrobot_follower --robot.port=/dev/ttyACM0
lerobot-setup-motors --teleop.type=elrobot_leader --teleop.port=/dev/ttyACM1
```

> **Important:** Repeat for each servo one at a time. After all 8 IDs are assigned, reconnect all servos in daisy-chain before proceeding.

### Calibrate Arms

Calibration records each joint's range of motion. Run once per arm after motor IDs are set.

**Follower arm:**

```bash
./scripts/calibrate.sh follower /dev/ttyACM0
```

**Leader arm:**

```bash
./scripts/calibrate.sh leader /dev/ttyACM1
```

Or directly:

```bash
lerobot-calibrate --robot.type=elrobot_follower --robot.port=/dev/ttyACM0
lerobot-calibrate --teleop.type=elrobot_leader --teleop.port=/dev/ttyACM1
```

**During calibration:**

1. Move the arm to the **middle** of its range of motion → press **ENTER**
2. Move all joints (except `wrist_roll`) through their **full range** → press **ENTER**
3. Calibration file is saved to `~/.cache/huggingface/lerobot/calibration/`

> **Config files:** `configs/calibrate_follower.yaml`, `configs/calibrate_leader.yaml`

---

## Usage

### Keyboard Control (Terminal)

Direct joint-space control from the terminal — no leader arm or browser needed:

```bash
./scripts/keyboard_teleop.sh /dev/ttyACM0
# With custom speed:
./scripts/keyboard_teleop.sh /dev/ttyACM0 10.0
```

Or directly:

```bash
python scripts/keyboard_control.py --port /dev/ttyACM0 --speed 5.0 --fps 30
```

**Key Bindings:**

| Joint | + Key | - Key |
|-------|-------|-------|
| shoulder_yaw | Q | A |
| shoulder_pitch | W | S |
| elbow_yaw | E | D |
| elbow_pitch | R | F |
| wrist_pitch | T | G |
| wrist_roll | Y | H |
| wrist_yaw | U | J |
| gripper | O | L |

| Key | Action |
|-----|--------|
| 1-5 | Set speed (1=1.0, 2=2.0, 3=5.0, 4=10.0, 5=20.0) |
| Z | Go to home position |
| X | Go to zero position |
| P | Print current joint positions |
| ESC | Quit |

### Telegrip (Web UI)

Browser-based keyboard control with live joint visualization. Works over SSH/headless — no X11 needed.

```bash
./scripts/telegrip.sh /dev/ttyACM0
```

Or directly:

```bash
python telegrip/elrobot_telegrip.py --port /dev/ttyACM0
```

Open the URL shown in terminal (default: `https://localhost:8443`). The WebSocket runs on port `8442`.

**Simulation mode** (no physical robot):

```bash
python telegrip/elrobot_telegrip.py --no-robot
# Or:
./scripts/telegrip.sh --no-robot
```

> **Config:** `telegrip/config.yaml` — adjust `angle_step`, `pos_step`, network ports, and `send_interval`.

### Leader-Follower Teleoperation

Control the follower arm in real-time using the leader arm:

```bash
./scripts/teleoperate.sh /dev/ttyACM0 /dev/ttyACM1
```

Or directly:

```bash
lerobot-teleoperate \
    --robot.type=elrobot_follower --robot.port=/dev/ttyACM0 \
    --teleop.type=elrobot_leader --teleop.port=/dev/ttyACM1
```

> **Config:** `configs/teleoperate.yaml`

### Record Dataset

Record teleoperation episodes for imitation learning:

```bash
./scripts/record.sh my-elrobot-dataset /dev/ttyACM0 /dev/ttyACM1
```

Or directly:

```bash
lerobot-record \
    --robot.type=elrobot_follower --robot.port=/dev/ttyACM0 \
    --teleop.type=elrobot_leader --teleop.port=/dev/ttyACM1 \
    --repo-id=my-elrobot-dataset \
    --num-episodes=50 \
    --fps=30
```

> **Config:** `configs/record.yaml`

### Train Policy

```bash
lerobot-train \
    --dataset.repo_id=my-elrobot-dataset \
    --policy.type=act \
    --output_dir=outputs/train/elrobot_act
```

### Replay / Evaluate

```bash
lerobot-replay \
    --robot.type=elrobot_follower --robot.port=/dev/ttyACM0 \
    --repo-id=my-elrobot-dataset \
    --episode=0
```

---

## Project Structure

```
elrobot_project/
├── README.md
├── configs/
│   ├── calibrate_follower.yaml
│   ├── calibrate_leader.yaml
│   ├── teleoperate.yaml
│   └── record.yaml
├── elrobot_follower/              # LeRobot robot driver (source reference)
│   ├── __init__.py
│   ├── config_elrobot_follower.py
│   └── elrobot_follower.py
├── elrobot_leader/                # LeRobot teleoperator driver (source reference)
│   ├── __init__.py
│   ├── config_elrobot_leader.py
│   └── elrobot_leader.py
├── telegrip/                      # Web-based keyboard control
│   ├── config.yaml
│   └── elrobot_telegrip.py
└── scripts/
    ├── setup_motors.sh
    ├── calibrate.sh
    ├── teleoperate.sh
    ├── record.sh
    ├── scan_bus.py
    ├── keyboard_control.py        # Terminal keyboard control
    ├── keyboard_teleop.sh
    └── telegrip.sh                # Web UI launcher
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `No module named lerobot.calibrate` | Use `lerobot-calibrate` (CLI tool), not `python -m lerobot.calibrate` |
| `Missing motor IDs` / empty motor list | Servos not powered, not wired, or IDs not assigned. Run `scan_bus.py` first |
| `NotImplementedError` on setup_motors | Clear pycache: `find ~/lerobot -name "*.pyc" -delete` |
| Port not found | Check `ls /dev/ttyACM*` or `ls /dev/ttyUSB*` |
| Permission denied on `/dev/ttyACM*` | Run `sudo usermod -aG dialout $USER` then log out/in |
| Servos shaking | Reduce P_Coefficient in driver (default set to 16) |
| `ModuleNotFoundError: websockets` | Run `pip install websockets` |

## References

- [norma-core/norma-core](https://github.com/norma-core/norma-core) - ElRobot hardware (CAD, STL, URDF, assembly manuals)
- [huggingface/lerobot](https://github.com/huggingface/lerobot) - LeRobot framework
- [ElRobot Isaac Sim Integration](~/ElRobot/) - Isaac Sim + Meta Quest VR teleoperation
