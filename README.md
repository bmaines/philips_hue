# 🏃 Philips Hue Motion Detector, Light & Color Flow Dashboard

A fast, zero-dependency local monitoring and control system for Philips Hue hardware. Provides real-time motion detection, ambient light (lux), temperature monitoring, battery health tracking, interactive light power/brightness/color controls, a customizable sequential light chaser engine, and a smooth two-color flow transition engine.

![Python 3](https://img.shields.io/badge/Python-3.8%2B-blue.svg)
![Dependencies](https://img.shields.io/badge/Dependencies-Zero%20(Standard%20Lib)-success.svg)
![Port](https://img.shields.io/badge/Web%20UI-http%3A%2F%2Flocalhost%3A8080-brightgreen.svg)
![License](https://img.shields.io/badge/License-MIT-purple.svg)

---

## ✨ Features

* 🏃 **Real-Time Motion Sensing:** Detects motion (`ZLLPresence` / `CLIPPresence`) with human-readable relative timestamps (*e.g., "12 seconds ago"*).
* 🔘 **Switch & Button Event Tracking:** Monitors Hue Dimmer Switch button presses (On, Off, Dim Up, Dim Down, Short & Long Press).
* 🌈 **Smooth Two-Color Flow Transition Engine:** Hardware-level smooth color fading alternating between Color A and Color B over customizable transition durations (`0.5s`–`60s`) and flow brightness (`1%`–`100%`).
* ⚡ **Sequential Light Chaser Engine:** High-speed sequential light animations with custom flash durations (ms), flash brightness (`1%`–`100%`), custom flash colors (Hex or preset pills), and pre-sequence color state preservation.
* 🔀 **Re-orderable Light Sequences & Bulk Selection:** Interactively reorder light sequence execution (⬆️ Up / ⬇️ Down) and quickly **Select All** / **Deselect All** lights in both effect panels.
* 🎨 **Full Light Color & Brightness Control:** Change light colors using preset pills or an interactive HTML color picker (`<input type="color">`), with automatic RGB-to-Hue/Sat conversion via standard library `colorsys`.
* 💡 **Interactive Light Power Control:** Toggle power state and adjust brightness (0–100%) from Web UI or CLI.
* 🌡️ **Environmental Metrics:** Monitors temperature (°C and °F) and ambient light levels (Lux) reported by Hue Motion Sensors.
* 🔋 **Battery Health Monitoring:** Displays remaining battery percentage for all wireless sensors and switches.
* 🔊 **Audio Alerts:** Web Audio API chime option whenever motion or switch presses are detected.
* ⚡ **Zero External Dependencies:** Built entirely with Python's standard library (`urllib.request`, `http.server`, `json`, `colorsys`). No `pip install` required!
* 🎨 **Dark Mode Glassmorphic UI:** Modern 60 FPS animated web dashboard.

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/bmaines/philips_hue.git
cd philips_hue
```

### 2. Start the Web Dashboard
```bash
python3 server.py
```
Open **[http://localhost:8080](http://localhost:8080)** in your web browser.

---

## 💻 Command Line (CLI) Usage

You can monitor and control your Philips Hue system directly from the terminal using `hue_motion.py`:

```bash
# Display status of all motion sensors, switches, and lights
python3 hue_motion.py

# Live monitoring loop with motion & switch press alerts (polls every 1.0 second)
python3 hue_motion.py --monitor

# Smoothly transition Light IDs 1 & 2 between Red (#ff0000) and Blue (#0000ff) every 2.0s at 75% brightness
python3 hue_motion.py --color-flow "1,2" --color-a "#ff0000" --color-b "#0000ff" --flow-duration 2.0 --flow-bri 75 --loops 10

# Run Light Chaser sequence on Light IDs 1, 2, 3 with custom flash duration (500ms) and 50% flash brightness
python3 hue_motion.py --chaser "1,2,3" --duration-ms 500 --flash-bri 50 --loops 5

# Run Light Chaser with custom flash color (Red) and keep previous colors between flashes
python3 hue_motion.py --chaser "1,2,3" --duration-ms 200 --flash-color "#ff0000" --idle-mode restore

# Toggle a light by ID (e.g. Light ID 1)
python3 hue_motion.py --toggle-light 1

# Set light brightness (0–100%)
python3 hue_motion.py --toggle-light 1 --bri 75

# Set light color by Hex string (e.g. Red, Blue, Green, Cyan)
python3 hue_motion.py --toggle-light 1 --color "#ff0000"
python3 hue_motion.py --toggle-light 1 --color "#0a84ff"

# Specify custom bridge IP or force re-pairing
python3 hue_motion.py --ip 192.168.68.53 --pair
```

---

## 🔘 One-Time Bridge Pairing

1. When running for the first time, the tool automatically discovers your Hue Bridge on the local network (via N-UPnP at `discovery.meethue.com`).
2. If pairing is required, press the **large round Link Button** on top of your physical Philips Hue Bridge.
3. The app will generate an API key and save it locally in `.hue_config.json`.

---

## 📂 Project Structure

| File | Description |
| :--- | :--- |
| **[hue_motion.py](file:///home/brandon/Documents/Philips_Hue/hue_motion.py)** | CLI motion & switch detector, live monitor loop, bridge pairing, light chaser engine, two-color smooth flow engine, and color/brightness controller. |
| **[server.py](file:///home/brandon/Documents/Philips_Hue/server.py)** | Native Python HTTP server (`http.server`) serving REST endpoints, chaser & color flow daemons & web UI on port `8080`. |
| **[index.html](file:///home/brandon/Documents/Philips_Hue/index.html)** | Glassmorphism dark-mode web dashboard UI with smooth color flow panel, re-orderable light chaser, Select All / Deselect All controls, color pickers, preset pills, live switch/motion updates & audio alerts. |
| **[AGENTS.md](file:///home/brandon/Documents/Philips_Hue/AGENTS.md)** | AI Agent instructions and project guidelines. |
| **`.gemini/rules/`** | Google Antigravity project ruleset. |

---

## 🌐 Local REST API Endpoints

The `server.py` daemon exposes the following REST endpoints:

* **`GET /api/status`**: Returns JSON object containing bridge IP, connection status, sensors, switches, and lights with color Hex data.
* **`POST /api/pair`**: Initiates link button pairing handshake.
* **`POST /api/color_flow/start`**: Starts smooth two-color flow daemon. Payload: `{"light_ids": ["1", "2"], "color_a": "#ff0000", "color_b": "#0000ff", "duration_sec": 2.0, "flow_bri": 100, "loops": 10}`.
* **`POST /api/color_flow/stop`**: Stops active color flow daemon.
* **`POST /api/chaser/start`**: Starts light chaser sequence daemon. Payload: `{"light_ids": ["1", "2"], "duration_ms": 235, "flash_color": "#ffffff", "flash_bri": 100, "idle_mode": "restore", "loops": 10}`.
* **`POST /api/chaser/stop`**: Stops active light chaser sequence daemon.
* **`POST /api/lights/<id>/state`**: Updates light state. Payload: `{"on": true/false, "brightness": 1..100, "hex": "#ff0000"}`.

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
