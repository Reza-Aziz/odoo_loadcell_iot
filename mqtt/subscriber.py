"""Subscriber MQTT -> simpan pembacaan timbangan ke Odoo lewat JSON-RPC."""

import json
import os
import sys
import urllib.request

import paho.mqtt.client as mqtt

MQTT_HOST = os.environ.get("MQTT_HOST", "")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_TLS = os.environ.get("MQTT_TLS", "true").lower() == "true"
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "factory/plant_1/line_1/scale_weight")

ODOO_URL = os.environ.get("ODOO_URL", "http://odoo:8069")
ODOO_DB = os.environ.get("ODOO_DB", "odoo")
ODOO_USER = os.environ.get("ODOO_USER", "admin")
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD", "admin")

uid = None


def rpc(service, method, *args):
    body = json.dumps({
        "jsonrpc": "2.0",
        "method": "call",
        "params": {"service": service, "method": method, "args": args},
    }).encode()
    req = urllib.request.Request(
        f"{ODOO_URL}/jsonrpc", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.load(resp)
    if "error" in result:
        raise RuntimeError(result["error"])
    return result["result"]


def odoo_uid():
    global uid
    if uid is None:
        uid = rpc("common", "login", ODOO_DB, ODOO_USER, ODOO_PASSWORD)
        if not uid:
            raise RuntimeError("login Odoo gagal, cek ODOO_USER/ODOO_PASSWORD")
    return uid


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code != 0:
        print(f"gagal connect ke {MQTT_HOST}:{MQTT_PORT}: {reason_code}", flush=True)
        return
    client.subscribe(MQTT_TOPIC, qos=1)
    print(f"subscribe {MQTT_TOPIC} @ {MQTT_HOST}:{MQTT_PORT}", flush=True)


def on_message(client, userdata, msg):
    try:
        weight = float(msg.payload.decode().strip())
    except ValueError:
        print(f"payload bukan angka, dilewati: {msg.payload!r}", flush=True)
        return
    try:
        rpc("object", "execute_kw", ODOO_DB, odoo_uid(), ODOO_PASSWORD,
            "iot.scale.reading", "create", [{"topic": msg.topic, "weight": weight}])
        print(f"{msg.topic} -> {weight} kg tersimpan", flush=True)
    except Exception as exc:  # noqa: BLE001 - jangan sampai subscriber mati
        print(f"gagal simpan ke Odoo: {exc}", flush=True)


def main():
    if not MQTT_HOST:
        sys.exit("MQTT_HOST belum diisi (salin .env.example jadi .env)")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if os.environ.get("MQTT_USERNAME"):
        client.username_pw_set(os.environ["MQTT_USERNAME"], os.environ.get("MQTT_PASSWORD", ""))
    if MQTT_TLS:
        client.tls_set()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect_async(MQTT_HOST, MQTT_PORT)
    client.loop_forever(retry_first_connection=True)


if __name__ == "__main__":
    main()
