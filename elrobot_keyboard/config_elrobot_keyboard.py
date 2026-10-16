from dataclasses import dataclass

from ..config import TeleoperatorConfig


@TeleoperatorConfig.register_subclass("elrobot_keyboard")
@dataclass
class ElRobotKeyboardConfig(TeleoperatorConfig):
    step: float = 1.0  # target change per key event (same units as the follower's positions)
