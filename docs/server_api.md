# RCT digital monitoring server — HTTP API

A small FastAPI server that exposes the IKA RCT digital hotplate's
temperature and stirring speed over HTTP, and lets a client drive the
setpoints, heater, and motor. It is meant to be consumed by an ESP32 (or
any HTTP client) and also serves a self-refreshing web dashboard.

## Design in one paragraph

The device wrapper (`RctDigital`) talks to the hotplate over a blocking
serial port and handles one command at a time. The server runs a single
**background poller thread** that reads the device once per second and
stores the result in an in-memory snapshot. `GET` endpoints return that
cached snapshot, so they are fast and never block on the serial port.
`POST` control endpoints take the same lock the poller uses, so a write
never interleaves with a read. This means the readings you get are at
most ~1 second old (see `age_seconds` in `/status`).

## Running the server

```bash
pip install -e .
python3 -m hotplate_controller.server [PORT]
```

- `PORT` is the serial device path (e.g. `/dev/ttyACM1`). If omitted, the
  server auto-detects by USB VID:PID `0483:5740`, then falls back to the
  `$RCT_PORT` environment variable.
- The server listens on `0.0.0.0:17048`, so a device on the same network
  can reach it at `http://<server-ip>:17048`.
- Interactive API docs (Swagger UI) are at `/docs`; ReDoc is at `/redoc`.

Base URL used in the examples below: `http://localhost:17048`.

## Endpoints

### Monitoring (GET)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Self-refreshing HTML dashboard (for a browser). |
| GET | `/health` | Liveness and device connection state. |
| GET | `/status` | Full snapshot of all readings plus its age. |
| GET | `/temperature` | Plate, probe, and target temperatures (°C). |
| GET | `/speed` | Actual and target stirring speeds (rpm). |

`GET /status` response:

```json
{
  "connected": true,
  "plate_temperature_c": 24.5,
  "probe_temperature_c": 23.0,
  "speed_rpm": 0.0,
  "target_temperature_c": 25.0,
  "target_speed_rpm": 200.0,
  "safety_temperature_c": 300.0,
  "timestamp": "2026-06-23T09:05:26+00:00",
  "error": null,
  "age_seconds": 0.4
}
```

When the device is absent or unreadable, the server stays up and returns
`"connected": false`, all reading fields `null`, and a human-readable
`"error"` string. Always check `connected` before trusting a value.

`GET /temperature` response:

```json
{
  "plate": 24.5,
  "probe": 23.0,
  "target": 25.0,
  "unit": "C",
  "connected": true,
  "timestamp": "2026-06-23T09:05:26+00:00"
}
```

`GET /speed` response:

```json
{
  "actual": 0.0,
  "target": 200.0,
  "unit": "rpm",
  "connected": true,
  "timestamp": "2026-06-23T09:05:26+00:00"
}
```

### Control (POST)

| Method | Path | Body | Description |
|--------|------|------|-------------|
| POST | `/control/target/temperature` | `{"value": <°C>}` | Set the temperature setpoint (0–310 °C). |
| POST | `/control/target/speed` | `{"value": <rpm>}` | Set the stirring-speed setpoint (0–1500 rpm). |
| POST | `/control/heater/start` | — | Start heating toward the setpoint. |
| POST | `/control/heater/stop` | — | Stop heating. |
| POST | `/control/motor/start` | — | Start stirring toward the setpoint. |
| POST | `/control/motor/stop` | — | Stop stirring. |
| POST | `/control/reset` | — | Return the device to normal operating mode. |

Setting a setpoint does **not** start heating or stirring; call the
matching `start` endpoint explicitly. Setpoint endpoints return the
accepted value, e.g. `{"target": 60.0}`. Action endpoints return
`{"ok": true}`.

### Status codes

| Code | Meaning |
|------|---------|
| 200 | Success. |
| 422 | Setpoint out of range, or malformed request body. |
| 503 | The device monitor is not ready or the serial exchange failed. |

## curl examples

```bash
# Read everything
curl http://localhost:17048/status

# Just the temperatures
curl http://localhost:17048/temperature

# Set the temperature setpoint to 60 C
curl -X POST http://localhost:17048/control/target/temperature \
     -H 'Content-Type: application/json' -d '{"value": 60}'

# Start, then stop the heater
curl -X POST http://localhost:17048/control/heater/start
curl -X POST http://localhost:17048/control/heater/stop

# Out-of-range request -> 422
curl -i -X POST http://localhost:17048/control/target/temperature \
     -H 'Content-Type: application/json' -d '{"value": 999}'
```

## ESP32 example (Arduino `HTTPClient`)

Reading the status and setting a setpoint from an ESP32. Replace the
Wi-Fi credentials and the server IP with your own.

```cpp
#include <WiFi.h>
#include <HTTPClient.h>

const char* WIFI_SSID = "your-ssid";
const char* WIFI_PASS = "your-password";
const char* SERVER = "http://192.168.0.42:17048";  // server IP:port

void setup() {
  Serial.begin(115200);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nconnected");
}

// GET /status and print the raw JSON.
void readStatus() {
  HTTPClient http;
  http.begin(String(SERVER) + "/status");
  int code = http.GET();
  if (code == 200) {
    Serial.println(http.getString());
  } else {
    Serial.printf("GET /status failed: %d\n", code);
  }
  http.end();
}

// POST /control/target/temperature with a JSON body.
void setTemperature(float celsius) {
  HTTPClient http;
  http.begin(String(SERVER) + "/control/target/temperature");
  http.addHeader("Content-Type", "application/json");
  String body = String("{\"value\":") + celsius + "}";
  int code = http.POST(body);
  Serial.printf("set temp -> %d: %s\n", code, http.getString().c_str());
  http.end();
}

void loop() {
  readStatus();
  setTemperature(60.0);
  delay(2000);
}
```

To parse the JSON on the device, add the `ArduinoJson` library and
deserialize `http.getString()`; the flat keys above map directly to
`doc["plate_temperature_c"]`, `doc["speed_rpm"]`, and so on.
