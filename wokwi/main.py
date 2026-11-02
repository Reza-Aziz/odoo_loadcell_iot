# Wokwi ESP32 + MicroPython -> HiveMQ
# Potensiometer di GPIO34 dipetakan ke 0..100 kg, publish tiap 2 detik.

import time

import network
from machine import ADC, Pin
from umqtt.simple import MQTTClient

WIFI_SSID = "Wokwi-GUEST"
WIFI_PASS = ""
BROKER = "broker.hivemq.com"
TOPIC = b"factory/plant_1/line_1/scale_weight"
CLIENT_ID = b"esp32_scale_01"
FULL_SCALE_KG = 100.0
INTERVAL_S = 2

pot = ADC(Pin(34))
pot.atten(ADC.ATTN_11DB)


def connect_wifi():
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    wifi.connect(WIFI_SSID, WIFI_PASS)
    while not wifi.isconnected():
        time.sleep_ms(200)
    print("wifi:", wifi.ifconfig()[0])


def read_kg():
    # rata-rata 10 sampel: ADC berderit, sekali baca bisa meleset jauh
    total = 0
    for _ in range(10):
        total += pot.read()
    return round(total / 10 / 4095 * FULL_SCALE_KG, 2)


def main():
    connect_wifi()
    client = MQTTClient(CLIENT_ID, BROKER, 1883, keepalive=30)
    client.connect()
    print("mqtt: terhubung ke", BROKER)
    while True:
        kg = read_kg()
        client.publish(TOPIC, str(kg))
        print("publish:", kg, "kg")
        time.sleep(INTERVAL_S)


main()
