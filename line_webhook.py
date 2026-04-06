
import os
from flask import Flask, request
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import LINE_CHANNEL_ACCESS_TOKEN, SHEET_NAME, GOOGLE_SHEET_KEY
from sheet_utils import setup_google_credentials

app = Flask(__name__)


def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_path = setup_google_credentials()
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    client = gspread.authorize(creds)
    if GOOGLE_SHEET_KEY:
        return client.open_by_key(GOOGLE_SHEET_KEY).sheet1
    else:
        return client.open(SHEET_NAME).sheet1

@app.route("/linewebhook", methods=['POST'])
def linewebhook():
    try:
        events = request.json['events']
    except Exception:
        return 'ok'

    sheet = get_sheet()
    for event in events:
        if event['type'] == 'message' and event['message']['type'] == 'text':
            user_text = event['message']['text']
            user_id = event['source']['userId']

            if user_text.startswith('キーワード:'):
                keywords = [k.strip() for k in user_text.replace('キーワード:', '').split(',') if k.strip()]
                keywords_str = ','.join(keywords)

                # ユーザーIDの行を検索
                try:
                    cell = sheet.find(user_id)
                    sheet.update_cell(cell.row, 2, keywords_str)  # 2列目にキーワード
                except gspread.exceptions.CellNotFound:
                    # 新規ユーザーの場合は末尾に追加
                    sheet.append_row([user_id, keywords_str])

                reply_text = f"キーワードを更新しました:\n{keywords_str}"
                reply_message(event['replyToken'], reply_text)

            elif user_text.startswith('キーワード確認'):
                try:
                    cell = sheet.find(user_id)
                    kws = sheet.cell(cell.row, 2).value
                except gspread.exceptions.CellNotFound:
                    kws = ''
                reply_text = f"現在のキーワード: {kws if kws else '未設定'}"
                reply_message(event['replyToken'], reply_text)

            else:
                reply_message(event['replyToken'], "キーワードを設定するには「キーワード:」で送信してください。")

    return 'ok'


def reply_message(reply_token, text):
    url = 'https://api.line.me/v2/bot/message/reply'
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "replyToken": reply_token,
        "messages": [
            {"type": "text", "text": text}
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[LINE reply error] {e}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)