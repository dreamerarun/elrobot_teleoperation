import importlib, importlib.util, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != ROOT]

import lerobot.robots, lerobot.teleoperators  # noqa: E402


def load_as(alias, folder):
    init = ROOT / folder / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        alias, init, submodule_search_locations=[str(init.parent)]
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod


fol = load_as("lerobot.robots.elrobot_follower", "elrobot_follower")
load_as("lerobot.teleoperators.elrobot_leader", "elrobot_leader")
kb = load_as("lerobot.teleoperators.elrobot_keyboard", "elrobot_keyboard")

Follower = getattr(fol, "ElRobotFollower", None) or importlib.import_module(
    "lerobot.robots.elrobot_follower.elrobot_follower"
).ElRobotFollower

# cache the follower's latest observation so the keyboard starts from the real pose
_get_obs, _connect = Follower.get_observation, Follower.connect


def get_observation(self, *a, **k):
    obs = _get_obs(self, *a, **k)
    kb.OBS_CACHE.update(obs)
    return obs


def connect(self, *a, **k):
    _connect(self, *a, **k)
    self.get_observation()


Follower.get_observation = get_observation
Follower.connect = connect

cmd = sys.argv.pop(1)
for mod in (f"lerobot.scripts.lerobot_{cmd}", f"lerobot.{cmd}"):
    try:
        main = importlib.import_module(mod).main
        break
    except ModuleNotFoundError:
        continue
else:
    raise SystemExit(f"Could not find a lerobot entrypoint for '{cmd}'")
main()
