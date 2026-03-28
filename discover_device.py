"""
Script para descobrir os comandos e status suportados pelo dispositivo Tuya.
Rode com: python3 discover_device.py
"""
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

import json
from agent.tools import _get_tuya_client

client, device_id = _get_tuya_client()

if client is None:
    print("Erro: cliente Tuya não inicializado. Verifique as variáveis no .env.")
    exit(1)

print(f"Device ID: {device_id}\n")

print("=" * 50)
print("FUNÇÕES SUPORTADAS (comandos disponíveis)")
print("=" * 50)
resp = client.get(f"/v1.0/iot-03/devices/{device_id}/functions")
if resp.get("success"):
    for fn in resp.get("result", {}).get("functions", []):
        print(f"  code: {fn['code']}")
        print(f"  type: {fn.get('type')}")
        print(f"  values: {fn.get('values')}")
        print()
else:
    print(f"Erro: {resp}")

print("=" * 50)
print("STATUS ATUAL DO DISPOSITIVO")
print("=" * 50)
resp = client.get(f"/v1.0/devices/{device_id}/status")
if resp.get("success"):
    for item in resp.get("result", []):
        print(f"  {item['code']}: {item['value']}")
else:
    print(f"Erro: {resp}")
