import os
from typing import Any, Optional

from langchain_core.tools import tool

_tuya_client: Any = None
_tuya_device_id: Optional[str] = None


def _get_tuya_client() -> tuple[Any, Optional[str]]:
    global _tuya_client, _tuya_device_id
    if _tuya_client is not None:
        return _tuya_client, _tuya_device_id
    access_id = os.getenv("TUYA_ACCESS_ID")
    access_secret = os.getenv("TUYA_ACCESS_SECRET")
    device_id = os.getenv("TUYA_DEVICE_ID")
    if not access_id or not access_secret or not device_id:
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


def _send_commands(commands: list[dict]) -> str:
    client, device_id = _get_tuya_client()
    if client is None or device_id is None:
        return "Dispositivo Tuya não configurado. Verifique TUYA_ACCESS_ID, TUYA_ACCESS_SECRET e TUYA_DEVICE_ID no .env."
    path = f"/v1.0/iot-03/devices/{device_id}/commands"
    payload = {"commands": commands}
    try:
        response = client.post(path, payload)
        if not response.get("success", True):
            return f"Comando recusado pelo dispositivo: {response.get('msg', 'erro desconhecido')}."
        return "ok"
    except Exception as e:
        return f"Falha ao comunicar com o robô: {str(e)}."


def get_device_state() -> Optional[dict]:
    client, device_id = _get_tuya_client()
    if client is None or device_id is None:
        return None
    path = f"/v1.0/devices/{device_id}/status"
    try:
        response = client.get(path)
        if not response.get("success", True):
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
        switch_go = status_by_code.get("switch_go")
        charge_state = status_by_code.get("charge_state")
        work_state = status_by_code.get("work_state")
        if isinstance(charge_state, str) and "charging" in charge_state.lower():
            status = "docked"
        elif switch_go is True:
            status = "cleaning"
        elif work_state is not None:
            ws = str(work_state).lower()
            if "charging" in ws or "charge" in ws or "dock" in ws:
                status = "docked"
            elif "cleaning" in ws or "sweep" in ws or "go" in ws:
                status = "cleaning"
            elif "return" in ws or "back" in ws:
                status = "returning"
            else:
                status = "idle"
        elif switch_go is False and (charge_state is None or charge_state is False):
            status = "idle"
        else:
            status = "docked" if charge_state else "idle"
        return {
            "status": status,
            "batteryLevel": battery if battery is not None else 0,
        }
    except Exception:
        return None


@tool
def start_cleaning() -> str:
    """Inicia a limpeza do robô aspirador. Use quando o usuário pedir para limpar, aspirar, começar, iniciar limpeza."""
    result = _send_commands([{"code": "switch_go", "value": True}])
    if result == "ok":
        return "Limpeza iniciada."
    return result


@tool
def stop_cleaning() -> str:
    """Para a limpeza do robô. Use quando o usuário pedir para parar, pausar, interromper."""
    result = _send_commands([{"code": "switch_go", "value": False}])
    if result == "ok":
        return "Limpeza pausada."
    return result


@tool
def return_to_base() -> str:
    """Envia o robô de volta para a base de carregamento. Use quando o usuário pedir para voltar, retornar à base, encostar, carregar."""
    result = _send_commands([{"code": "switch_charge", "value": True}])
    if result == "ok":
        return "Robô retornando à base."
    return result


@tool
def locate_robot() -> str:
    """Faz o robô emitir um som ou sinal para localização. Use quando o usuário pedir para encontrar, localizar, onde está o robô."""
    result = _send_commands([{"code": "find_robot", "value": True}])
    if result == "ok":
        return "Comando de localização enviado."
    return result


@tool
def set_suction(level: str) -> str:
    """Ajusta o nível de sucção do aspirador. level: um de 'standby', 'gentle', 'normal', 'strong'. Use quando o usuário pedir para mudar sucção, aumentar/diminuir potência."""
    level = (level or "").strip().lower()
    if level not in ("standby", "gentle", "normal", "strong"):
        return f"Nível de sucção inválido: use um de standby, gentle, normal, strong (recebido: {level or 'vazio'})."
    result = _send_commands([{"code": "suction", "value": level}])
    if result == "ok":
        return f"Sucção ajustada para {level}."
    return result


@tool
def clean_specific_room(room_name: str) -> str:
    """Limpa um cômodo específico da casa. room_name: nome do cômodo (ex: cozinha, sala, quarto, banheiro)."""
    result = _send_commands([{"code": "switch_go", "value": True}])
    if result == "ok":
        return f"Limpando o cômodo: {room_name}."
    return result
