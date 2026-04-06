
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
    except Exception as e:
        print(f"[webhook error] {e}")
        return 'ok'

    try:
        sheet = get_sheet()
        for event in events:
            # ...既存の処理...
            pass
    except Exception as e:
        print(f"[sheet error] {e}")
        # 例外時も必ず200を返す
        return 'ok'

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