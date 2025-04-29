import os
import json
import gspread
from google.oauth2.service_account import Credentials

def main():
    # 1) サービスアカウントのJSONファイルパスを指定
    credential_path = "/home/pi/credential.json"

    # 2) スコープの指定
    #   Google Sheets API を使う場合、以下のスコープを指定しておく
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    # 3) 認証情報の作成
    credentials = Credentials.from_service_account_file(credential_path, scopes=SCOPES)

    # 4) gspread でクライアントインスタンス作成
    client = gspread.authorize(credentials)

    # 5) スプレッドシートキー（URL中に含まれるID部分）を指定
    # 例えばスプレッドシートURLが
    #   https://docs.google.com/spreadsheets/d/XXXXXXXXXXXXXXXXXXXXXXX/edit
    # の場合は 'XXXXXXXXXXXXXXXXXXXXXXX' がシートキー
    SPREADSHEET_KEY = "1wuKt5C-eyRiX9BStpcmEMlMjL1f4JZeXr_r3kfpcR9U"

    # 6) スプレッドシートを開く
    sheet = client.open_by_key(SPREADSHEET_KEY)

    # 7) 読み込みたいワークシートを指定
    worksheet = sheet.worksheet("Sheet1")

    # 8) A1:D10 を例に読み込む
    values = worksheet.get("A1:D10")

    # 9) 内容を表示
    print(values)

if __name__ == "__main__":
    main()
