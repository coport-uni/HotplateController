#!/usr/bin/env python3
# Real-device verification for the IKA RCT 5 digital.
#
# Step 1 (non-actuating): query the device identity with IN_NAME.
# Step 2 (fallback, only if step 1 fails): change the temperature
#   setpoint 10 C -> 20 C and read it back, then restore it. This does
#   NOT call start_heater, so no actual heating occurs.
#
# Usage: python3 claude_test/verify_device.py [PORT]
#   PORT defaults to auto-detection by USB VID:PID, then $RCT_PORT.

import os
import sys

from hotplate_controller import RctDigital, find_rct_port
from hotplate_controller.errors import RctError

SETPOINT_LOW = 10.0
SETPOINT_HIGH = 20.0
TOLERANCE = 0.6  # device resolution is 1 K


def resolve_port(argv):
    if len(argv) > 1:
        return argv[1]
    detected = find_rct_port()
    if detected:
        return detected
    return os.environ.get("RCT_PORT")


def step1_identify(rct):
    print("[step 1] non-actuating identity query (IN_NAME)...")
    name = rct.read_name()
    print(f"         device name : {name!r}")
    # Best-effort extra reads; ignore if a particular one is unsupported.
    for label, reader in (
        ("set temperature", rct.read_target_temperature),
        ("plate temperature", rct.read_plate_temperature),
        ("set speed", rct.read_target_speed),
    ):
        try:
            print(f"         {label:<16}: {reader()}")
        except RctError as exc:
            print(f"         {label:<16}: (skipped: {exc})")
    return bool(name)


def step2_setpoint_roundtrip(rct):
    print(
        "[step 2] fallback: temperature setpoint 10 C -> 20 C (no heating)..."
    )
    original = rct.read_target_temperature()
    print(f"         original setpoint: {original} C")
    try:
        for target in (SETPOINT_LOW, SETPOINT_HIGH):
            rct.set_target_temperature(target)
            readback = rct.read_target_temperature()
            print(f"         set {target} C -> read {readback} C")
            if abs(readback - target) > TOLERANCE:
                print("         MISMATCH")
                return False
        return True
    finally:
        rct.set_target_temperature(original)
        print(f"         restored setpoint: {original} C")


def main():
    port = resolve_port(sys.argv)
    if not port:
        print("FAIL: no RCT digital found (set PORT arg or $RCT_PORT).")
        return 1
    print(f"connecting to {port} ...")
    try:
        with RctDigital(port) as rct:
            try:
                if step1_identify(rct):
                    print("PASS: non-actuating communication OK.")
                    return 0
                print("step 1 returned no name; trying fallback.")
            except RctError as exc:
                print(f"step 1 failed ({exc}); trying fallback.")
            if step2_setpoint_roundtrip(rct):
                print("PASS: setpoint round-trip OK (no heating).")
                return 0
            print("FAIL: setpoint round-trip mismatch.")
            return 1
    except RctError as exc:
        print(f"FAIL: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 - report any driver error
        print(f"FAIL: unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
