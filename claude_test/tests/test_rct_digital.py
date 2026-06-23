"""Pure unit tests for the RCT digital controller.

These exercise only the hardware-independent logic: range validation,
error-code description, and USB port matching. No serial device and no
``ika`` ``dummy`` instance are constructed.
"""

from types import SimpleNamespace

import pytest

from hotplate_controller import ports
from hotplate_controller.errors import RctRangeError, describe_error_code
from hotplate_controller.limits import (
    RCT_USB_PID,
    RCT_USB_VID,
    validate_speed,
    validate_temperature,
    validate_watchdog_time,
)


@pytest.mark.parametrize("celsius", [0, 25.5, 310])
def test_validate_temperature_accepts_in_range(celsius):
    assert validate_temperature(celsius) == float(celsius)


@pytest.mark.parametrize("celsius", [-1, 311, 1000])
def test_validate_temperature_rejects_out_of_range(celsius):
    with pytest.raises(RctRangeError):
        validate_temperature(celsius)


@pytest.mark.parametrize("rpm", [0, 50, 1500])
def test_validate_speed_accepts_in_range(rpm):
    assert validate_speed(rpm) == float(rpm)


@pytest.mark.parametrize("rpm", [-1, 1501])
def test_validate_speed_rejects_out_of_range(rpm):
    with pytest.raises(RctRangeError):
        validate_speed(rpm)


@pytest.mark.parametrize("seconds", [20, 750, 1500])
def test_validate_watchdog_accepts_in_range(seconds):
    assert validate_watchdog_time(seconds) == seconds


@pytest.mark.parametrize("seconds", [19, 1501])
def test_validate_watchdog_rejects_out_of_range(seconds):
    with pytest.raises(RctRangeError):
        validate_watchdog_time(seconds)


def test_describe_known_error_code_is_case_insensitive():
    assert "Watchdog" in describe_error_code("Er02")
    assert describe_error_code("er02") == describe_error_code("ER02")


def test_describe_unknown_error_code():
    assert "Unknown" in describe_error_code("Er99")


def _fake_port(vid, pid, device):
    return SimpleNamespace(vid=vid, pid=pid, device=device)


def test_find_rct_port_matches_vid_pid(monkeypatch):
    fake = [
        _fake_port(0x0403, 0x6001, "/dev/ttyUSB0"),
        _fake_port(RCT_USB_VID, RCT_USB_PID, "/dev/ttyACM1"),
    ]
    monkeypatch.setattr(ports.list_ports, "comports", lambda: fake)
    assert ports.find_rct_port() == "/dev/ttyACM1"


def test_find_rct_port_returns_none_when_absent(monkeypatch):
    fake = [_fake_port(0x0403, 0x6001, "/dev/ttyUSB0")]
    monkeypatch.setattr(ports.list_ports, "comports", lambda: fake)
    assert ports.find_rct_port() is None
