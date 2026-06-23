#!/usr/bin/env python3
# Confirm that writing a setpoint is actually reflected on the device.
#
# Writes distinct temperature and speed setpoints, reads them back, and
# restores the originals. Sets setpoints only (no start_heater /
# start_motor), so nothing physically heats or stirs.
#
# Usage: python3 claude_test/check_setpoints.py [PORT]

import os
import sys

from hotplate_controller import RctDigital, find_rct_port

TEMP_TARGETS = (30.0, 40.0)  # within 0..310 C, distinct from default
TEMP_TOL = 0.6  # device resolution 1 K
SPEED_TARGETS = (300.0, 500.0)  # within 0..1500 rpm
SPEED_TOL = 5.0  # set accuracy 10 rpm


def resolve_port(argv):
    if len(argv) > 1:
        return argv[1]
    return find_rct_port() or os.environ.get("RCT_PORT")


def check_axis(name, unit, read, write, targets, tol):
    original = read()
    print(f"[{name} setpoint]")
    print(f"         original: {original} {unit}")
    reflected = True
    try:
        for target in targets:
            write(target)
            readback = read()
            ok = abs(readback - target) <= tol
            mark = "OK" if ok else "MISMATCH"
            print(f"         set {target} -> read {readback} {unit}  {mark}")
            reflected = reflected and ok
        return reflected
    finally:
        write(original)
        print(f"         restored: {original} {unit}")


def main():
    port = resolve_port(sys.argv)
    if not port:
        print("FAIL: no RCT digital found (set PORT arg or $RCT_PORT).")
        return 1
    print(f"connecting to {port} ...")
    with RctDigital(port) as rct:
        temp_ok = check_axis(
            "temperature",
            "C",
            rct.read_target_temperature,
            rct.set_target_temperature,
            TEMP_TARGETS,
            TEMP_TOL,
        )
        speed_ok = check_axis(
            "speed",
            "rpm",
            rct.read_target_speed,
            rct.set_target_speed,
            SPEED_TARGETS,
            SPEED_TOL,
        )
    print(
        f"RESULT: temperature reflected = {temp_ok}, "
        f"speed reflected = {speed_ok}"
    )
    return 0 if (temp_ok and speed_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
