import paho.mqtt.client as mqtt
import random
import time

# MQTTブローカー情報
MQTT_BROKER = "192.168.1.238"  # MosquittoブローカーのIPアドレス
MQTT_PORT = 1883               # MQTTポート番号

# MACアドレス（コロンなし）
MAC_ADDRESS = "E89F6D09C758"

# トピック名の定義
TOPIC_ID = f"{MAC_ADDRESS}/id"
TOPIC_X = f"{MAC_ADDRESS}/x"
TOPIC_Y = f"{MAC_ADDRESS}/y"

# MQTTクライアントの設定
client = mqtt.Client()

# MQTTブローカーに接続
print(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# メッセージ送信
try:
    # ランダムな値を生成
    id_value = random.randint(1, 100)              # 整数
    x_value = round(random.uniform(-100, 100), 3) # 小数点第3位まで
    y_value = round(random.uniform(-100, 100), 3) # 小数点第3位まで

    # メッセージを送信
    print(f"Publishing to {TOPIC_ID}: {id_value}")
    client.publish(TOPIC_ID, str(id_value))

    print(f"Publishing to {TOPIC_X}: {x_value}")
    client.publish(TOPIC_X, str(x_value))

    print(f"Publishing to {TOPIC_Y}: {y_value}")
    client.publish(TOPIC_Y, str(y_value))

    print("Messages published successfully!")

    # 接続を維持
    print("Keeping the connection alive...")
    while True:
        time.sleep(1)  # 無限ループで接続を維持（Ctrl+Cで停止可能）

except KeyboardInterrupt:
    print("\nManual interruption. Disconnecting...")
    client.disconnect()
    print("Disconnected from MQTT broker.")
