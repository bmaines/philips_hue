# Project Instructions & Agent Guidelines

## 1. Project Context
This codebase provides real-time motion detection, environmental sensing, and light control for local Philips Hue hardware on the home network.

* **Bridge IP:** `192.168.68.53`
* **Port:** `8080` (Web UI at `http://localhost:8080`)
* **Key Files:**
  * `hue_motion.py`: CLI motion detection, bridge pairing, and light controller script.
  * `server.py`: Native Python HTTP server providing REST endpoints.
  * `index.html`: Responsive dark-mode dashboard UI.
  * `.hue_config.json`: Local credentials storage.

## 2. Core Rules for AI Agents
1. **Zero External Dependencies:** Only use Python standard library packages (`urllib`, `json`, `http.server`). Do NOT add `pip` dependencies.
2. **Auto-Start Dashboard:** Keep `server.py` running on port `8080` whenever working on or testing the project.
3. **Bridge Polling Safety:** Do not poll the Hue Bridge faster than 100ms. Keep default polling at 1.0s.
4. **UI Quality:** Maintain modern dark-mode glassmorphism aesthetics in `index.html`.
