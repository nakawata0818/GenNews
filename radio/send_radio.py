import sys
import os
# プロジェクトのルートディレクトリを検索パスに追加して config や send_news を読み込めるようにする
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from config import LINE_CHANNEL_ACCESS_TOKEN, RENDER_HOSTNAME
from send_news import get_prepared_articles # 後ほど send_news.py に追加
from radio.radio_script import generate_radio_script
from radio.tts_google import generate_audio
import os

def run_radio_flow(user_id):
    """ラジオニュース配信のメインフロー"""
    # 1. ニュース記事の選定 (既存ロジックを流用)
    print(f"[RADIO] Fetching articles for {user_id}")
    articles = get_prepared_articles(user_id)
    print(f"[RADIO] {len(articles)} articles selected for the script.")
    
    if not articles:
        send_line_text(user_id, "ラジオで放送できる新しいニュースが見つかりませんでした。")
        return

    # 2. 台本生成
    print(f"[RADIO] Generating script...")
    script = generate_radio_script(articles)

    # 3. 音声生成
    print(f"[RADIO] Generating audio...")
    audio_res = generate_audio(script)
    
    if not audio_res:
        send_line_text(user_id, "申し訳ありません。音声の生成に失敗しました。")
        return
    
    filename, audio_path = audio_res
    print(f"[RADIO] Audio generated successfully: {filename}")

    # 4. URL生成 (Renderまたはngrokのホスト名を使用)
    audio_url = f"https://{RENDER_HOSTNAME}/audio/{filename}"
    print(f"[RADIO] Audio URL: {audio_url}")

    # 5. LINE送信
    print(f"[RADIO] Sending audio to LINE...")
    send_audio_message(user_id, audio_url)

def send_audio_message(user_id, audio_url):
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}", "Content-Type": "application/json"}
    data = {
        "to": user_id,
        "messages": [
            {"type": "text", "text": "🎧 本日のパーソナライズニュースラジオです。"},
            {"type": "audio", "originalContentUrl": audio_url, "duration": 90000} # 最大90秒
        ]
    }
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data)

def send_line_text(user_id, text):
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}", "Content-Type": "application/json"}
    data = {"to": user_id, "messages": [{"type": "text", "text": text}]}
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data)

if __name__ == "__main__":
    # コマンドラインから直接実行してテストするためのブロック
    from config import LINE_USER_ID
    if LINE_USER_ID:
        print(f"[TEST] ユーザー {LINE_USER_ID} 宛にラジオ配信テストを開始します...")
        run_radio_flow(LINE_USER_ID)
    else:
        print("エラー: config.py または環境変数に LINE_USER_ID が設定されていません。")