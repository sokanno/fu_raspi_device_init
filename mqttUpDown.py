import os
import json
import csv
import re
import time
import random
import paho.mqtt.client as mqtt

import gspread
from google.oauth2.service_account import Credentials

# ★ 初期ハンドシェイクをスキップするかどうかのフラグ（True ならスキップ）
SKIP_INITIAL_HANDSHAKE = True

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
# ini/XXXXXXXXXXXX 形式のトピックパターン
ini_pattern = re.compile(r"^ini/([0-9A-F]{12})$")
# sendTest/<device_id> 形式のトピックパターン
send_test_pattern = re.compile(r"^sendTest/(.+)$")

def on_message(client, userdata, msg):
    topic = msg.topic
    # ここでは payload を文字列として扱っていますが、必要に応じて変換してください
    payload = msg.payload.decode()
    # print(f"Received: {topic} -> {payload}")

    # --- ini/XXXXXXXXXXXX トピックの場合 ---
    match_ini = ini_pattern.match(topic)
    if match_ini:
        mac_address = match_ini.group(1)
        print(f"Init from MAC: {mac_address}")

        device_data = userdata["device_data"]
        if mac_address in device_data:
            dev_info = device_data[mac_address]
            # すでに接続済みならハンドシェイク処理をスキップ
            if dev_info["connected"]:
                print(f"Device {mac_address} already connected. Skipping handshake response.")
                return

            # ハンドシェイク処理（未スキップの場合のみ実施）
            idxy_payload = f"{dev_info['id']},{dev_info['x']},{dev_info['y']}"
            client.publish(f"{mac_address}/idxy", idxy_payload, qos=1)
            print(f"Published idxy => {mac_address}/idxy : {idxy_payload}")
            dev_info["connected"] = True
        else:
            print(f"Unknown MAC: {mac_address}")
        return

    # --- sendTest/<device_id> トピックの場合 ---
    match_send_test = send_test_pattern.match(topic)
    if match_send_test:
        device_id = match_send_test.group(1)
        # payloadはランダムな数字文字列（例："12345"）となる前提
        # ここで必要に応じてデータの記録や処理を追加できます
        return

    # その他のトピックは必要に応じて処理
    print("Unhandled topic.")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker!")
        # ini/＋とsendTest/＋の両方を購読
        client.subscribe("ini/+")
        client.subscribe("sendTest/+")
        print("Subscribed: ini/+ and sendTest/+")
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
    # 1行目はヘッダとして飛ばす想定
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

    # ★ 初期ハンドシェイクをスキップする場合は、すべてのデバイスを接続済みとする
    if SKIP_INITIAL_HANDSHAKE:
        for dev in device_data.values():
            dev["connected"] = True
        print("Skipping initial handshake; all devices marked as connected.")

    # === 3) MQTTクライアントのセットアップ ===
    MQTT_BROKER = "192.168.1.238"
    MQTT_PORT = 1883
    MQTT_KEEPALIVE = 60

    # userdata に device_data を格納
    client = mqtt.Client(protocol=mqtt.MQTTv311, userdata={"device_data": device_data})
    client.on_message = on_message
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    print("Connecting to MQTT broker...")
    client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)

    # バックグラウンドで受信＆再接続処理
    client.loop_start()

    try:
        # === 4) 定期的な送信処理と受信待ちのメインループ ===
        while True:
            # ランダムRGB生成 (3バイト)
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)

            # 接続済みデバイスに対して publish
            for mac, dev_info in device_data.items():
                if dev_info["connected"]:
                    dev_id = dev_info["id"]
                    color_topic = f"cl/{dev_id}"
                    payload = bytes([r, g, b])  # 3バイトのペイロード
                    client.publish(color_topic, payload, qos=0)
                    # print(f"Published => {color_topic} : {r},{g},{b}")

            # フレームレートに合わせた待ち時間（ここでは1秒）
            time.sleep(0.05)
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
