import os
import json
from flask import Flask, request, abort
import requests
from config import LINE_CHANNEL_ACCESS_TOKEN

app = Flask(__name__)

KEYWORDS_PATH = os.path.join(os.path.dirname(__file__), 'keywords.json')

@app.route("/linewebhook", methods=['POST'])
def linewebhook():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        events = request.json['events']
    except Exception:
        return 'ok'
    for event in events:
        if event['type'] == 'message' and event['message']['type'] == 'text':
            user_text = event['message']['text']
            user_id = event['source']['userId']
            if user_text.startswith('キーワード:'):
                # 例: キーワード:AI,経済,健康
                keywords = [k.strip() for k in user_text.replace('キーワード:', '').split(',') if k.strip()]
                with open(KEYWORDS_PATH, 'w', encoding='utf-8') as f:
                    json.dump(keywords, f, ensure_ascii=False, indent=2)
                reply_text = f"キーワードを更新しました:\n{', '.join(keywords)}"
                reply_message(event['replyToken'], reply_text)
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
    requests.post(url, headers=headers, json=data)

if __name__ == "__main__":
    app.run(port=5000)
