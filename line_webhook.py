
import os
from flask import Flask, request
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import LINE_CHANNEL_ACCESS_TOKEN, SHEET_NAME, GOOGLE_SHEET_KEY
from sheet_utils import setup_google_credentials, update_keyword_weight
from send_news import get_more_news, send_line_flex

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
        # 1. Postback処理 (👍👎ボタンなどの操作)
        if event['type'] == 'postback':
            data = event['postback']['data']
            user_id = event['source']['userId']
            from sheet_utils import get_user_keywords
            
            if "action=like" in data:
                for kw, _ in get_user_keywords(user_id):
                    update_keyword_weight(user_id, kw, 0.2)
                reply_message(event['replyToken'], "フィードバックありがとうございます！より興味に近いニュースをお届けします (+)")
            
            elif "action=dislike" in data:
                for kw, _ in get_user_keywords(user_id):
                    update_keyword_weight(user_id, kw, -0.3)
                reply_message(event['replyToken'], "フィードバックありがとうございます。このトピックの頻度を減らします (-)")
                
            elif "action=more" in data:
                get_more_news(user_id)
                # 返信は get_more_news 内でFlexとして送られるか、必要に応じてreplyを送る
                # reply_message(event['replyToken'], "追加ニュースを探しています...")
                
            continue

        # 2. メッセージ処理
        if event['type'] == 'message' and event['message']['type'] == 'text':
            user_text = event['message']['text']
            user_id = event['source']['userId']
            print(f"[DEBUG] user_text: {user_text}, user_id: {user_id}")

            if user_text == 'もっと':
                get_more_news(user_id)
                reply_message(event['replyToken'], '追加ニュースを配信しました')

            # (中略: キーワード更新などのロジックは維持)

            elif user_text.startswith('キーワード:'):
                keywords = [k.strip() for k in user_text.replace('キーワード:', '').split(',') if k.strip()]
                keywords_str = ','.join(keywords)

                # 従来シートにも書き込み（従来のまま）
                try:
                    cell = sheet.find(user_id)
                    sheet.update_cell(cell.row, 2, keywords_str)  # 2列目にキーワード
                except Exception as e:
                    print(f"[Sheet find error] {e}")
                    # 新規ユーザーの場合は末尾に追加
                    sheet.append_row([user_id, keywords_str])

                # keywordsシートにも1キーワードずつ登録（重複はスキップ）
                from sheet_utils import get_sheet_by_name
                kw_sheet = get_sheet_by_name('keywords')
                existing = kw_sheet.get_all_records()
                for kw in keywords:
                    # 既に同じuser_id, keywordがあればスキップ
                    if any(r.get('user_id') == user_id and r.get('keyword') == kw for r in existing):
                        continue
                    kw_sheet.append_row([user_id, kw, 1.0])

                reply_text = f"キーワードを更新しました:\n{keywords_str}"
                reply_message(event['replyToken'], reply_text)

            elif user_text.startswith('キーワード確認'):
                try:
                    cell = sheet.find(user_id)
                    kws = sheet.cell(cell.row, 2).value
                except Exception as e:
                    print(f"[Sheet find error] {e}")
                    kws = ''
                reply_text = f"現在のキーワード: {kws if kws else '未設定'}"
                reply_message(event['replyToken'], reply_text)

            else:
                reply_message(event['replyToken'], "キーワードを設定するには「キーワード:AI,経済」のように送信してください。\nニュース内の👍👎ボタンで学習します。")

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