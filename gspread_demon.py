import re
import time               # ← 追加
import socket             # ← 追加
import paho.mqtt.client as mqtt
import gspread
from google.oauth2.service_account import Credentials

def wait_for_broker(host="localhost", port=1883, timeout=10):
    """MQTT ブローカーが開くまで最大 timeout 秒待つ"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), 2):
                return True      # 接続成功＝ブローカー稼働
        except OSError:
            time.sleep(1)
    raise RuntimeError(f"MQTT broker {host}:{port} not available")

# Google Sheets 読み取り用関数
def get_sheets_values():
    """
    Googleスプレッドシートから値(A1:E75)を取得して返す。
    """
    # credential_path = "credential.json"
    credential_path = "/Users/fu/device_init/fu_raspi_device_init/credential.json"

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    credentials = Credentials.from_service_account_file(credential_path, scopes=SCOPES)
    client = gspread.authorize(credentials)

    SPREADSHEET_KEY = "1wuKt5C-eyRiX9BStpcmEMlMjL1f4JZeXr_r3kfpcR9U"
    sheet = client.open_by_key(SPREADSHEET_KEY)

    worksheet = sheet.worksheet("Sheet1")
    values = worksheet.get("A1:E76")  # E列まで読み取り

    return values

# MQTT コールバック関数
ini_pattern = re.compile(r"^ini/([0-9A-F]{12})$")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()
    print(f"Received: {topic} -> {payload}")

    match_ini = ini_pattern.match(topic)
    if not match_ini:
        return

    mac_address = match_ini.group(1)
    print(f"Init from MAC: {mac_address}")

    device_data = userdata["device_data"]
    if mac_address in device_data:
        info = device_data[mac_address]
        
        # idxy + ラジアン値の配信
        response = f"{info['id']},{info['x']},{info['y']}"
        if 'h_enc' in info and info['h_enc']:
            response += f",{info['h_enc']}"
        
        client.publish(f"{mac_address}/idxy", response, qos=1)
        print(f"Published => {mac_address}/idxy : {response}")
        
        info["connected"] = True
    else:
        print(f"Unknown MAC: {mac_address}")


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker!")
        client.subscribe("ini/+")
        print("Subscribed to ini/+")
    else:
        print(f"Failed to connect, rc={rc}")


def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"Unexpected disconnection (rc={rc})")
    else:
        print("Disconnected cleanly.")


def main():
    # 1) シート読み込みと device_data 構築
    rows = get_sheets_values()
    device_data = {}
    for row in rows[1:]:
        if len(row) < 4:
            continue
        
        mac, dev_id, x, y = row[0], row[1], row[2], row[3]
        
        # E列（horizontalEncoderValue）の処理 - ラジアン値として処理
        h_enc = None
        if len(row) > 4 and row[4]:
            try:
                # 文字列から数値に変換し、小数点以下2桁でフォーマット
                radian_value = float(row[4])
                # 0.00～6.28の範囲チェック
                if 0.00 <= radian_value <= 6.28:
                    h_enc = f"{radian_value:.2f}"
                else:
                    print(f"Warning: h_enc value {radian_value} for MAC {mac} is out of range (0.00-6.28)")
            except ValueError:
                print(f"Warning: Invalid h_enc value '{row[4]}' for MAC {mac}")
                h_enc = None
        
        device_data[mac] = {
            "id": dev_id, 
            "x": x, 
            "y": y, 
            "h_enc": h_enc,
            "connected": False
        }

    # デバイスデータの確認用出力
    print("Loaded device data:")
    for mac, data in device_data.items():
        print(f"  {mac}: id={data['id']}, x={data['x']}, y={data['y']}, h_enc={data['h_enc']}")

    # 2) MQTT クライアント設定
    broker, port, keepalive = "192.168.1.2", 1883, 60
    client = mqtt.Client(protocol=mqtt.MQTTv311, userdata={"device_data": device_data})
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    print("Connecting to MQTT broker...")
    wait_for_broker(broker, port) 
    client.connect(broker, port, keepalive)

    try:
        print("Waiting for ini/ messages...")
        client.loop_forever()
    except KeyboardInterrupt:
        print("Interrupted by user, exiting...")
    finally:
        client.disconnect()

if __name__ == "__main__":
    main()