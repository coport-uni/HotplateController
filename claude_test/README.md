# claude_test

Scratch / diagnostic scripts (per CLAUDE.md Section 3). Not part of CI.

| File | Purpose | Notes |
|------|---------|-------|
| `verify_device.py` | Verify serial comms with a real RCT digital: non-actuating `IN_NAME` identity query, with a temperature-setpoint 10 C -> 20 C round-trip (no heating) as a fallback. | Run: `python3 claude_test/verify_device.py [PORT]`. Port auto-detects by USB VID:PID `0483:5740`, then `$RCT_PORT`. Confirmed: returns `'RCT digital'`. |
| `check_setpoints.py` | Confirm a written setpoint is actually reflected: writes distinct temperature and speed setpoints, reads them back, restores originals. Setpoints only (no heating/stirring). | Run: `python3 claude_test/check_setpoints.py [PORT]`. Confirmed: temp 21->30->40, speed 200->300->500 read back exactly. |
