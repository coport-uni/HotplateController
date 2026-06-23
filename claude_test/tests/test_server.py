"""Tests for the FastAPI monitoring/control server.

These run without hardware: a fake controller stands in for
``RctDigital`` and is injected onto the app, and the snapshot is filled
once with :meth:`DeviceMonitor.poll_once` so no background thread runs.
The ``TestClient`` is used without its context manager so the real
device-opening lifespan never executes.
"""

import pytest
from fastapi.testclient import TestClient

from hotplate_controller import server
from hotplate_controller.errors import RctCommError
from hotplate_controller.limits import validate_speed, validate_temperature


class FakeController:
    """In-memory stand-in for ``RctDigital`` that records control calls.

    The setters reuse the real range validators so out-of-range requests
    raise ``RctRangeError`` exactly as the device wrapper would.
    """

    def __init__(self):
        self.target_temperature = 25.0
        self.target_speed = 200.0
        self.heater_on = False
        self.motor_on = False
        self.calls = []

    def read_plate_temperature(self):
        return 24.5

    def read_probe_temperature(self):
        return 23.0

    def read_speed(self):
        return 0.0

    def read_target_temperature(self):
        return self.target_temperature

    def read_target_speed(self):
        return self.target_speed

    def read_safety_temperature(self):
        return 300.0

    def set_target_temperature(self, celsius):
        value = validate_temperature(celsius)
        self.target_temperature = value
        self.calls.append(("set_target_temperature", value))
        return value

    def set_target_speed(self, rpm):
        value = validate_speed(rpm)
        self.target_speed = value
        self.calls.append(("set_target_speed", value))
        return value

    def start_heater(self):
        self.heater_on = True
        self.calls.append(("start_heater",))

    def stop_heater(self):
        self.heater_on = False
        self.calls.append(("stop_heater",))

    def start_motor(self):
        self.motor_on = True
        self.calls.append(("start_motor",))

    def stop_motor(self):
        self.motor_on = False
        self.calls.append(("stop_motor",))

    def reset(self):
        self.calls.append(("reset",))


class FailingController(FakeController):
    """A controller whose reads always fail, as if disconnected."""

    def read_plate_temperature(self):
        raise RctCommError("no response; check wiring")


def _make_client(controller):
    """Build a TestClient with a pre-polled monitor over ``controller``."""
    monitor = server.DeviceMonitor(controller)
    monitor.poll_once()
    app = server.create_app()
    app.state.monitor = monitor
    return TestClient(app)


@pytest.fixture
def controller():
    return FakeController()


@pytest.fixture
def client(controller):
    return _make_client(controller)


def test_status_reports_connected_readings(client):
    body = client.get("/status").json()
    assert body["connected"] is True
    assert body["plate_temperature_c"] == 24.5
    assert body["probe_temperature_c"] == 23.0
    assert body["target_temperature_c"] == 25.0
    assert "age_seconds" in body


def test_health_reflects_connection(client):
    body = client.get("/health").json()
    assert body == {"status": "ok", "connected": True}


def test_temperature_endpoint_shape(client):
    body = client.get("/temperature").json()
    assert body["plate"] == 24.5
    assert body["target"] == 25.0
    assert body["unit"] == "C"


def test_speed_endpoint_shape(client):
    body = client.get("/speed").json()
    assert body["actual"] == 0.0
    assert body["target"] == 200.0
    assert body["unit"] == "rpm"


def test_set_temperature_updates_setpoint(client, controller):
    response = client.post("/control/target/temperature", json={"value": 60})
    assert response.status_code == 200
    assert response.json() == {"target": 60.0}
    assert controller.target_temperature == 60.0
    assert ("set_target_temperature", 60.0) in controller.calls


def test_set_temperature_out_of_range_is_422(client):
    response = client.post("/control/target/temperature", json={"value": 999})
    assert response.status_code == 422


def test_set_speed_out_of_range_is_422(client):
    response = client.post("/control/target/speed", json={"value": 99999})
    assert response.status_code == 422


def test_heater_endpoints_drive_controller(client, controller):
    assert client.post("/control/heater/start").json() == {"ok": True}
    assert controller.heater_on is True
    client.post("/control/heater/stop")
    assert controller.heater_on is False


def test_motor_endpoints_drive_controller(client, controller):
    client.post("/control/motor/start")
    assert controller.motor_on is True
    client.post("/control/motor/stop")
    assert controller.motor_on is False


def test_reset_endpoint_calls_controller(client, controller):
    assert client.post("/control/reset").json() == {"ok": True}
    assert ("reset",) in controller.calls


def test_dashboard_returns_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "RCT digital monitor" in response.text


def test_disconnected_device_stays_up():
    client = _make_client(FailingController())
    status = client.get("/status")
    assert status.status_code == 200
    assert status.json()["connected"] is False
    assert client.get("/health").json()["connected"] is False


def test_missing_monitor_returns_503():
    app = server.create_app()
    response = TestClient(app).get("/status")
    assert response.status_code == 503
