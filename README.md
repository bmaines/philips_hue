# 🏃 Philips Hue Motion Detector & Light Dashboard

A fast, zero-dependency local monitoring and control system for Philips Hue hardware. Provides real-time motion detection, ambient light (lux), temperature monitoring, battery health tracking, and interactive light power/brightness/color controls.

![Python 3](https://img.shields.io/badge/Python-3.8%2B-blue.svg)
![Dependencies](https://img.shields.io/badge/Dependencies-Zero%20(Standard%20Lib)-success.svg)
![Port](https://img.shields.io/badge/Web%20UI-http%3A%2F%2Flocalhost%3A8080-brightgreen.svg)
![License](https://img.shields.io/badge/License-MIT-purple.svg)

---

## ✨ Features

* 🏃 **Real-Time Motion Sensing:** Detects motion (`ZLLPresence` / `CLIPPresence`) with human-readable relative timestamps (*e.g., "12 seconds ago"*).
* 🔘 **Switch & Button Event Tracking:** Monitors Hue Dimmer Switch button presses (On, Off, Dim Up, Dim Down, Short & Long Press).
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

You can also monitor and control your Philips Hue system directly from the terminal using `hue_motion.py`:

```bash
# Display status of all motion sensors, switches, and lights
python3 hue_motion.py

# Live monitoring loop with motion & switch press alerts (polls every 1.0 second)
python3 hue_motion.py --monitor

# Output raw JSON data
python3 hue_motion.py --json

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
| **[hue_motion.py](file:///home/brandon/Documents/Philips_Hue/hue_motion.py)** | CLI motion & switch detector, live monitor loop, bridge pairing, and light color/brightness controller. |
| **[server.py](file:///home/brandon/Documents/Philips_Hue/server.py)** | Native Python HTTP server (`http.server`) serving REST endpoints & web UI on port `8080`. |
| **[index.html](file:///home/brandon/Documents/Philips_Hue/index.html)** | Glassmorphism dark-mode web dashboard UI with color pickers, preset pills, live switch/motion updates & audio alerts. |
| **[AGENTS.md](file:///home/brandon/Documents/Philips_Hue/AGENTS.md)** | AI Agent instructions and project guidelines. |
| **`.gemini/rules/`** | Google Antigravity project ruleset. |

---

## 🌐 Local REST API Endpoints

The `server.py` daemon exposes the following REST endpoints:

* **`GET /api/status`**: Returns JSON object containing bridge IP, connection status, sensors, switches, and lights with color Hex data.
* **`POST /api/pair`**: Initiates link button pairing handshake.
* **`POST /api/lights/<id>/state`**: Updates light state. Payload: `{"on": true/false, "brightness": 1..100, "hex": "#ff0000"}`.

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
