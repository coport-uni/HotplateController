"""Demo scenario for the IKA RCT 5 digital controller.

Runs the :class:`RctDigital` features in order:

1. read device information,
2. adjust the temperature setpoint and read the current temperature,
3. adjust the speed setpoint and read the current speed.

By default the scenario is non-actuating: it changes setpoints and reads
values but does NOT start heating or stirring, and it restores the
original setpoints before exiting. Set ``RCT_ACTUATE=1`` to also run the
heater and motor briefly -- only do this with the plate clear and safe.

Usage: python3 main.py [PORT]
  PORT defaults to auto-detection by USB VID:PID, then $RCT_PORT.
"""

import os
import sys
import time

from hotplate_controller import RctDigital, find_rct_port

DEMO_TEMPERATURE_C = 30.0
DEMO_SPEED_RPM = 300.0
SETTLE_S = 2.0
ACTUATE = os.environ.get("RCT_ACTUATE") == "1"


def resolve_port(argv):
    if len(argv) > 1:
        return argv[1]
    return find_rct_port() or os.environ.get("RCT_PORT")


def show_device_info(rct):
    print("1) device information")
    print(f"   port           : {rct.port}")
    print(f"   name           : {rct.read_name()}")
    print(f"   safety temp    : {rct.read_safety_temperature()} C")


def control_temperature(rct):
    print("2) temperature control")
    original = rct.read_target_temperature()
    print(f"   current temp   : {rct.read_plate_temperature()} C")
    print(f"   original setpt : {original} C")
    rct.set_target_temperature(DEMO_TEMPERATURE_C)
    print(f"   new setpoint   : {rct.read_target_temperature()} C")
    if ACTUATE:
        rct.start_heater()
        time.sleep(SETTLE_S)
        print(f"   heating temp   : {rct.read_plate_temperature()} C")
        rct.stop_heater()
    rct.set_target_temperature(original)
    print(f"   restored setpt : {rct.read_target_temperature()} C")


def control_speed(rct):
    print("3) speed control")
    original = rct.read_target_speed()
    print(f"   current speed  : {rct.read_speed()} rpm")
    print(f"   original setpt : {original} rpm")
    rct.set_target_speed(DEMO_SPEED_RPM)
    print(f"   new setpoint   : {rct.read_target_speed()} rpm")
    if ACTUATE:
        rct.start_motor()
        time.sleep(SETTLE_S)
        print(f"   running speed  : {rct.read_speed()} rpm")
        rct.stop_motor()
    rct.set_target_speed(original)
    print(f"   restored setpt : {rct.read_target_speed()} rpm")


def main():
    port = resolve_port(sys.argv)
    if not port:
        print("no RCT digital found (set PORT arg or $RCT_PORT).")
        return 1
    mode = "ACTUATING" if ACTUATE else "setpoint-only (safe)"
    print(f"connecting to {port} [{mode}] ...")
    with RctDigital(port) as rct:
        show_device_info(rct)
        control_temperature(rct)
        control_speed(rct)
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
