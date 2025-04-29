import paho.mqtt.client as mqtt
import csv
import re
import time
import random

MQTT_BROKER = "192.168.1.238"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60

device_data = {}
try:
    with open("/home/pi/mqtt/mqtt/devices.csv", "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            device_data[row["macAddress"]] = {
                "id": row["id"],
                "x": row["x"],
                "y": row["y"],
                "connected": False  # 初期化メッセージを受けたかどうか
            }
    print(f"Loaded device data: {len(device_data)} devices.")
except FileNotFoundError:
    print("Error: devices.csv not found.")
    exit(1)

client = mqtt.Client(protocol=mqtt.MQTTv311)

ini_pattern = re.compile(r"^ini/([0-9A-F]{12})$")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()
    print(f"Received: {topic} -> {payload}")

    # もし ini/XXXXXXXXXXXX にマッチしたら
    match_ini = ini_pattern.match(topic)
    if match_ini:
        mac_address = match_ini.group(1)
        print(f"Init from MAC: {mac_address}")

        if mac_address in device_data:
            dev_info = device_data[mac_address]
            idxy_payload = f"{dev_info['id']},{dev_info['x']},{dev_info['y']}"
            client.publish(f"{mac_address}/idxy", idxy_payload, qos=1)
            print(f"Published idxy => {mac_address}/idxy : {idxy_payload}")

            dev_info["connected"] = True
        else:
            print(f"Unknown MAC: {mac_address}")
        return

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker!")
        # 常にini/+を購読するので、デバイスが再接続してきたら拾える
        client.subscribe("ini/+")
        print("Subscribed: ini/+")
    else:
        print(f"Failed to connect, rc = {rc}")

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"Unexpected disconnection. rc = {rc}")
    else:
        print("Disconnected from broker.")

client.on_message = on_message
client.on_connect = on_connect
client.on_disconnect = on_disconnect

print("Connecting...")
client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)

# バックグラウンドで受信＆再接続処理
client.loop_start()

try:
    while True:
        # 送信処理 (1秒に1回)
        # ランダムRGB生成 (3バイト)
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        for mac, dev_info in device_data.items():
            if dev_info["connected"]:
                dev_id = dev_info["id"]
                # # ランダムRGB生成 (3バイト)
                # r = random.randint(0, 255)
                # g = random.randint(0, 255)
                # b = random.randint(0, 255)
                color_topic = f"cl/{dev_id}"
                # 3バイトのペイロードを送信
                payload = bytes([r, g, b])
                client.publish(color_topic, payload, qos=0)
                print(f"Publish => {color_topic} : {r},{g},{b}")

        time.sleep(0.1)

except KeyboardInterrupt:
    print("Exiting...")
    client.loop_stop()
    client.disconnect()
