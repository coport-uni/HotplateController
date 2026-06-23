# HotplateController

Serial controller for the **IKA Plate (RCT 5 digital)** magnetic
stirrer / hotplate.

It depends on the [`ika`](https://pypi.org/project/ika/) package as the
primary serial driver and uses the device manual (`docs/`) as a
supplementary reference for the parts `ika` does not cover: a pyserial
read timeout, setpoint range validation, device error-code descriptions,
and a `read_name` that tolerates the trailing carriage return `ika`
leaves unstripped.

Target environment: **Linux / Docker**, USB virtual COM port
(`/dev/ttyACM*`, STM32 VCP, USB VID:PID `0483:5740`).

## Install

```bash
pip install -e .
```

This pulls in `ika` and `pyserial`. On Linux the RCT digital enumerates
natively via the `cdc_acm` kernel module — no vendor driver is needed.

## Usage

```python
from hotplate_controller import RctDigital, find_rct_port

port = find_rct_port()  # auto-detect by USB VID:PID, e.g. /dev/ttyACM1
with RctDigital(port) as rct:
    print(rct.read_name())            # 'RCT digital'
    print(rct.read_plate_temperature())
    rct.set_target_temperature(40)    # setpoint only; does not heat
    rct.start_heater()                # begin heating toward setpoint
```

All setpoints are range-checked against the manual (temperature
0–310 °C, speed 0–1500 rpm, watchdog 20–1500 s) and raise
`RctRangeError` when out of bounds.

## Layout

| Path | Purpose |
|------|---------|
| `hotplate_controller/rct_digital.py` | `RctDigital` wrapper over `ika.MagneticStirrer` |
| `hotplate_controller/limits.py` | Manual-derived ranges + pure validators |
| `hotplate_controller/errors.py` | Exceptions + `Er02`..`Er46` code map |
| `hotplate_controller/ports.py` | Port auto-detection by USB VID:PID |
| `tests/` | Pure unit tests (no hardware) |
| `claude_test/verify_device.py` | Real-device verification script |

## Verify against a real device

```bash
python3 claude_test/verify_device.py [PORT]
```

Step 1 is a non-actuating `IN_NAME` identity query. If that fails it
falls back to a temperature-setpoint 10 °C → 20 °C round-trip (it does
**not** start heating) and restores the original setpoint.

## Tests

```bash
pytest
ruff check . && ruff format --check .
```
# HotplateController
