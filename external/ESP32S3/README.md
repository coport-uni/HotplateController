# ESP32-S3 client for the HotplateController server

An ESP-IDF firmware for the **ESP32-S3-BOX-3** that connects to the
HotplateController FastAPI server (see [`../../docs/server_api.md`](../../docs/server_api.md))
over WiFi, shows the hotplate's temperature and stirring speed on the
LCD, and drives the setpoints, heater, and motor from the touchscreen.

It is adapted from the SmartPlugController ESP-BOX-3 example: the WiFi
bring-up (`network.c`), the `esp_http_client` request/response pattern,
the LVGL display, and the on-board buttons follow the same structure.

## What it does

- Polls `GET /status` every `HOTPLATE_POLL_INTERVAL_S` seconds and shows:
  - plate temperature, stirring speed,
  - target temperature / target speed,
  - external probe and safety temperatures,
  - device connection state (online / offline) and reading age.
- Sends control commands via the touch buttons:
  - **Temp -/+**, **Spd -/+** — adjust the setpoints by the configured
    step (`POST /control/target/{temperature,speed}`),
  - **Heat**, **Stir** — toggle heater / motor
    (`POST /control/{heater,motor}/{start,stop}`).
- The two physical buttons (CONFIG / MUTE) mirror Temp +/- so the demo
  works without the touchscreen.

All HTTP runs on one background task, so requests never overlap. Touch
callbacks only enqueue a command; the task performs the request and then
refreshes the readings.

## Hardware

- **ESP32-S3-BOX-3** (320x240 LCD with capacitive touch, two buttons).
- The hotplate server reachable on the same WiFi network.

## Prerequisites

- [ESP-IDF](https://docs.espressif.com/projects/esp-idf/) **>= 5.3**
  installed and exported (`. $IDF_PATH/export.sh`).
- The managed components (`espressif/esp-box-3`, `espressif/cjson`) are
  pulled automatically by the component manager on first build.

## Configure

```bash
cd external/ESP32S3
idf.py set-target esp32s3
idf.py menuconfig    # -> "Hotplate monitor"
```

Set, under **Hotplate monitor**:

| Option | Meaning |
|--------|---------|
| `HOTPLATE_WIFI_SSID` / `HOTPLATE_WIFI_PASSWORD` | WiFi (WPA2-Personal). |
| `HOTPLATE_SERVER_URL` | Base URL of the server, e.g. `http://192.168.0.42:17048`. |
| `HOTPLATE_POLL_INTERVAL_S` | Status poll period (seconds). |
| `HOTPLATE_TEMP_STEP_C` | Step for the Temp -/+ buttons. |
| `HOTPLATE_SPEED_STEP_RPM` | Step for the Spd -/+ buttons. |

Leaving the SSID empty boots the UI in a "configure WiFi" state without
attempting to connect.

## Build, flash, monitor

```bash
idf.py build
idf.py -p /dev/ttyACM0 flash monitor   # use your board's port
```

On boot the screen shows `starting`, then `WiFi connecting...`, then the
live readings once the server responds. Press the buttons (touch or
physical) to drive the hotplate.

## Files

| File | Role |
|------|------|
| `main/main.c` | App entry: BSP/LVGL init, wiring, task startup. |
| `main/network.c/.h` | WiFi STA bring-up and connection state. |
| `main/hotplate_client.c/.h` | HTTP polling + control task, JSON parsing. |
| `main/ui.c/.h` | LVGL readings panel and control buttons. |
| `main/buttons_check.c/.h` | On-board CONFIG / MUTE button handling. |
| `main/Kconfig.projbuild` | `menuconfig` options. |
| `sdkconfig.defaults` | Board defaults (ESP32-S3, PSRAM, LVGL). |

## Notes

- The server exposes no heater/motor run-state readback, so the **Heat**
  and **Stir** buttons reflect the *intended* state (what was last sent),
  not a confirmed device state.
- Setpoints out of range are rejected by the server with HTTP 422; the
  client logs the status code and leaves its cached target unchanged.
- The endpoint contract this firmware depends on is documented in
  [`../../docs/server_api.md`](../../docs/server_api.md).
