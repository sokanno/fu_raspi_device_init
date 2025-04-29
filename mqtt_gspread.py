import os
import json
import csv
import re
import time
import random
import paho.mqtt.client as mqtt

import gspread
from google.oauth2.service_account import Credentials

##############################
# Google Sheets 読み取り用関数
##############################
def get_sheets_values():
    """
    Googleスプレッドシートから値(A1:D75)を取得して返す。
    """
    credential_path = "/home/pi/credential.json"
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    credentials = Credentials.from_service_account_file(credential_path, scopes=SCOPES)
    client = gspread.authorize(credentials)

    SPREADSHEET_KEY = "1wuKt5C-eyRiX9BStpcmEMlMjL1f4JZeXr_r3kfpcR9U"
    sheet = client.open_by_key(SPREADSHEET_KEY)

    worksheet = sheet.worksheet("Sheet1")
    values = worksheet.get("A1:D76")

    return values

##############################
# MQTT コールバック関数
##############################
ini_pattern = re.compile(r"^ini/([0-9A-F]{12})$")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()
    print(f"Received: {topic} -> {payload}")

    # ini/XXXXXXXXXXXX にマッチしたら
    match_ini = ini_pattern.match(topic)
    if match_ini:
        mac_address = match_ini.group(1)
        print(f"Init from MAC: {mac_address}")

        # userdata["device_data"] から情報を取得
        device_data = userdata["device_data"]
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
        # 常に ini/+ を購読
        client.subscribe("ini/+")
        print("Subscribed: ini/+")
    else:
        print(f"Failed to connect, rc = {rc}")

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"Unexpected disconnection. rc = {rc}")
    else:
        print("Disconnected from broker.")

##############################
# メイン処理
##############################
def main():
    # === 1) Googleスプレッドシート読み込み ===
    sheet_values = get_sheets_values()
    print("=== Google Sheets (A1:D75) ===")
    for row in sheet_values:
        print(row)
    print("================================\n")

    # === 2) スプレッドシートの情報で device_data を作成 ===
    device_data = {}
    # 1行目をヘッダとして飛ばす想定の場合
    for row in sheet_values[1:]:
        # 例: row = ['ABCD12345678', '1', '10', '20']
        if len(row) < 4:
            continue
        mac = row[0]
        dev_id = row[1]
        x = row[2]
        y = row[3]

        device_data[mac] = {
            "id": dev_id,
            "x": x,
            "y": y,
            "connected": False
        }

    # === 3) MQTTクライアントのセットアップ ===
    MQTT_BROKER = "192.168.1.238"
    MQTT_PORT = 1883
    MQTT_KEEPALIVE = 60

    client = mqtt.Client(protocol=mqtt.MQTTv311, userdata={"device_data": device_data})
    client.on_message = on_message
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    print("Connecting to MQTT broker...")
    client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)

    # バックグラウンドで受信＆再接続処理
    client.loop_start()

    try:
        # === 4) 定期的な送信処理の例 ===
        while True:
            # ランダムRGB生成 (3バイト)
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)

            # 接続済みデバイスに対して publish
            # for mac, dev_info in device_data.items():
            #     if dev_info["connected"]:
            #         dev_id = dev_info["id"]
            #         color_topic = f"cl/{dev_id}"
            #         payload = bytes([r, g, b])  # 3バイトのペイロード
            #         client.publish(color_topic, payload, qos=0)
            #         # print(f"Publish => {color_topic} : {r},{g},{b}")

            # time.sleep(0.05)

    except KeyboardInterrupt:
        print("Exiting...")

    finally:
        client.loop_stop()
        client.disconnect()

##############################
# エントリーポイント
##############################
if __name__ == "__main__":
    main()
