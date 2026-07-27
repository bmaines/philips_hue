#!/usr/bin/env python3
"""
Philips Hue Motion Sensor, Light & Switch Control
--------------------------------------------------
Detects motion sensors, switches, and lights on your Philips Hue Bridge,
reporting real-time motion status, button presses, light states, color, battery levels, temperature, and lux.
"""

import os
import sys
import time
import json
import argparse
import colorsys
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


def hex_to_hue_sat_bri(hex_str):
    """Convert Hex RGB string (e.g. #FF0000) to Hue (0-65535), Saturation (0-254), and Brightness (1-254)."""
    hex_str = hex_str.lstrip("#")
    if len(hex_str) != 6:
        return 0, 254, 254

    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0

    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    hue_val = int(h * 65535)
    sat_val = int(s * 254)
    bri_val = max(1, int(v * 254))
    return hue_val, sat_val, bri_val


def hue_sat_to_hex(hue_val, sat_val, bri_val=254):
    """Convert Hue (0-65535), Saturation (0-254), Brightness (1-254) to Hex RGB string."""
    h = (hue_val % 65536) / 65535.0
    s = (sat_val % 255) / 254.0
    v = (bri_val % 255) / 254.0

    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def set_light_state(bridge_ip, username, light_id, on_state=True, brightness=None, hex_color=None, hue=None, sat=None, ct=None):
    """Turn light ON/OFF, change brightness, or set color via Hue API v1."""
    url = f"http://{bridge_ip}/api/{username}/lights/{light_id}/state"
    payload = {"on": bool(on_state)}

    if hex_color is not None:
        h_val, s_val, v_val = hex_to_hue_sat_bri(hex_color)
        payload["hue"] = h_val
        payload["sat"] = s_val
        if brightness is None:
            payload["bri"] = v_val

    if hue is not None:
        payload["hue"] = max(0, min(65535, int(hue)))
    if sat is not None:
        payload["sat"] = max(0, min(254, int(sat)))
    if ct is not None:
        payload["ct"] = max(154, min(500, int(ct)))

    if brightness is not None:
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


def format_button_event(event_code):
    """Map Hue button event code to human-readable description."""
    if event_code is None:
        return "No button presses yet"

    code = int(event_code)

    button_names = {
        1: "On Button",
        2: "Dim Up Button",
        3: "Dim Down Button",
        4: "Off Button"
    }

    action_names = {
        0: "Pressed",
        1: "Held",
        2: "Released (Short Press)",
        3: "Released (Long Press)"
    }

    button_id = code // 1000
    action_id = code % 1000

    b_name = button_names.get(button_id, f"Button {button_id}")
    a_name = action_names.get(action_id, f"Action {action_id}")

    return f"{b_name} - {a_name}"


def parse_switches(sensors_data):
    """Filter and parse Hue switch / dimmer button sensors."""
    if not sensors_data or not isinstance(sensors_data, dict):
        return []

    switches = []
    for sid, sdata in sensors_data.items():
        stype = sdata.get("type", "")
        if stype in ("ZLLSwitch", "ZTPSwitch", "CLIPSwitch"):
            state = sdata.get("state", {})
            config = sdata.get("config", {})

            buttonevent = state.get("buttonevent")
            last_updated = state.get("lastupdated", "none")
            battery = config.get("battery", "N/A")
            reachable = config.get("reachable", True)

            switches.append({
                "id": sid,
                "name": sdata.get("name", f"Switch {sid}"),
                "type": stype,
                "model": sdata.get("modelid", "Unknown"),
                "productname": sdata.get("productname", "Hue Switch"),
                "buttonevent": buttonevent,
                "button_desc": format_button_event(buttonevent),
                "last_updated": last_updated,
                "battery": battery,
                "reachable": reachable
            })

    return switches


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
    """Parse lights into structured list with color data."""
    if not lights_data or not isinstance(lights_data, dict):
        return []

    lights_list = []
    for lid, ldata in lights_data.items():
        state = ldata.get("state", {})
        on_state = state.get("on", False)
        bri = state.get("bri", 254)
        bri_pct = round((bri / 254.0) * 100) if bri is not None else 0
        reachable = state.get("reachable", True)

        hue_val = state.get("hue")
        sat_val = state.get("sat")
        ct_val = state.get("ct")
        colormode = state.get("colormode", "ct")

        # Convert Hue/Sat to Hex color string for UI representation
        if hue_val is not None and sat_val is not None:
            hex_color = hue_sat_to_hex(hue_val, sat_val, bri if bri else 254)
        else:
            hex_color = "#ffcc00"

        lights_list.append({
            "id": lid,
            "name": ldata.get("name", f"Light {lid}"),
            "on": on_state,
            "brightness": bri_pct,
            "raw_bri": bri,
            "hue": hue_val,
            "sat": sat_val,
            "ct": ct_val,
            "colormode": colormode,
            "hex_color": hex_color,
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


def print_switches_status(switches):
    """Pretty print status of Hue switches."""
    print("\n" + "=" * 65)
    print("🔘 PHILIPS HUE SWITCH & BUTTON STATUS")
    print("=" * 65)

    if not switches:
        print("⚠️ No Switches (ZLLSwitch / ZTPSwitch) found on this Hue Bridge.")
        print("=" * 65 + "\n")
        return

    for sw in switches:
        last_seen = format_time_ago(sw["last_updated"])
        print(f"\n🔘 Switch: \033[1m{sw['name']}\033[0m (ID: {sw['id']} | Model: {sw['model']})")
        print(f"   Last Action:   \033[1;36m{sw['button_desc']}\033[0m (Code: {sw['buttonevent']})")
        print(f"   Pressed At:    {sw['last_updated']} UTC ({last_seen})")
        print(f"   Battery:       {sw['battery']}%" if isinstance(sw['battery'], int) else f"   Battery:       {sw['battery']}")
        print(f"   Reachable:     {'Yes' if sw['reachable'] else '❌ Offline'}")

    print("\n" + "=" * 65 + "\n")


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
        print(f"   Color Hex:  {l['hex_color']}")
        print(f"   Reachable:  {'Yes' if l['reachable'] else '❌ Offline'}")

    print("\n" + "=" * 65 + "\n")


def live_monitor(bridge_ip, username, interval=1.0):
    """Continuously monitor motion sensors & switch button presses live."""
    print(f"\n📡 Starting Live Monitor for Motion & Switches (Polling every {interval}s). Press Ctrl+C to stop.\n")
    print(f"{'TIME':<12} | {'DEVICE NAME':<22} | {'EVENT / STATE':<28} | {'LAST UPDATED'}")
    print("-" * 80)

    last_motion_states = {}
    last_switch_events = {}

    try:
        while True:
            sensors_data = get_sensors_v1(bridge_ip, username)
            sensors = parse_motion_sensors(sensors_data)
            switches = parse_switches(sensors_data)

            now_str = datetime.now().strftime("%H:%M:%S")

            for s in sensors:
                sid = s["id"]
                prev_presence = last_motion_states.get(sid)
                curr_presence = s["presence"]
                last_seen = format_time_ago(s["last_updated"])

                if prev_presence is None or curr_presence != prev_presence:
                    if curr_presence:
                        state_str = "\033[1;41;37m 🚨 MOTION! \033[0m"
                        sys.stdout.write("\a")
                    else:
                        state_str = "\033[1;32m 🟢 Clear    \033[0m"

                    print(f"{now_str:<12} | {s['name']:<22} | {state_str:<37} | {last_seen}")
                    last_motion_states[sid] = curr_presence

            for sw in switches:
                sw_id = sw["id"]
                prev_time = last_switch_events.get(sw_id)
                curr_time = sw["last_updated"]

                if prev_time is not None and curr_time != prev_time and curr_time != "none":
                    btn_desc = sw["button_desc"]
                    event_str = f"\033[1;43;30m 🔘 {btn_desc} \033[0m"
                    sys.stdout.write("\a")
                    print(f"{now_str:<12} | {sw['name']:<22} | {event_str:<37} | {format_time_ago(curr_time)}")
                
                last_switch_events[sw_id] = curr_time

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\n🛑 Live monitoring stopped.")


def main():
    parser = argparse.ArgumentParser(description="Philips Hue Motion Sensor, Switch & Light Control")
    parser.add_argument("--ip", help="Philips Hue Bridge IP address")
    parser.add_argument("--key", help="Philips Hue API Username/Key")
    parser.add_argument("--monitor", "-m", action="store_true", help="Run live motion & switch monitoring loop")
    parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds (default: 1.0)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON data")
    parser.add_argument("--pair", action="store_true", help="Force re-pairing with Hue Bridge")
    parser.add_argument("--toggle-light", help="Light ID to toggle state (on/off)")
    parser.add_argument("--bri", type=int, help="Set brightness (0-100%%) for light")
    parser.add_argument("--color", help="Set light color via hex string (e.g., '#FF0000')")
    parser.add_argument("--hue", type=int, help="Set hue value (0-65535)")
    parser.add_argument("--sat", type=int, help="Set saturation value (0-254)")
    parser.add_argument("--ct", type=int, help="Set color temperature (154-500 mireds)")

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

    if args.toggle_light:
        lights_data = get_lights_v1(bridge_ip, api_key)
        parsed_lights = parse_lights(lights_data)
        target = next((l for l in parsed_lights if str(l["id"]) == str(args.toggle_light)), None)
        if target:
            new_state = not target["on"] if (args.color is None and args.hue is None and args.bri is None) else True
            print(f"Setting light {target['name']} (ID {args.toggle_light}) -> {'ON' if new_state else 'OFF'}")
            set_light_state(
                bridge_ip, api_key, args.toggle_light,
                on_state=new_state, brightness=args.bri,
                hex_color=args.color, hue=args.hue, sat=args.sat, ct=args.ct
            )
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
    switches = parse_switches(sensors_data)
    lights = parse_lights(lights_data)

    if args.json:
        print(json.dumps({"sensors": motion_sensors, "switches": switches, "lights": lights}, indent=2))
        return

    if args.monitor:
        live_monitor(bridge_ip, api_key, interval=args.interval)
    else:
        print_sensor_status(motion_sensors)
        print_switches_status(switches)
        print_lights_status(lights)


if __name__ == "__main__":
    main()
