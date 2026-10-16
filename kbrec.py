import argparse, importlib, importlib.util, json, os, select, sys, termios, time, tty
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# repo has its own lerobot/ folder; keep it from shadowing the installed one
sys.path = [p for p in sys.path if Path(p or ".").resolve() != ROOT]
import lerobot.robots  # noqa: E402


def load_as(alias, folder):
    init = ROOT / folder / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        alias, init, submodule_search_locations=[str(init.parent)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod


fol = load_as("lerobot.robots.elrobot_follower", "elrobot_follower")
Config = fol.ElRobotFollowerConfig
Robot = getattr(fol, "ElRobotFollower", None) or importlib.import_module(
    "lerobot.robots.elrobot_follower.elrobot_follower").ElRobotFollower

JOINTS = ["shoulder_yaw", "shoulder_pitch", "elbow_yaw", "elbow_pitch",
          "wrist_pitch", "wrist_roll", "wrist_yaw", "gripper"]
PAIRS = ["qa", "ws", "ed", "rf", "tg", "yh", "uj", "ol"]
KEYS = {}
for j, (p, m) in zip(JOINTS, PAIRS):
    KEYS[p] = (j, +1)
    KEYS[m] = (j, -1)
SPEEDS = {"1": 0.5, "2": 1.0, "3": 2.0, "4": 5.0, "5": 10.0}


def joint_keys(obs):
    nums = [k for k, v in obs.items()
            if isinstance(v, (int, float)) or getattr(v, "ndim", None) == 0]
    m = {j: next((k for k in nums if k.startswith(j)), None) for j in JOINTS}
    if any(v is None for v in m.values()):
        if len(nums) == len(JOINTS):
            m = dict(zip(JOINTS, nums))
        else:
            raise SystemExit(f"Can't map joints. Numeric observation keys: {nums}")
    return m


def read_keys(fd):
    data = b""
    while select.select([fd], [], [], 0)[0]:
        chunk = os.read(fd, 1024)
        if not chunk:
            break
        data += chunk
    return data.decode(errors="ignore").lower()


def record(robot, out, fps):
    obs = robot.get_observation()
    jm = joint_keys(obs)
    print("joint mapping:", jm)
    target = {jm[j]: float(obs[jm[j]]) for j in JOINTS}
    frames, rec, t0, step = [], False, 0.0, 1.0

    def save():
        if frames:
            json.dump({"fps": fps, "joint_keys": jm, "frames": frames}, open(out, "w"))
            print(f"\nsaved {len(frames)} frames ({frames[-1]['t']:.1f}s) -> {out}")
        else:
            print("\nnothing recorded, no file written")

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    tty.setcbreak(fd)
    print("keys: q/a w/s e/d r/f t/g y/h u/j o/l  |  1-5 speed  |  SPACE start/stop(save+exit)  |  Ctrl+C quit")
    try:
        while True:
            tl = time.perf_counter()
            stop = False
            for ch in read_keys(fd):
                if ch in SPEEDS:
                    step = SPEEDS[ch]
                elif ch in KEYS:
                    j, s = KEYS[ch]
                    target[jm[j]] += s * step
                elif ch == " ":
                    if not rec:
                        rec, frames, t0 = True, [], time.perf_counter()
                    else:
                        stop = True
            sent = robot.send_action(dict(target))
            if isinstance(sent, dict):  # follower may clip; avoid target wind-up
                for k in target:
                    if k in sent:
                        target[k] = float(sent[k])
            if rec:
                frames.append({"t": time.perf_counter() - t0,
                               "action": {k: float(v) for k, v in target.items()}})
            print(f"\r{'REC' if rec else 'idle'} step={step} frames={len(frames)}   ", end="", flush=True)
            if stop:
                break
            time.sleep(max(0.0, 1 / fps - (time.perf_counter() - tl)))
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        save()


def glide(robot, frm, to, fps, secs=2.0):
    n = max(1, int(secs * fps))
    for i in range(1, n + 1):
        a = i / n
        robot.send_action({k: frm[k] + (to[k] - frm[k]) * a for k in to})
        time.sleep(1 / fps)


def play(robot, path, speed, fps, loops):
    data = json.load(open(path))
    frames = data["frames"]
    first, last = frames[0]["action"], frames[-1]["action"]
    obs = robot.get_observation()
    cur = {k: float(obs[k]) for k in first}
    print("moving to start pose (2 s)...")
    glide(robot, cur, first, fps, 2.0)
    i = 0
    try:
        while loops == 0 or i < loops:
            i += 1
            print(f"loop {i}" + (f"/{loops}" if loops else "  (Ctrl+C to stop)"))
            t0 = time.perf_counter()
            for fr in frames:
                while time.perf_counter() - t0 < fr["t"] / speed:
                    time.sleep(0.001)
                robot.send_action(fr["action"])
            if loops == 0 or i < loops:
                glide(robot, last, first, fps, 1.0)  # return to start pose
        print("done")
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["record", "play"])
    ap.add_argument("--port", default="/dev/ttyACM0")
    ap.add_argument("--id", default=None, help="robot id used at calibration (none if you didn't set one)")
    ap.add_argument("--file", default="run1.json")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--loop", type=int, default=1, help="number of repeats, 0 = forever")
    ap.add_argument("--speed", type=float, default=1.0, help="playback speed")
    a = ap.parse_args()

    robot = Robot(Config(port=a.port, id=a.id))
    robot.connect()
    try:
        if a.mode == "record":
            record(robot, a.file, a.fps)
        else:
            play(robot, a.file, a.speed, a.fps, a.loop)
    finally:
        robot.disconnect()
