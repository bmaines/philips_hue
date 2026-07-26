#!/usr/bin/env python3
"""
Philips Hue Motion Sensor Detector & Light Control
--------------------------------------------------
Detects motion sensors and lights on your Philips Hue Bridge,
reporting real-time motion status, light states, battery levels, temperature, and light levels.
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime, timezone
import urllib.request
import urllib.error

CONFIG_FILE = os.path.expanduser("~/Documents/Philips_Hue/.hue_config.json")


def discover_bridge_ip():
    """Discover Hue Bridge IP address via discovery service."""
    print("🔍 Discovering Philips Hue Bridge on local network...")
    try:
        req = urllib.request.Request(
            "https://discovery.meethue.com",
            headers={"User-Agent": "AntigravityHueSensor/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            bridges = json.loads(response.read().decode())
            if bridges and isinstance(bridges, list) and len(bridges) > 0:
                ip = bridges[0].get("internalipaddress")
                if ip:
                    print(f"✅ Found Philips Hue Bridge at IP: {ip}")
                    return ip
    except Exception as e:
        print(f"⚠️ Discovery API lookup failed ({e}).")

    fallback_ip = "192.168.68.53"
    print(f"ℹ️ Using bridge IP: {fallback_ip}")
    return fallback_ip


def load_config():
    """Load stored bridge configuration if present."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(config):
    """Save bridge configuration to file."""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        print(f"💾 Configuration saved to {CONFIG_FILE}")
    except Exception as e:
        print(f"⚠️ Could not save config: {e}")


def pair_bridge(bridge_ip, timeout=45):
    """Attempt to pair with the Hue Bridge by asking user to press the Link button."""
    url = f"http://{bridge_ip}/api"
    body = json.dumps({"devicetype": "antigravity_hue#motion_sensor"}).encode("utf-8")

    print("\n" + "=" * 60)
    print("🔘 BRIDGE PAIRING REQUIRED")
    print("Please press the large round LINK BUTTON on top of your")
    print(f"Philips Hue Bridge ({bridge_ip}) within {timeout} seconds.")
    print("=" * 60 + "\n")

    start_time = time.time()
    while time.time() - start_time < timeout:
        remaining = int(timeout - (time.time() - start_time))
        sys.stdout.write(f"\rWaiting for link button press... ({remaining}s remaining)  ")
        sys.stdout.flush()

        try:
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=3) as res:
                resp_json = json.loads(res.read().decode())
                if isinstance(resp_json, list) and len(resp_json) > 0:
                    item = resp_json[0]
                    if "success" in item:
                        username = item["success"]["username"]
                        print(f"\n\n🎉 Pairing successful! Created API key: {username}")
                        return username
                    elif "error" in item:
                        error_type = item["error"].get("type")
                        if error_type != 101:
                            print(f"\n⚠️ Unexpected pairing error: {item['error']}")
                            return None
        except Exception:
            pass

        time.sleep(2)

    print("\n❌ Pairing timed out. Link button was not pressed.")
    return None


def get_sensors_v1(bridge_ip, username):
    """Fetch all sensors data from Hue API v1."""
    url = f"http://{bridge_ip}/api/{username}/sensors"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as res:
            return json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            print("❌ Unauthorized: Invalid API key.")
        return None
    except Exception as e:
        print(f"❌ Error communicating with bridge: {e}")
        return None


def get_lights_v1(bridge_ip, username):
    """Fetch all lights data from Hue API v1."""
    url = f"http://{bridge_ip}/api/{username}/lights"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as res:
            return json.loads(res.read().decode())
    except Exception as e:
        print(f"❌ Error fetching lights: {e}")
        return None


def set_light_state(bridge_ip, username, light_id, on_state, brightness=None):
    """Turn light ON/OFF or change brightness via Hue API v1."""
    url = f"http://{bridge_ip}/api/{username}/lights/{light_id}/state"
    payload = {"on": bool(on_state)}
    if brightness is not None:
        # Scale 0-100% to 1-254
        bri_val = max(1, min(254, int((brightness / 100.0) * 254)))
        payload["bri"] = bri_val

    data = json.dumps(payload).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data, method="PUT", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as res:
            resp = json.loads(res.read().decode())
            return resp
    except Exception as e:
        print(f"❌ Error setting light state: {e}")
        return None


def parse_motion_sensors(sensors_data):
    """Filter and group motion sensors and associated temperature/light sensors."""
    if not sensors_data or not isinstance(sensors_data, dict):
        return []

    motion_sensors = []
    temp_sensors = {}
    light_sensors = {}

    for sid, sdata in sensors_data.items():
        stype = sdata.get("type", "")
        uid = sdata.get("uniqueid", "")
        mac_prefix = uid.split("-")[0] if "-" in uid else uid

        if stype in ("ZLLTemperature", "CLIPTemperature"):
            temp_sensors[mac_prefix] = sdata.get("state", {}).get("temperature")
        elif stype in ("ZLLLightLevel", "CLIPLightLevel"):
            light_sensors[mac_prefix] = sdata.get("state", {}).get("lightlevel")

    for sid, sdata in sensors_data.items():
        stype = sdata.get("type", "")
        if stype in ("ZLLPresence", "CLIPPresence"):
            uid = sdata.get("uniqueid", "")
            mac_prefix = uid.split("-")[0] if "-" in uid else uid

            state = sdata.get("state", {})
            config = sdata.get("config", {})

            presence = state.get("presence", False)
            last_updated = state.get("lastupdated", "none")
            battery = config.get("battery", "N/A")
            reachable = config.get("reachable", True)
            on_state = config.get("on", True)

            raw_temp = temp_sensors.get(mac_prefix)
            temp_c = (raw_temp / 100.0) if raw_temp is not None else None

            raw_light = light_sensors.get(mac_prefix)
            lux = round(10 ** ((raw_light - 1) / 10000.0), 1) if raw_light is not None and raw_light > 0 else None

            motion_sensors.append({
                "id": sid,
                "name": sdata.get("name", f"Motion Sensor {sid}"),
                "presence": presence,
                "last_updated": last_updated,
                "battery": battery,
                "reachable": reachable,
                "on": on_state,
                "temperature_c": temp_c,
                "lux": lux,
                "model": sdata.get("modelid", "Unknown"),
                "productname": sdata.get("productname", "Hue Motion Sensor")
            })

    return motion_sensors


def parse_lights(lights_data):
    """Parse lights into structured list."""
    if not lights_data or not isinstance(lights_data, dict):
        return []

    lights_list = []
    for lid, ldata in lights_data.items():
        state = ldata.get("state", {})
        on_state = state.get("on", False)
        bri = state.get("bri", 254)
        bri_pct = round((bri / 254.0) * 100) if bri is not None else 0
        reachable = state.get("reachable", True)

        lights_list.append({
            "id": lid,
            "name": ldata.get("name", f"Light {lid}"),
            "on": on_state,
            "brightness": bri_pct,
            "raw_bri": bri,
            "reachable": reachable,
            "type": ldata.get("type", "Light"),
            "model": ldata.get("modelid", "Unknown"),
            "productname": ldata.get("productname", "Hue Light")
        })
    return lights_list


def format_time_ago(utc_iso_str):
    """Format UTC ISO timestamp (e.g. 2026-07-25T18:00:00) as human readable elapsed time."""
    if not utc_iso_str or utc_iso_str == "none":
        return "Unknown"
    try:
        dt = datetime.strptime(utc_iso_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        diff_sec = int((now - dt).total_seconds())

        if diff_sec < 0:
            diff_sec = 0
        if diff_sec < 60:
            return f"{diff_sec} seconds ago"
        elif diff_sec < 3600:
            return f"{diff_sec // 60} min {diff_sec % 60} sec ago"
        else:
            hours = diff_sec // 3600
            mins = (diff_sec % 3600) // 60
            return f"{hours}h {mins}m ago"
    except Exception:
        return utc_iso_str


def print_sensor_status(sensors):
    """Pretty print status of motion sensors."""
    print("\n" + "=" * 65)
    print("🏃 PHILIPS HUE MOTION SENSOR STATUS")
    print("=" * 65)

    if not sensors:
        print("⚠️ No Motion Sensors (ZLLPresence / CLIPPresence) found on this Hue Bridge.")
        print("=" * 65 + "\n")
        return

    for s in sensors:
        status_icon = "🚨 MOTION DETECTED!" if s["presence"] else "🟢 No Motion"
        status_str = f"\033[1;31m{status_icon}\033[0m" if s["presence"] else f"\033[1;32m{status_icon}\033[0m"
        last_seen = format_time_ago(s["last_updated"])

        print(f"\n📡 Sensor: \033[1m{s['name']}\033[0m (ID: {s['id']} | Model: {s['model']})")
        print(f"   Status:        {status_str}")
        print(f"   Last Motion:   {s['last_updated']} UTC ({last_seen})")
        print(f"   Battery:       {s['battery']}%" if isinstance(s['battery'], int) else f"   Battery:       {s['battery']}")
        if s['temperature_c'] is not None:
            temp_f = (s['temperature_c'] * 9/5) + 32
            print(f"   Temperature:   {s['temperature_c']:.1f}°C ({temp_f:.1f}°F)")
        if s['lux'] is not None:
            print(f"   Light Level:   {s['lux']} lux")
        print(f"   Reachable:     {'Yes' if s['reachable'] else '❌ Offline'}")
        print(f"   Sensor Active: {'Yes' if s['on'] else 'Disabled'}")

    print("\n" + "=" * 65 + "\n")


def print_lights_status(lights):
    """Pretty print status of Hue lights."""
    print("\n" + "=" * 65)
    print("💡 PHILIPS HUE LIGHTS STATUS")
    print("=" * 65)

    if not lights:
        print("⚠️ No Lights found on this Hue Bridge.")
        print("=" * 65 + "\n")
        return

    for l in lights:
        status_icon = "💡 ON " if l["on"] else "🌑 OFF"
        status_str = f"\033[1;33m{status_icon}\033[0m" if l["on"] else f"\033[1;30m{status_icon}\033[0m"

        print(f"\n💡 Light: \033[1m{l['name']}\033[0m (ID: {l['id']} | Model: {l['model']})")
        print(f"   State:      {status_str}")
        print(f"   Brightness: {l['brightness']}%")
        print(f"   Reachable:  {'Yes' if l['reachable'] else '❌ Offline'}")

    print("\n" + "=" * 65 + "\n")


def live_monitor(bridge_ip, username, interval=1.0):
    """Continuously monitor motion sensors and log events live."""
    print(f"\n📡 Starting Live Motion Monitor (Polling every {interval}s). Press Ctrl+C to stop.\n")
    print(f"{'TIME':<12} | {'SENSOR NAME':<22} | {'MOTION STATE':<18} | {'LAST DETECTED'}")
    print("-" * 75)

    last_states = {}

    try:
        while True:
            sensors_data = get_sensors_v1(bridge_ip, username)
            sensors = parse_motion_sensors(sensors_data)

            now_str = datetime.now().strftime("%H:%M:%S")

            for s in sensors:
                sid = s["id"]
                prev_presence = last_states.get(sid)
                curr_presence = s["presence"]
                last_seen = format_time_ago(s["last_updated"])

                if prev_presence is None or curr_presence != prev_presence:
                    if curr_presence:
                        state_str = "\033[1;41;37m 🚨 MOTION! \033[0m"
                        sys.stdout.write("\a")
                    else:
                        state_str = "\033[1;32m 🟢 Clear    \033[0m"

                    print(f"{now_str:<12} | {s['name']:<22} | {state_str:<27} | {last_seen}")
                    last_states[sid] = curr_presence

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\n🛑 Live monitoring stopped.")


def main():
    parser = argparse.ArgumentParser(description="Philips Hue Motion Sensor & Light Control")
    parser.add_argument("--ip", help="Philips Hue Bridge IP address")
    parser.add_argument("--key", help="Philips Hue API Username/Key")
    parser.add_argument("--monitor", "-m", action="store_true", help="Run live motion monitoring loop")
    parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds (default: 1.0)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON data")
    parser.add_argument("--pair", action="store_true", help="Force re-pairing with Hue Bridge")
    parser.add_argument("--toggle-light", help="Light ID to toggle state (on/off)")
    parser.add_argument("--bri", type=int, help="Set brightness (0-100%%) for light")

    args = parser.parse_args()

    config = load_config()

    bridge_ip = args.ip or config.get("bridge_ip") or discover_bridge_ip()
    api_key = args.key or config.get("api_key")

    if not api_key or args.pair:
        api_key = pair_bridge(bridge_ip)
        if not api_key:
            sys.exit(1)

    config["bridge_ip"] = bridge_ip
    config["api_key"] = api_key
    save_config(config)

    # Toggle light command
    if args.toggle_light:
        lights_data = get_lights_v1(bridge_ip, api_key)
        parsed_lights = parse_lights(lights_data)
        target = next((l for l in parsed_lights if str(l["id"]) == str(args.toggle_light)), None)
        if target:
            new_state = not target["on"]
            print(f"Toggling light {target['name']} (ID {args.toggle_light}) -> {'ON' if new_state else 'OFF'}")
            set_light_state(bridge_ip, api_key, args.toggle_light, new_state, args.bri)
        else:
            print(f"Light ID {args.toggle_light} not found.")
        return

    sensors_data = get_sensors_v1(bridge_ip, api_key)
    lights_data = get_lights_v1(bridge_ip, api_key)

    if sensors_data is None:
        print("⚠️ Failed to retrieve sensors. Attempting re-pairing...")
        api_key = pair_bridge(bridge_ip)
        if api_key:
            config["api_key"] = api_key
            save_config(config)
            sensors_data = get_sensors_v1(bridge_ip, api_key)
            lights_data = get_lights_v1(bridge_ip, api_key)

    if sensors_data is None and lights_data is None:
        print("❌ Could not communicate with Hue Bridge.")
        sys.exit(1)

    motion_sensors = parse_motion_sensors(sensors_data)
    lights = parse_lights(lights_data)

    if args.json:
        print(json.dumps({"sensors": motion_sensors, "lights": lights}, indent=2))
        return

    if args.monitor:
        live_monitor(bridge_ip, api_key, interval=args.interval)
    else:
        print_sensor_status(motion_sensors)
        print_lights_status(lights)


if __name__ == "__main__":
    main()
