import json
import os
from pathlib import Path
from typing import Any, Optional

from langchain_core.tools import tool

_tuya_client: Any = None
_tuya_device_id: Optional[str] = None

_DEVICE_CONFIG_PATH = Path(__file__).resolve().parent.parent / ".device_config.json"


def _load_saved_device_id() -> Optional[str]:
    try:
        if _DEVICE_CONFIG_PATH.exists():
            data = json.loads(_DEVICE_CONFIG_PATH.read_text())
            return data.get("device_id")
    except Exception:
        pass
    return None


def save_device_id(device_id: str) -> None:
    global _tuya_device_id, _tuya_client
    _DEVICE_CONFIG_PATH.write_text(json.dumps({"device_id": device_id}))
    _tuya_device_id = device_id
    _tuya_client = None  # força reconexão com novo device_id


def _get_tuya_client() -> tuple[Any, Optional[str]]:
    global _tuya_client, _tuya_device_id
    if _tuya_client is not None:
        return _tuya_client, _tuya_device_id
    access_id = os.getenv("TUYA_ACCESS_ID")
    access_secret = os.getenv("TUYA_ACCESS_SECRET")
    device_id = _load_saved_device_id() or os.getenv("TUYA_DEVICE_ID")
    if not access_id or not access_secret:
        return None, None
    try:
        from tuya_connector import TuyaOpenAPI
        endpoint = os.getenv("TUYA_API_ENDPOINT", "https://openapi.tuyaus.com")
        openapi = TuyaOpenAPI(endpoint, access_id, access_secret)
        openapi.connect()
        _tuya_client = openapi
        _tuya_device_id = device_id
        return _tuya_client, _tuya_device_id
    except Exception:
        return None, None


def list_devices() -> list[dict]:
    """Lista todos os dispositivos vinculados ao projeto Tuya."""
    client, _ = _get_tuya_client()
    if client is None:
        return []
    try:
        resp = client.get("/v1.0/iot-03/devices", {"page_size": 50})
        if resp.get("success"):
            return resp.get("result", {}).get("devices", []) or []
    except Exception:
        pass
    return []


def _send_commands(commands: list[dict]) -> str:
    client, device_id = _get_tuya_client()
    if client is None or device_id is None:
        return "Tuya device not configured. Check TUYA_ACCESS_ID, TUYA_ACCESS_SECRET and TUYA_DEVICE_ID in .env."
    path = f"/v1.0/iot-03/devices/{device_id}/commands"
    payload = {"commands": commands}
    try:
        response = client.post(path, payload)
        if not response.get("success", False):
            return f"Command rejected by device: {response.get('msg', 'unknown error')}."
        return "ok"
    except Exception as e:
        return f"Failed to communicate with robot: {str(e)}."


def get_device_state() -> Optional[dict]:
    client, device_id = _get_tuya_client()
    if client is None or device_id is None:
        return None
    path = f"/v1.0/devices/{device_id}/status"
    try:
        response = client.get(path)
        if not response.get("success", False):
            return None
        result = response.get("result") or []
        status_by_code: dict[str, Any] = {}
        for item in result:
            code = item.get("code")
            if code is not None:
                status_by_code[code] = item.get("value")
        battery = None
        for key in ("battery_percentage", "bat_percentage", "bat_state", "residual_electricity"):
            if key in status_by_code:
                val = status_by_code[key]
                if isinstance(val, (int, float)):
                    battery = max(0, min(100, int(val)))
                    break
                if isinstance(val, str) and val.isdigit():
                    battery = max(0, min(100, int(val)))
                    break

        power_go = status_by_code.get("power_go")
        mode = status_by_code.get("mode", "")

        if mode == "chargego":
            status = "returning"
        elif power_go is True:
            status = "cleaning"
        else:
            status = "docked" if mode == "standby" else "idle"
        return {
            "status": status,
            "batteryLevel": battery if battery is not None else 0,
            "mode": mode or "standby",
            "totalCleanArea": status_by_code.get("total_clean_area", 0),
            "totalCleanTime": status_by_code.get("total_clean_time", 0),
            "cleanCount": status_by_code.get("clean_count", 0),
        }
    except Exception:
        return None


@tool
def start_cleaning() -> str:
    """Starts the vacuum robot cleaning. Use when the user asks to clean, vacuum, start, or begin cleaning."""
    result = _send_commands([{"code": "power_go", "value": True}])
    if result == "ok":
        return "Cleaning started."
    return result


@tool
def stop_cleaning() -> str:
    """Stops the robot cleaning. Use when the user asks to stop, pause, or interrupt."""
    result = _send_commands([{"code": "power_go", "value": False}])
    if result == "ok":
        return "Cleaning paused."
    return result


@tool
def return_to_base() -> str:
    """Sends the robot back to the charging base. Use when the user asks to return, go back to base, or dock."""
    result = _send_commands([{"code": "mode", "value": "chargego"}])
    if result == "ok":
        return "Robot returning to base."
    return result


@tool
def locate_robot() -> str:
    """Makes the robot emit a sound or signal for location. Use when the user asks to find, locate, or where is the robot."""
    result = _send_commands([{"code": "seek", "value": True}])
    if result == "ok":
        return "Locate command sent."
    return result


@tool
def set_clean_mode(mode: str) -> str:
    """Sets the cleaning mode. mode: one of 'smart', 'random', 'spiral', 'wall_follow', 'mop', 'left_bow', 'right_bow'. Use when the user asks to change the cleaning mode or pattern."""
    valid_modes = ("smart", "random", "spiral", "wall_follow", "mop", "left_bow", "right_bow", "left_spiral", "right_spiral", "partial_bow")
    mode = (mode or "").strip().lower()
    if mode not in valid_modes:
        return f"Invalid mode: use one of {', '.join(valid_modes)}."
    result = _send_commands([{"code": "mode", "value": mode}])
    if result == "ok":
        return f"Mode set to {mode}."
    return result
