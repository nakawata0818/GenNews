import os
import threading
from flask import Flask, request
from urllib.parse import parse_qs
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials # Keep for get_sheet()

from config import LINE_CHANNEL_ACCESS_TOKEN, SHEET_NAME, GOOGLE_SHEET_KEY
from sheet_utils import setup_google_credentials, update_keyword_weight, save_article_log, get_sheet_by_name, set_user_keywords, get_user_keywords, update_related_keyword, delete_user_keyword, get_user_state, set_user_state
from send_news import get_more_news, send_line_flex, deliver_news_to_user
from feature_extractor import extract_features
from profile import generate_user_profile, generate_profile_summary
from category import get_category, recategorize_user_keywords
from radio.send_radio import run_radio_flow

app = Flask(__name__)

def safe_get_more_news(user_id):
    """スレッド内でエラーが起きてもプロセスを落とさずログを出す"""
    try:
        print(f"[THREAD] get_more_news started for {user_id}")
        get_more_news(user_id)
    except Exception as e:
        print(f"[THREAD ERROR] get_more_news: {e}")

def safe_deliver_news(user_id):
    """スレッド内でエラーが起きてもプロセスを落とさずログを出す"""
    try:
        print(f"[THREAD] deliver_news started for {user_id}")
        deliver_news_to_user(user_id)
    except Exception as e:
        print(f"[THREAD ERROR] deliver_news: {e}")

@app.route("/linewebhook", methods=['POST'])
def linewebhook():
    try:
        events = request.json['events']
    except Exception:
        return 'ok'

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
            rel_kws_str = params.get('rel_kws', '')
            rel_kws = [kw.strip() for kw in rel_kws_str.split(',') if kw.strip()]
            article_id = params.get('article_id') # article_idも取得するように変更
            category = params.get('category', 'その他') # categoryも取得

            if action == "like":
                for kw in target_kws:
                    if kw: update_keyword_weight(user_id, kw, 0.2)
                for rkw in rel_kws:
                    if rkw: update_related_keyword(user_id, rkw, "like")
                # 記事ログ保存
                if article_id:
                    save_article_log(user_id, article_id, target_kws, category, action)
                msg = f"「{target_kws_str}」の関心度を上げました👍" if target_kws_str else "この記事への関心度を上げました👍"
                reply_message(event['replyToken'], msg)
            
            elif action == "dislike":
                for kw in target_kws:
                    if kw: update_keyword_weight(user_id, kw, -0.3)
                for rkw in rel_kws:
                    if rkw: update_related_keyword(user_id, rkw, "dislike")
                # 記事ログ保存
                if article_id:
                    save_article_log(user_id, article_id, target_kws, category, action)
                msg = f"「{target_kws_str}」の関心度を下げました👎" if target_kws_str else "この記事への関心度を下げました👎"
                reply_message(event['replyToken'], msg)
                
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

            # 現在の対話状態を取得
            state = get_user_state(user_id)

            # 状態に応じた処理（キーワード追加/削除の対話中）
            if state == 'WAITING_FOR_ADD_KEYWORD':
                if user_text == "キャンセル":
                    set_user_state(user_id, 'IDLE')
                    reply_message(event['replyToken'], "追加をキャンセルしました。")
                else:
                    kw = user_text
                    update_keyword_weight(user_id, kw, 0.0)
                    recategorize_user_keywords(user_id)
                    set_user_state(user_id, 'IDLE')
                    reply_message(event['replyToken'], f"キーワード「{kw}」を追加し、カテゴリを再構成しました。")
                continue

            elif state == 'WAITING_FOR_DELETE_NUMBER':
                if user_text == "キャンセル":
                    set_user_state(user_id, 'IDLE')
                    reply_message(event['replyToken'], "削除をキャンセルしました。")
                else:
                    try:
                        # 全角数字やドットなどが混じっても対応できるように
                        num_str = user_text.replace('．', '').replace('.', '').strip()
                        num = int(num_str)
                        user_kws = get_user_keywords(user_id)
                        if 1 <= num <= len(user_kws):
                            kw_to_del = user_kws[num-1][0]
                            if delete_user_keyword(user_id, kw_to_del):
                                recategorize_user_keywords(user_id)
                                set_user_state(user_id, 'IDLE')
                                reply_message(event['replyToken'], f"キーワード「{kw_to_del}」を削除し、カテゴリを再構成しました。")
                            else:
                                reply_message(event['replyToken'], "削除に失敗しました。番号を確認してください。")
                        else:
                            reply_message(event['replyToken'], f"1〜{len(user_kws)}の番号を入力してください。")
                    except ValueError:
                        reply_message(event['replyToken'], "有効な数字を入力するか「キャンセル」と送ってください。")
                continue

            if user_text == 'もっと':
                # 非同期で実行
                thread = threading.Thread(target=safe_get_more_news, args=(user_id,))
                thread.start()
                reply_message(event['replyToken'], '追加ニュースを配信しました')

            elif user_text == 'ニュース実行':
                # 非同期で実行
                thread = threading.Thread(target=safe_deliver_news, args=(user_id,))
                thread.start()
                reply_message(event['replyToken'], 'ニュースの生成を開始しました。完了次第お届けします。')

            elif user_text == 'ラジオ':
                # ラジオ生成は非常に重いためスレッドで実行
                thread = threading.Thread(target=run_radio_flow, args=(user_id,))
                thread.start()
                reply_message(event['replyToken'], '📻 本日のニュースを音声用に編集しています。1〜2分ほどお待ちください。')

            # (中略: キーワード更新などのロジックは維持)
            elif user_text.startswith('キーワード:'):
                keywords = [k.strip() for k in user_text.replace('キーワード:', '').split(',') if k.strip()]
                keywords_str = ','.join(keywords)

                set_user_keywords(user_id, keywords) # sheet_utilsの関数を使用

                reply_text = f"キーワードを更新しました:\n{keywords_str}"
                reply_message(event['replyToken'], reply_text)

            elif user_text == 'キーワード追加':
                set_user_state(user_id, 'WAITING_FOR_ADD_KEYWORD')
                reply_message(event['replyToken'], "追加したいキーワードを1つ送信してください。\n（中止する場合は「キャンセル」）")

            elif user_text == 'キーワード削除':
                user_kws = get_user_keywords(user_id)
                if not user_kws:
                    reply_message(event['replyToken'], "登録されているキーワードがありません。")
                else:
                    set_user_state(user_id, 'WAITING_FOR_DELETE_NUMBER')
                    list_str = "\n".join([f"{i+1}. {kw}" for i, (kw, w) in enumerate(user_kws)])
                    reply_message(event['replyToken'], f"削除するキーワードの番号を入力してください：\n\n{list_str}\n\n（中止する場合は「キャンセル」）")

            elif user_text.startswith('キーワード確認'):
                try:
                    # keywordsシートから取得
                    user_kws_with_weight = get_user_keywords(user_id)
                    if not user_kws_with_weight:
                        reply_text = "現在のキーワード: 未設定"
                    else:
                        # カテゴリごとに束ねる
                        category_groups = {}
                        for kw, weight in user_kws_with_weight:
                            cat = get_category(kw)
                            if cat not in category_groups:
                                category_groups[cat] = []
                            # 重みが2.0以上の重要ワードには★を付与
                            mark = "★" if weight >= 2.0 else ""
                            category_groups[cat].append(f"{kw}{mark}({weight:.1f})")
                        
                        result_lines = ["📋 登録キーワード（カテゴリ別）"]
                        for cat, kws in category_groups.items():
                            result_lines.append(f"\n──────────\n■ {cat}")
                            result_lines.append("・" + "\n・".join(kws))
                        reply_text = "\n".join(result_lines)
                except Exception as e:
                    print(f"[Keyword check error] {e}")
                    reply_text = "キーワードの取得中にエラーが発生しました。"
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