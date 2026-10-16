import os
import re
import select
import sys
import termios
import tty

from ..teleoperator import Teleoperator
from .config_elrobot_keyboard import ElRobotKeyboardConfig

OBS_CACHE = {}  # filled by the follower wrapper in elrun.py

JOINTS = ["shoulder_yaw", "shoulder_pitch", "elbow_yaw", "elbow_pitch",
          "wrist_pitch", "wrist_roll", "wrist_yaw", "gripper"]
PAIRS = ["qa", "ws", "ed", "rf", "tg", "yh", "uj", "ol"]
KEYS = {}
for joint, (plus, minus) in zip(JOINTS, PAIRS):
    KEYS[plus] = (joint, +1)
    KEYS[minus] = (joint, -1)
SPEEDS = {"1": 0.5, "2": 1.0, "3": 2.0, "4": 5.0, "5": 10.0}
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z~]|\x1b")


class ElRobotKeyboard(Teleoperator):
    config_class = ElRobotKeyboardConfig
    name = "elrobot_keyboard"

    def __init__(self, config: ElRobotKeyboardConfig):
        super().__init__(config)
        self.config = config
        self.step = config.step
        self._target = None
        self._fd = None
        self._old = None
        self._connected = False

    @property
    def action_features(self):
        return {f"{j}.pos": float for j in JOINTS}

    @property
    def feedback_features(self):
        return {}

    @property
    def is_connected(self):
        return self._connected

    @property
    def is_calibrated(self):
        return True

    def connect(self, calibrate: bool = True):
        if not sys.stdin.isatty():
            raise RuntimeError("elrobot_keyboard needs a real terminal (stdin must be a TTY)")
        self._fd = sys.stdin.fileno()
        self._old = termios.tcgetattr(self._fd)
        tty.setcbreak(self._fd)  # Ctrl-C still works
        self._connected = True

    def calibrate(self):
        pass

    def configure(self):
        pass

    def _init_target(self):
        keys = list(self.action_features)
        missing = [k for k in keys if k not in OBS_CACHE]
        if missing:
            have = [k for k, v in OBS_CACHE.items() if not getattr(v, "ndim", 0)]
            raise RuntimeError(
                f"Follower observation has no {missing}. Numeric observation keys are {have}. "
                "Fix JOINTS / the '.pos' suffix in elrobot_keyboard.py to match."
            )
        self._target = {k: float(OBS_CACHE[k]) for k in keys}

    def get_action(self):
        if self._target is None:
            self._init_target()
        data = b""
        while select.select([sys.stdin], [], [], 0)[0]:
            chunk = os.read(self._fd, 1024)
            if not chunk:
                break
            data += chunk
        for ch in ANSI.sub("", data.decode(errors="ignore")).lower():
            if ch in SPEEDS:
                self.step = SPEEDS[ch]
            elif ch in KEYS:
                joint, sign = KEYS[ch]
                self._target[f"{joint}.pos"] += sign * self.step
        return dict(self._target)

    def send_feedback(self, feedback):
        pass

    def disconnect(self):
        if self._connected:
            termios.tcflush(self._fd, termios.TCIFLUSH)
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old)
        self._connected = False
