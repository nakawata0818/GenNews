import os
import threading
from flask import Flask, request
from urllib.parse import parse_qs
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials # Keep for get_sheet()

from config import LINE_CHANNEL_ACCESS_TOKEN, SHEET_NAME, GOOGLE_SHEET_KEY
from sheet_utils import setup_google_credentials, update_keyword_weight, save_article_log, get_sheet_by_name, set_user_keywords
from send_news import get_more_news, send_line_flex
from feature_extractor import extract_features
from profile import generate_user_profile, generate_profile_summary

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

def safe_get_more_news(user_id):
    """スレッド内でエラーが起きてもプロセスを落とさずログを出す"""
    try:
        print(f"[THREAD] get_more_news started for {user_id}")
        get_more_news(user_id)
    except Exception as e:
        print(f"[THREAD ERROR] get_more_news: {e}")

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
            
            # クエリパラメータの簡易解析 (action=like&kws=AI,経済)
            parsed_data = parse_qs(data)
            params = {k: v[0] for k, v in parsed_data.items()}
            action = params.get('action')
            target_kws_str = params.get('kws', '')
            target_kws = [kw.strip() for kw in target_kws_str.split(',') if kw.strip()]
            article_id = params.get('article_id') # article_idも取得するように変更
            category = params.get('category', 'その他') # categoryも取得

            if action == "like":
                for kw in target_kws:
                    if kw: update_keyword_weight(user_id, kw, 0.2)
                # 記事ログ保存
                if article_id:
                    save_article_log(user_id, article_id, target_kws, category, action)
                reply_message(event['replyToken'], f"「{target_kws_str}」の関心度を上げました👍")
            
            elif action == "dislike":
                for kw in target_kws:
                    if kw: update_keyword_weight(user_id, kw, -0.3)
                # 記事ログ保存
                if article_id:
                    save_article_log(user_id, article_id, target_kws, category, action)
                reply_message(event['replyToken'], f"「{target_kws_str}」の関心度を下げました👎")
                
            elif action == "more":
                # タイムアウト回避のためスレッドで実行
                thread = threading.Thread(target=safe_get_more_news, args=(user_id,))
                thread.start()
                # 先に受領メッセージだけ返す
                reply_message(event['replyToken'], "追加のニュースを探しています...少々お待ちください。")
            
            elif action == "click":
                # 記事ログ保存
                if article_id and params.get('url'):
                    save_article_log(user_id, article_id, target_kws, category, action)
                    # ユーザーに直接URLを開かせる
                    # LINEのFlex MessageのURIアクションは直接開くため、ここでは何もしない
                    # reply_message(event['replyToken'], "記事を開きます。") # これは不要
                    pass
                # URIアクションを直接開くため、ここではreplyは不要
                
            continue

        # 2. メッセージ処理
        if event['type'] == 'message' and event['message']['type'] == 'text':
            user_text = event['message']['text']
            user_id = event['source']['userId']
            print(f"[DEBUG] user_text: {user_text}, user_id: {user_id}")

            if user_text == 'もっと':
                # 非同期で実行
                thread = threading.Thread(target=safe_get_more_news, args=(user_id,))
                thread.start()
                reply_message(event['replyToken'], '追加ニュースを配信しました')

            # (中略: キーワード更新などのロジックは維持)
            elif user_text.startswith('キーワード:'):
                keywords = [k.strip() for k in user_text.replace('キーワード:', '').split(',') if k.strip()]
                keywords_str = ','.join(keywords)

                set_user_keywords(user_id, keywords) # sheet_utilsの関数を使用

                reply_text = f"キーワードを更新しました:\n{keywords_str}"
                reply_message(event['replyToken'], reply_text)

            elif user_text.startswith('キーワード確認'):
                try:
                    # keywordsシートから取得
                    user_kws_with_weight = get_user_keywords(user_id)
                    kws = ", ".join([f"{kw}({weight})" for kw, weight in user_kws_with_weight])
                except Exception as e:
                    print(f"[Sheet find error] {e}")
                    kws = ''
                reply_text = f"現在のキーワード: {kws if kws else '未設定'}"
                reply_message(event['replyToken'], reply_text)
            
            elif user_text == '傾向':
                profile = generate_user_profile(user_id)
                summary = generate_profile_summary(profile)
                reply_message(event['replyToken'], summary)
                # TODO: プロファイルフィードバックボタンの追加
                # reply_message(event['replyToken'], summary, buttons_for_profile_feedback)

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