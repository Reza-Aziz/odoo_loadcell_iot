"""Bridge MQTT -> Odoo: simpan pembacaan timbangan dan tulis ke receipt aktif."""

import json
import logging
import os
import sys
import urllib.request

import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")

MQTT_HOST = os.environ.get("MQTT_HOST", "")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_TLS = os.environ.get("MQTT_TLS", "true").lower() == "true"
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "factory/plant_1/line_1/scale_weight")
MQTT_TARE_GRAM = float(os.environ.get("MQTT_TARE_GRAM") or 0)

ODOO_URL = os.environ.get("ODOO_URL", "http://odoo:8069")
ODOO_DB = os.environ.get("ODOO_DB", "odoo")
ODOO_USER = os.environ.get("ODOO_USER", "admin")
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD", "admin")

# Receipt yang boleh ditimpa beratnya otomatis.
OPEN_STATES = ["confirmed", "waiting", "assigned"]

uid = None


def rpc(service, method, *args, **kwargs):
    body = json.dumps({
        "jsonrpc": "2.0",
        "method": "call",
        "params": {"service": service, "method": method,
                   "args": list(args), "kwargs": kwargs},
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


def parse_kg(payload):
    """Berat dalam kg dari payload device."""
    text = payload.decode(errors="replace").strip()
    try:
        return float(text)  # angka mentah dianggap kilogram
    except ValueError:
        pass
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    if "weight_gram" in data:
        return float(data["weight_gram"]) / 1000
    if "weight" in data:
        value = float(data["weight"])
        return value / 1000 if str(data.get("unit", "kg")).lower() in ("g", "gram") else value
    return None


def write_to_picking(user_id, weight):
    """Tulis berat ke receipt aktif terbaru; verifikasi direset karena berat baru."""
    ids = rpc("object", "execute_kw", ODOO_DB, user_id, ODOO_PASSWORD,
              "stock.picking", "search",
              [[("picking_type_code", "=", "incoming"), ("state", "in", OPEN_STATES)]],
              limit=1, order="id desc")
    if not ids:
        return None
    rpc("object", "execute_kw", ODOO_DB, user_id, ODOO_PASSWORD,
        "stock.picking", "write",
        [ids, {"iot_net_weight": weight, "is_iot_verified": False}])
    return ids[0]


def on_message(client, userdata, msg):
    kg = parse_kg(msg.payload)
    if kg is None:
        print(f"payload tidak dikenali, dilewati: {msg.payload!r}", flush=True)
        return
    weight = round(kg - MQTT_TARE_GRAM / 1000, 3)
    user_id = odoo_uid()
    try:
        rpc("object", "execute_kw", ODOO_DB, user_id, ODOO_PASSWORD,
            "iot.scale.reading", "create", [{"topic": msg.topic, "weight": weight}])
    except Exception as exc:  # noqa: BLE001 - jangan sampai subscriber mati
        print(f"gagal simpan reading: {exc}", flush=True)
        return
    try:
        picking_id = write_to_picking(user_id, weight)
    except Exception as exc:  # noqa: BLE001
        print(f"gagal tulis ke receipt: {exc}", flush=True)
        return
    target = f"receipt #{picking_id}" if picking_id else "tidak ada receipt aktif"
    print(f"{msg.topic} -> {weight} kg -> {target}", flush=True)


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
