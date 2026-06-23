# HotplateController

> Control an **IKA RCT digital** magnetic stirring hotplate from
> Python, over a single USB cable.

This guide assumes you have **never used this device or the `ika`
Python library before**. It walks you through plugging in, finding the
device, and reading/controlling it in a few lines of code.

---

## What is this?

The **IKA Plate (RCT digital)** is a laboratory **hotplate magnetic
stirrer**: it heats a sample and spins a magnetic stir bar in the
vessel sitting on its plate. The device has a USB port, so a computer
can read its sensors and send it commands.

This project is a small, friendly Python wrapper around that. Instead of
learning the low-level serial protocol, you write:

```python
rct.read_plate_temperature()   # how hot is the plate right now?
rct.set_target_temperature(40) # I want it to go to 40 °C
```

Under the hood it uses the community [`ika`](https://pypi.org/project/ika/)
library and adds the safety and convenience pieces a first-time user
needs (timeouts, value checks, clearer errors, automatic port
detection).

---

## A 30-second primer (for newcomers)

- **USB virtual COM port** — When you plug the device in, Linux shows it
  as a file such as `/dev/ttyACM0`. Your program "talks" to the device
  by reading from and writing to that file. You normally never touch it
  directly; `find_rct_port()` finds it for you.
- **Setpoint vs. actual value** — The *setpoint* (target) is what you
  ask for ("heat to 40 °C"). The *actual* value is what the sensor reads
  right now. **Setting a setpoint does not start heating.** You start the
  heater separately with `start_heater()`. The same is true for stirring.

---

## Before you start

- A computer running **Linux** (tested on Ubuntu / Docker).
- **Python 3.9 or newer**.
- The **IKA RCT digital**, powered on, connected with the included
  **USB A–B cable**.
- No driver to install: on Linux the device appears automatically (via
  the built-in `cdc_acm` kernel module).

---

## Step 1 — Install

```bash
pip install -e .
```

This installs this package plus its dependencies (`ika`, `pyserial`).

## Step 2 — Find your device

```bash
python3 -c "from hotplate_controller import find_rct_port; print(find_rct_port())"
```

You should see something like `/dev/ttyACM1`. If it prints `None`, the
device was not found — see [Troubleshooting](#troubleshooting).

## Step 3 — Run the demo

```bash
python3 main.py
```

Expected output (your numbers will differ):

```
connecting to /dev/ttyACM1 [setpoint-only (safe)] ...
1) device information
   port           : /dev/ttyACM1
   name           : RCT digital
   safety temp    : 370.0 C
2) temperature control
   current temp   : 16.0 C
   original setpt : 21.0 C
   new setpoint   : 30.0 C
   restored setpt : 21.0 C
3) speed control
   current speed  : 0.0 rpm
   original setpt : 200.0 rpm
   new setpoint   : 300.0 rpm
   restored setpt : 200.0 rpm
done.
```

This run is **safe**: it only changes setpoints and reads values — it
does **not** heat or stir — and it restores the original setpoints when
finished. (`current speed: 0.0 rpm` is normal: the motor is off.)

To also see the heater and motor physically run for a couple of seconds,
opt in explicitly — **only with the plate clear and safe**:

```bash
RCT_ACTUATE=1 python3 main.py
```

---

## Step 4 — Use it in your own code

```python
from hotplate_controller import RctDigital, find_rct_port

# `with` makes sure the serial port is closed for you afterwards.
with RctDigital(find_rct_port()) as rct:
    # 1) device information
    print(rct.read_name())                # 'RCT digital'

    # 2) temperature: read, then control
    print(rct.read_plate_temperature())   # current plate temp, °C
    rct.set_target_temperature(40)        # set target (does NOT heat yet)
    rct.start_heater()                    # <- THIS actually heats
    # ... your experiment ...
    rct.stop_heater()

    # 3) speed: read, then control
    rct.set_target_speed(300)             # target speed, rpm
    rct.start_motor()                     # start stirring
    print(rct.read_speed())               # current actual speed, rpm
    rct.stop_motor()
```

### What you can call

| Method | What it does |
|--------|--------------|
| `read_name()` | Device model name, e.g. `'RCT digital'` |
| `read_plate_temperature()` | Current hotplate temperature (°C) |
| `read_probe_temperature()` | Current external probe temperature (°C) |
| `read_speed()` | Current actual stir speed (rpm) |
| `read_target_temperature()` | Temperature setpoint (°C) |
| `read_target_speed()` | Speed setpoint (rpm) |
| `read_safety_temperature()` | Configured safety temperature (°C) |
| `set_target_temperature(c)` | Set temperature target (0–310 °C) |
| `set_target_speed(rpm)` | Set speed target (0–1500 rpm) |
| `start_heater()` / `stop_heater()` | Begin / end heating |
| `start_motor()` / `stop_motor()` | Begin / end stirring |
| `reset()` | Return device to normal operating mode |
| `enable_watchdog_mode_1(s)` / `_2(s)` | Safety watchdog (20–1500 s) |

Values outside the allowed ranges raise `RctRangeError`, so you cannot
accidentally command, say, 500 °C.

---

## ⚠️ Safety notes

- **Heating is real.** `start_heater()` drives the plate toward the
  setpoint (up to 310 °C). Never run it unattended, dry, or with
  flammable material on the plate.
- Setting a setpoint **alone** is harmless. Nothing physically happens
  until you call `start_heater()` / `start_motor()`.
- Keep the device's hardware safety-temperature dial set sensibly; the
  watchdog (`enable_watchdog_mode_1/2`) can switch everything off if the
  computer stops talking to the device.

---

## Check that your hardware works

Both scripts below are safe (no heating, no stirring):

```bash
python3 claude_test/verify_device.py     # identity query (IN_NAME)
python3 claude_test/check_setpoints.py   # write a setpoint, read it back
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `find_rct_port()` returns `None` | Check the USB cable and that the device is on. List ports with `ls /dev/ttyACM*`. You can also pass the port by hand: `python3 main.py /dev/ttyACM0`. |
| `Permission denied` opening the port | Add yourself to the `dialout` group: `sudo usermod -aG dialout $USER`, then log out and back in. |
| Connects, but reads time out | Another program may already hold the port, or the wrong port was chosen. Close other software and retry. |

The serial settings (9600 baud, 7 data bits, even parity, 1 stop bit)
are handled for you — you never configure them by hand.

---

## How this relates to the `ika` library

This wraps `ika.magnetic_stirrer.MagneticStirrer` and adds what a real
deployment needs but `ika` leaves out:

- a **read timeout** (`ika` leaves it unset, so a read could otherwise
  hang forever),
- **setpoint range validation** against the device manual,
- **device error-code descriptions** (`Er02`..`Er46`),
- **USB auto-detection** by hardware id, and
- a robust `read_name()` that tolerates a quirk where `ika`'s own
  `read_device_name()` can crash on a real RCT digital.

The device manual lives in [`docs/`](docs/).

---

## Project layout

| Path | Purpose |
|------|---------|
| `main.py` | Ordered demo: info → temperature → speed |
| `hotplate_controller/rct_digital.py` | `RctDigital` wrapper over `ika` |
| `hotplate_controller/limits.py` | Allowed ranges + value validators |
| `hotplate_controller/errors.py` | Exceptions + `Er02`..`Er46` map |
| `hotplate_controller/ports.py` | USB port auto-detection |
| `tests/` | Pure unit tests (no hardware needed) |
| `claude_test/` | Real-device diagnostic scripts |

## Development

```bash
pytest
ruff check . && ruff format --check .
```
