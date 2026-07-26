# Philips Hue Project Ruleset

## 1. Project Context & Overview
* **Workspace Location:** `/home/brandon/Documents/Philips_Hue`
* **Target Hardware:** Philips Hue Bridge (IP: `192.168.68.53`), Hue Motion Sensors (`ZLLPresence`), Temperature Sensors (`ZLLTemperature`), Ambient Light Sensors (`ZLLLightLevel`), Hue Switches (`ZLLSwitch`), and Hue Smart Lights.
* **Core Components:**
  * [hue_motion.py](file:///home/brandon/Documents/Philips_Hue/hue_motion.py): Primary CLI monitoring tool, bridge pairing logic, relative timestamp calculations, switch event parser, and light state mutation helper.
  * [server.py](file:///home/brandon/Documents/Philips_Hue/server.py): Zero-dependency HTTP server (`http.server`) running on port `8080` providing static file serving and JSON REST APIs (`/api/status`, `/api/pair`, `/api/lights/<id>/state`).
  * [index.html](file:///home/brandon/Documents/Philips_Hue/index.html): Modern, responsive dark-mode dashboard featuring live motion alerts, switch press badges, temperature/lux metrics, battery bars, audio alerts, and interactive light toggles/sliders.
  * [.hue_config.json](file:///home/brandon/Documents/Philips_Hue/.hue_config.json): Cached Hue Bridge IP and application key.

---

## 2. Mandatory Behavioral Rules & Conventions

### 🔒 GitHub Push & Upload Permission
* **CRITICAL RULE:** ALWAYS prompt the user for explicit permission before running `git push` or uploading code/commits to GitHub. Never push autonomously.

### 📦 Zero External Dependencies
* **Rule:** Maintain 100% Python Standard Library compatibility.
* Do NOT add required third-party dependencies (e.g. `pip install flask`, `requests`, `phue`, `aiohttp`).
* All networking must use `urllib.request` and all web serving must use `http.server` / `socketserver`.

### 🚀 Auto-Starting Web Server
* **Rule:** Always ensure `server.py` is running in the background on port `8080` during interactive development and monitoring sessions.
* If `server.py` is stopped or modified, automatically restart it using `python3 server.py` so **`http://localhost:8080`** remains continuously available.

### 🛡️ Bridge CPU & API Rate Limiting
* Do not issue requests to the Hue Bridge faster than **100ms** apart.
* Keep default frontend polling at **1.0 second** (`1000ms`) to prevent bridge CPU saturation.

### 🎨 UI Aesthetics & Interactions
* Maintain dark-mode glassmorphism styling in `index.html` with curated color tokens (`--accent-red`, `--accent-green`, `--accent-yellow`, `--accent-blue`, `--accent-cyan`).
* Ensure light toggling and brightness adjustments respond instantaneously with immediate UI updates.

### 💾 Backup Integrity
* Update `Philips_Hue_Backup.zip` when completing major feature additions or refactors.
