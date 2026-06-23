# ToDo

Append-only task history (per CLAUDE.md Section 4).

## Active Tasks

### feat/rct-digital-comms — RCT digital serial communication
Goal: control the IKA Plate (RCT 5 digital) over its USB virtual COM
port, depending on the `ika` package as the primary driver and using the
device manual (`docs/`) as a supplementary reference (timeouts, value
ranges, error codes). Target environment: Linux/Docker, `/dev/ttyACM*`.

- [ ] Scaffold `hotplate_controller` package + `pyproject.toml`
- [x] `limits.py` — manual-derived ranges + pure validation helpers
- [x] `errors.py` — exceptions + Er02..Er46 code map
- [x] `ports.py` — auto-detect by USB VID:PID 0483:5740
- [x] `rct_digital.py` — `RctDigital` wrapper over `ika.MagneticStirrer`
      (sets read timeout, validates ranges, robust `read_name`)
- [x] `claude_test/verify_device.py` — real-device verification
- [x] `tests/test_rct_digital.py` — pure validation unit tests (no dummy)
- [x] Run ruff + pytest (ruff clean, 20 passed)
- [x] Verify against the real device on `/dev/ttyACM1`

Note: no git remote is configured for this repo, so the GitHub issue /
PR steps from CLAUDE.md Section 4 are not applicable for this task.

## Completed

### feat/rct-digital-comms — RCT digital serial communication (DONE)
Real-device check on `/dev/ttyACM1` (STM32 VCP, VID:PID 0483:5740):
non-actuating `IN_NAME` returned `'RCT digital'`; reads of set
temperature (21 C), plate temperature (16 C) and set speed (200 rpm)
also succeeded, so the 10->20 setpoint fallback was not needed.
ruff clean; 20 pure unit tests pass.

Setpoint write reflection confirmed on the real device
(`claude_test/check_setpoints.py`): temperature 21->30->40 C and speed
200->300->500 rpm were written and read back exactly, then restored.
Setpoints only (no start_heater/start_motor), so nothing physically
heated or stirred.

## Learned Patterns

- `ika` (2.x) leaves pyserial `timeout` unset in
  `IKADevice.__init__` -> reads can block forever. Always set
  `device._ser.timeout` after construction.
- `ika` `MagneticStirrer.read_device_name()` compares the response
  against an un-stripped string (`response == 'RCT digital'`) while the
  base leaves a trailing `\r`, so on a real device it can fall through
  to `float(...)` and raise. Read the name via the raw response and
  strip it yourself.
