#!/usr/bin/env python
"""
ElRobot Telegrip - Web-based keyboard teleoperation for ElRobot 7+1 DOF arm.

Provides a web UI with keyboard control for the ElRobot arm.
Supports both joint-space and end-effector control modes.

Usage:
    python telegrip/elrobot_telegrip.py --port /dev/ttyACM0
    python telegrip/elrobot_telegrip.py --port /dev/ttyACM0 --no-robot  # simulation only
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import ssl
import sys
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread
from typing import Optional

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── ElRobot joint configuration ──────────────────────────────────────────────

ELROBOT_JOINT_NAMES = [
    "shoulder_yaw", "shoulder_pitch", "elbow_yaw", "elbow_pitch",
    "wrist_pitch", "wrist_roll", "wrist_yaw", "gripper"
]
NUM_JOINTS = len(ELROBOT_JOINT_NAMES)
GRIPPER_INDEX = 7

# Key mapping for web keyboard control
# Single arm: WASD + QE for position, RTFG for wrist, O/L for gripper
WEB_KEY_MAP = {
    # Position control (cartesian-like via joint deltas)
    'w': ("shoulder_pitch", +1),
    's': ("shoulder_pitch", -1),
    'a': ("shoulder_yaw", +1),
    'd': ("shoulder_yaw", -1),
    'q': ("elbow_yaw", +1),
    'e': ("elbow_yaw", -1),
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

ANGLE_STEP = 5.0  # degrees per keypress


# ── Robot Interface ──────────────────────────────────────────────────────────

class ElRobotInterface:
    """Interface to the physical ElRobot arm via lerobot driver."""

    def __init__(self, port: str, enable_robot: bool = True):
        self.port = port
        self.enable_robot = enable_robot
        self.robot = None
        self.is_connected = False
        self.current_angles = np.zeros(NUM_JOINTS)

    def connect(self) -> bool:
        if not self.enable_robot:
            logger.info("Robot disabled, running in simulation mode")
            self.is_connected = True
            return True

        try:
            from lerobot.robots.elrobot_follower.config_elrobot_follower import ElRobotFollowerConfig
            from lerobot.robots.elrobot_follower.elrobot_follower import ElRobotFollower

            config = ElRobotFollowerConfig(
                port=self.port,
                use_degrees=True,
                disable_torque_on_disconnect=True,
            )
            self.robot = ElRobotFollower(config)
            self.robot.connect()
            self.is_connected = True

            # Read initial state
            obs = self.robot.get_observation()
            for i, name in enumerate(ELROBOT_JOINT_NAMES):
                self.current_angles[i] = obs.get(f"{name}.pos", 0.0)

            logger.info(f"ElRobot connected on {self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    def get_angles(self) -> np.ndarray:
        if self.robot and self.is_connected:
            try:
                obs = self.robot.get_observation()
                for i, name in enumerate(ELROBOT_JOINT_NAMES):
                    self.current_angles[i] = obs.get(f"{name}.pos", 0.0)
            except Exception as e:
                logger.error(f"Read error: {e}")
        return self.current_angles.copy()

    def set_angles(self, angles: np.ndarray):
        self.current_angles = angles.copy()
        if self.robot and self.is_connected:
            try:
                action = {f"{name}.pos": float(angles[i]) for i, name in enumerate(ELROBOT_JOINT_NAMES)}
                self.robot.send_action(action)
            except Exception as e:
                logger.error(f"Write error: {e}")

    def disconnect(self):
        if self.robot and self.is_connected:
            try:
                self.robot.disconnect()
            except Exception:
                pass
        self.is_connected = False
        logger.info("ElRobot disconnected")


# ── Web Keyboard Handler ────────────────────────────────────────────────────

class WebKeyboardHandler:
    """Processes keyboard events from the web UI and updates robot joints."""

    def __init__(self, robot_interface: ElRobotInterface):
        self.robot = robot_interface
        self.pressed_keys = set()
        self.angle_step = ANGLE_STEP

    def on_key_press(self, key: str):
        key = key.lower()
        self.pressed_keys.add(key)

    def on_key_release(self, key: str):
        key = key.lower()
        self.pressed_keys.discard(key)

    def update(self):
        """Apply pressed keys as joint deltas."""
        if not self.pressed_keys:
            return

        angles = self.robot.get_angles()
        changed = False

        for key in list(self.pressed_keys):
            if key in WEB_KEY_MAP:
                joint_name, direction = WEB_KEY_MAP[key]
                idx = ELROBOT_JOINT_NAMES.index(joint_name)
                angles[idx] += direction * self.angle_step
                changed = True

        if changed:
            self.robot.set_angles(angles)


# ── Web Server ───────────────────────────────────────────────────────────────

def generate_web_ui() -> str:
    """Generate the web UI HTML with ElRobot controls."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>ElRobot Telegrip</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Courier New', monospace; background: #1a1a2e; color: #eee; padding: 20px; }
        h1 { color: #00d4ff; text-align: center; margin-bottom: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .status { background: #16213e; padding: 15px; border-radius: 8px; margin-bottom: 15px;
                  border: 1px solid #0f3460; }
        .status.connected { border-color: #00ff88; }
        .status.disconnected { border-color: #ff4444; }
        .joints { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; }
        .joint { background: #16213e; padding: 12px; border-radius: 8px; border: 1px solid #0f3460; }
        .joint-name { color: #00d4ff; font-weight: bold; font-size: 14px; }
        .joint-value { color: #00ff88; font-size: 18px; margin: 5px 0; }
        .joint-keys { color: #888; font-size: 12px; }
        .controls { background: #16213e; padding: 15px; border-radius: 8px; border: 1px solid #0f3460; }
        .controls h3 { color: #00d4ff; margin-bottom: 10px; }
        .key-row { display: flex; gap: 5px; margin: 3px 0; align-items: center; }
        .key { display: inline-block; background: #0f3460; color: #fff; padding: 4px 10px;
               border-radius: 4px; font-size: 14px; min-width: 30px; text-align: center; }
        .key.active { background: #00d4ff; color: #000; }
        .label { color: #888; font-size: 12px; min-width: 120px; }
        #log { background: #0a0a1a; padding: 10px; border-radius: 8px; margin-top: 15px;
               max-height: 150px; overflow-y: auto; font-size: 12px; color: #888; }
    </style>
</head>
<body>
    <div class="container">
        <h1>ElRobot Telegrip</h1>
        <div class="status" id="status">Connecting...</div>
        <div class="joints" id="joints"></div>
        <div class="controls">
            <h3>Keyboard Controls</h3>
            <div class="key-row"><span class="label">shoulder_yaw</span> <span class="key" id="k-a">A</span> / <span class="key" id="k-d">D</span></div>
            <div class="key-row"><span class="label">shoulder_pitch</span> <span class="key" id="k-w">W</span> / <span class="key" id="k-s">S</span></div>
            <div class="key-row"><span class="label">elbow_yaw</span> <span class="key" id="k-q">Q</span> / <span class="key" id="k-e">E</span></div>
            <div class="key-row"><span class="label">elbow_pitch</span> <span class="key" id="k-r">R</span> / <span class="key" id="k-f">F</span></div>
            <div class="key-row"><span class="label">wrist_pitch</span> <span class="key" id="k-t">T</span> / <span class="key" id="k-g">G</span></div>
            <div class="key-row"><span class="label">wrist_roll</span> <span class="key" id="k-y">Y</span> / <span class="key" id="k-h">H</span></div>
            <div class="key-row"><span class="label">wrist_yaw</span> <span class="key" id="k-u">U</span> / <span class="key" id="k-j">J</span></div>
            <div class="key-row"><span class="label">gripper</span> <span class="key" id="k-o">O</span> / <span class="key" id="k-l">L</span></div>
        </div>
        <div id="log"></div>
    </div>
    <script>
        const JOINTS = ["shoulder_yaw","shoulder_pitch","elbow_yaw","elbow_pitch",
                        "wrist_pitch","wrist_roll","wrist_yaw","gripper"];
        const KEY_JOINTS = {a:"shoulder_yaw",d:"shoulder_yaw",w:"shoulder_pitch",s:"shoulder_pitch",
                           q:"elbow_yaw",e:"elbow_yaw",r:"elbow_pitch",f:"elbow_pitch",
                           t:"wrist_pitch",g:"wrist_pitch",y:"wrist_roll",h:"wrist_roll",
                           u:"wrist_yaw",j:"wrist_yaw",o:"gripper",l:"gripper"};

        // Create joint displays
        const jointsDiv = document.getElementById('joints');
        JOINTS.forEach(j => {
            const d = document.createElement('div');
            d.className = 'joint';
            d.innerHTML = `<div class="joint-name">${j}</div><div class="joint-value" id="val-${j}">0.00</div>`;
            jointsDiv.appendChild(d);
        });

        let ws;
        function connectWS() {
            const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${proto}//${location.hostname}:WS_PORT`);
            ws.onopen = () => {
                document.getElementById('status').textContent = 'Connected';
                document.getElementById('status').className = 'status connected';
            };
            ws.onclose = () => {
                document.getElementById('status').textContent = 'Disconnected - reconnecting...';
                document.getElementById('status').className = 'status disconnected';
                setTimeout(connectWS, 2000);
            };
            ws.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data);
                    if (data.joints) {
                        JOINTS.forEach((j, i) => {
                            const el = document.getElementById(`val-${j}`);
                            if (el) el.textContent = data.joints[i].toFixed(2);
                        });
                    }
                } catch(err) {}
            };
        }
        connectWS();

        document.addEventListener('keydown', (e) => {
            const k = e.key.toLowerCase();
            const el = document.getElementById(`k-${k}`);
            if (el) el.classList.add('active');
            if (ws && ws.readyState === 1) ws.send(JSON.stringify({type:'keydown', key:k}));
        });
        document.addEventListener('keyup', (e) => {
            const k = e.key.toLowerCase();
            const el = document.getElementById(`k-${k}`);
            if (el) el.classList.remove('active');
            if (ws && ws.readyState === 1) ws.send(JSON.stringify({type:'keyup', key:k}));
        });
    </script>
</body>
</html>"""


class TelegripRequestHandler(SimpleHTTPRequestHandler):
    """HTTP handler serving the web UI."""

    html_content = ""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(self.html_content.encode())

    def log_message(self, format, *args):
        pass  # Suppress HTTP logs


# ── Main Server ──────────────────────────────────────────────────────────────

class ElRobotTelegrip:
    """Main telegrip server for ElRobot."""

    def __init__(self, port: str, http_port: int = 8443, ws_port: int = 8442,
                 enable_robot: bool = True, fps: float = 20.0):
        self.robot = ElRobotInterface(port, enable_robot)
        self.keyboard = WebKeyboardHandler(self.robot)
        self.http_port = http_port
        self.ws_port = ws_port
        self.fps = fps
        self.running = False

    async def run(self):
        """Start the telegrip server."""
        # Connect robot
        if not self.robot.connect():
            if self.robot.enable_robot:
                logger.error("Cannot start without robot connection")
                return

        self.running = True

        # Generate SSL certs if needed
        cert_path = Path(__file__).parent / "cert.pem"
        key_path = Path(__file__).parent / "key.pem"
        use_ssl = cert_path.exists() and key_path.exists()

        # Start HTTP server
        html = generate_web_ui().replace("WS_PORT", str(self.ws_port))
        TelegripRequestHandler.html_content = html

        httpd = HTTPServer(("0.0.0.0", self.http_port), TelegripRequestHandler)
        if use_ssl:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(str(cert_path), str(key_path))
            httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
            proto = "https"
        else:
            proto = "http"

        http_thread = Thread(target=httpd.serve_forever, daemon=True)
        http_thread.start()

        logger.info(f"Web UI: {proto}://localhost:{self.http_port}")

        # Start WebSocket server
        try:
            import websockets
        except ImportError:
            logger.error("Install websockets: pip install websockets")
            self.robot.disconnect()
            return

        clients = set()

        async def ws_handler(websocket, path=None):
            clients.add(websocket)
            try:
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data.get("type") == "keydown":
                            self.keyboard.on_key_press(data["key"])
                        elif data.get("type") == "keyup":
                            self.keyboard.on_key_release(data["key"])
                    except json.JSONDecodeError:
                        pass
            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                clients.discard(websocket)

        if use_ssl:
            ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_ctx.load_cert_chain(str(cert_path), str(key_path))
            ws_server = await websockets.serve(ws_handler, "0.0.0.0", self.ws_port, ssl=ssl_ctx)
        else:
            ws_server = await websockets.serve(ws_handler, "0.0.0.0", self.ws_port)

        logger.info(f"WebSocket server on port {self.ws_port}")
        logger.info("Press Ctrl+C to stop")

        # Control loop
        dt = 1.0 / self.fps
        try:
            while self.running:
                self.keyboard.update()

                # Broadcast joint state
                angles = self.robot.get_angles()
                msg = json.dumps({"joints": angles.tolist()})
                if clients:
                    await asyncio.gather(
                        *[c.send(msg) for c in clients.copy()],
                        return_exceptions=True
                    )

                await asyncio.sleep(dt)
        except asyncio.CancelledError:
            pass
        finally:
            ws_server.close()
            httpd.shutdown()
            self.robot.disconnect()

    def stop(self):
        self.running = False


def main():
    parser = argparse.ArgumentParser(description="ElRobot Telegrip - Web Keyboard Control")
    parser.add_argument("--port", default="/dev/ttyACM0", help="Serial port")
    parser.add_argument("--http-port", type=int, default=8443, help="HTTP server port")
    parser.add_argument("--ws-port", type=int, default=8442, help="WebSocket server port")
    parser.add_argument("--no-robot", action="store_true", help="Run without physical robot")
    parser.add_argument("--fps", type=float, default=20.0, help="Control loop frequency")
    args = parser.parse_args()

    server = ElRobotTelegrip(
        port=args.port,
        http_port=args.http_port,
        ws_port=args.ws_port,
        enable_robot=not args.no_robot,
        fps=args.fps,
    )

    loop = asyncio.new_event_loop()

    def shutdown(sig, frame):
        logger.info("Shutting down...")
        server.stop()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        loop.run_until_complete(server.run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
