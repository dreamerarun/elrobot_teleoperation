#!/usr/bin/env python
"""Scan the serial bus to find connected Feetech servos at all baud rates."""

import argparse
import serial

def scan_bus(port: str):
    print(f"Scanning {port} for Feetech servos...\n")

    try:
        from lerobot.motors.feetech import FeetechMotorsBus
        from lerobot.motors import Motor, MotorNormMode

        bus = FeetechMotorsBus(
            port=port,
            motors={"scan": Motor(1, "sts3215", MotorNormMode.RANGE_M100_100)},
        )

        if not bus.port_handler.openPort():
            print(f"ERROR: Cannot open port {port}")
            return

        baudrates = [1_000_000, 500_000, 250_000, 115_200, 57_600, 38_400, 19_200, 9_600]

        for baud in baudrates:
            bus.port_handler.setBaudRate(baud)
            found_ids = []
            for motor_id in range(0, 253):
                result, error = bus.packet_handler.ping(bus.port_handler, motor_id)
                if error == 0:
                    model = result[0] if result else "unknown"
                    found_ids.append((motor_id, model))

            if found_ids:
                print(f"Baud {baud:>10}: Found {len(found_ids)} motor(s)")
                for mid, model in found_ids:
                    print(f"  - ID {mid}, model number: {model}")
            else:
                print(f"Baud {baud:>10}: No motors found")

        bus.port_handler.closePort()
        print("\nScan complete.")

    except Exception as e:
        print(f"Error: {e}")
        print("\nFallback: testing serial port...")
        try:
            s = serial.Serial(port, 1000000, timeout=1)
            print(f"Port {port} opened OK at 1Mbaud")
            s.close()
        except Exception as e2:
            print(f"Cannot open {port}: {e2}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scan Feetech servo bus")
    parser.add_argument("--port", default="/dev/ttyACM0", help="Serial port")
    args = parser.parse_args()
    scan_bus(args.port)
