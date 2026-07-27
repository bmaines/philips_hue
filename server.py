#!/usr/bin/env python3
"""
Philips Hue Motion Sensor, Switch & Light Dashboard Server
------------------------------------------------------------
Provides a local web dashboard to monitor Hue motion sensors, switches/buttons, control lights,
and run customizable sequential light chasers & two-color smooth flow transitions in real time.
"""

import os
import sys
import json
import http.server
import socketserver
import urllib.request
import urllib.error
from hue_motion import (
    discover_bridge_ip, load_config, save_config,
    get_sensors_v1, get_lights_v1, parse_motion_sensors,
    parse_switches, parse_lights, set_light_state, pair_bridge,
    get_entertainment_areas, set_entertainment_stream,
    start_chaser_daemon, stop_chaser_daemon,
    start_color_flow_daemon, stop_color_flow_daemon, CONFIG_FILE
)

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))


class HueDashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path == "/api/status":
            self.send_json_response(self.get_hue_status())
        elif self.path == "/api/config":
            config = load_config()
            self.send_json_response({"config": config})
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/pair":
            config = load_config()
            ip = config.get("bridge_ip") or discover_bridge_ip()
            key = pair_bridge(ip, timeout=30)
            if key:
                config["bridge_ip"] = ip
                config["api_key"] = key
                save_config(config)
                self.send_json_response({"success": True, "api_key": key})
            else:
                self.send_json_response({"success": False, "error": "Pairing timed out. Press the link button and try again."})
        elif self.path == "/api/save_key":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
                config = load_config()
                if "ip" in data:
                    config["bridge_ip"] = data["ip"]
                if "key" in data:
                    config["api_key"] = data["key"]
                save_config(config)
                self.send_json_response({"success": True})
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)})
        elif self.path == "/api/entertainment/action":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
                group_id = data.get("id")
                action = data.get("action", "start")
                config = load_config()
                bridge_ip = config.get("bridge_ip") or "192.168.68.53"
                api_key = config.get("api_key")

                is_active = (action == "start")
                res = set_entertainment_stream(bridge_ip, api_key, group_id, active=is_active)
                self.send_json_response({"success": True, "action": action, "result": res})
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)})
        elif self.path == "/api/color_flow/start":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                payload = json.loads(body)
                light_ids = payload.get("light_ids", [])
                color_a = payload.get("color_a", "#ff0000")
                color_b = payload.get("color_b", "#0000ff")
                duration_sec = payload.get("duration_sec", 2.0)
                flow_bri = payload.get("flow_bri", 100)
                loops = payload.get("loops", 10)
                config = load_config()
                bridge_ip = config.get("bridge_ip") or "192.168.68.53"
                api_key = config.get("api_key")
                start_color_flow_daemon(
                    bridge_ip, api_key, light_ids,
                    color_a=color_a, color_b=color_b,
                    duration_sec=duration_sec, flow_bri=flow_bri, loops=loops
                )
                self.send_json_response({"success": True, "message": f"Color Flow started ({color_a} ↔ {color_b}, {duration_sec}s, bri: {flow_bri}%)"})
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)})
        elif self.path == "/api/color_flow/stop":
            stop_color_flow_daemon()
            self.send_json_response({"success": True, "message": "Color Flow stopped"})
        elif self.path == "/api/chaser/start":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                payload = json.loads(body)
                light_ids = payload.get("light_ids", [])
                duration_ms = payload.get("duration_ms")
                bpm = payload.get("bpm")
                loops = payload.get("loops", 10)
                flash_color = payload.get("flash_color", "#ffffff")
                flash_bri = payload.get("flash_bri", 100)
                idle_mode = payload.get("idle_mode", "restore")
                config = load_config()
                bridge_ip = config.get("bridge_ip") or "192.168.68.53"
                api_key = config.get("api_key")
                start_chaser_daemon(
                    bridge_ip, api_key, light_ids,
                    duration_ms=duration_ms, bpm=bpm, loops=loops,
                    flash_color=flash_color, flash_bri=flash_bri, idle_mode=idle_mode
                )
                dur_str = f"{duration_ms}ms" if duration_ms else f"{bpm} BPM"
                self.send_json_response({"success": True, "message": f"Chaser started ({dur_str}, {flash_color}, bri: {flash_bri}%, {idle_mode})"})
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)})
        elif self.path == "/api/chaser/stop":
            stop_chaser_daemon()
            self.send_json_response({"success": True, "message": "Chaser stopped"})
        elif self.path.startswith("/api/lights/"):
            parts = self.path.strip("/").split("/")
            if len(parts) >= 4 and parts[2] != "" and parts[3] == "state":
                light_id = parts[2]
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8')
                try:
                    payload = json.loads(body)
                    config = load_config()
                    bridge_ip = config.get("bridge_ip") or "192.168.68.53"
                    api_key = config.get("api_key")
                    on_state = payload.get("on", True)
                    bri = payload.get("brightness")
                    hex_color = payload.get("hex") or payload.get("color")
                    hue = payload.get("hue")
                    sat = payload.get("sat")
                    ct = payload.get("ct")
                    res = set_light_state(
                        bridge_ip, api_key, light_id,
                        on_state=on_state, brightness=bri,
                        hex_color=hex_color, hue=hue, sat=sat, ct=ct
                    )
                    self.send_json_response({"success": True, "result": res})
                except Exception as e:
                    self.send_json_response({"success": False, "error": str(e)})
            else:
                self.send_json_response({"error": "Invalid endpoint"}, 400)

    def send_json_response(self, data, code=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def get_hue_status(self):
        config = load_config()
        bridge_ip = config.get("bridge_ip") or "192.168.68.53"
        api_key = config.get("api_key")

        if not api_key:
            return {
                "paired": False,
                "bridge_ip": bridge_ip,
                "error": "Bridge not paired yet. Click Pair or enter API Key.",
                "sensors": [],
                "switches": [],
                "lights": [],
                "entertainment": []
            }

        sensors_data = get_sensors_v1(bridge_ip, api_key)
        lights_data = get_lights_v1(bridge_ip, api_key)
        entertainment = get_entertainment_areas(bridge_ip, api_key)

        if sensors_data is None and lights_data is None:
            return {
                "paired": False,
                "bridge_ip": bridge_ip,
                "error": "Could not connect to bridge or API key invalid.",
                "sensors": [],
                "switches": [],
                "lights": [],
                "entertainment": []
            }

        sensors = parse_motion_sensors(sensors_data)
        switches = parse_switches(sensors_data)
        lights = parse_lights(lights_data)

        return {
            "paired": True,
            "bridge_ip": bridge_ip,
            "sensors": sensors,
            "switches": switches,
            "lights": lights,
            "entertainment": entertainment,
            "server_time": os.popen("date").read().strip()
        }


def run_server(port=PORT):
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), HueDashboardHandler) as httpd:
        print(f"\n🌐 Hue Motion, Switch & Lights Web Dashboard running at: http://localhost:{port}")
        print("Press Ctrl+C to stop the server.\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped.")


if __name__ == "__main__":
    run_server()
