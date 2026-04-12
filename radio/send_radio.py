import sys
import time
import os
# プロジェクトのルートディレクトリを検索パスに追加して config や send_news を読み込めるようにする
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from config import LINE_CHANNEL_ACCESS_TOKEN, RENDER_HOSTNAME
from send_news import get_prepared_articles # 後ほど send_news.py に追加
from radio.radio_script import generate_radio_script
from radio.tts_google import generate_audio
import os

def run_radio_flow(user_id, articles, time_of_day_label):
    """ラジオニュース配信のメインフロー"""
    print(f"[DEBUG][RADIO] Starting radio flow for {user_id} with {len(articles)} articles")

    # 2. 台本生成
    print(f"[RADIO] Generating script...")
    script = generate_radio_script(articles, time_of_day_label)

    # 3. 音声生成
    print(f"[RADIO] Generating audio...")
    tts_start = time.time()
    audio_res = generate_audio(script)
    
    if not audio_res:
        send_line_text(user_id, "申し訳ありません。音声の生成に失敗しました。")
        return
    
    filename, audio_path = audio_res
    print(f"[DEBUG][RADIO] Audio generated: {filename} at {audio_path}. ({time.time() - tts_start:.2f}s)")

    # 4. URL生成 (Renderまたはngrokのホスト名を使用)
    audio_url = f"https://{RENDER_HOSTNAME}/audio/{filename}"
    print(f"[DEBUG][RADIO] Audio URL: {audio_url}")

    # 5. LINE送信
    print(f"[DEBUG][RADIO] Sending audio and URLs to LINE...")
    send_audio_message(user_id, audio_url, articles, time_of_day_label)

def send_audio_message(user_id, audio_url, articles, time_of_day_label):
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}", "Content-Type": "application/json"}
    
    # 記事のURLリストを作成
    url_list_text = f"📖 {time_of_day_label}のニュース記事一覧：\n\n"
    for i, a in enumerate(articles, 1):
        url_list_text += f"{i}. {a.get('title')}\n{a.get('url')}\n\n"

    data = {
        "to": user_id,
        "messages": [
            {"type": "text", "text": f"🎧 {time_of_day_label}のパーソナライズニュースラジオです。"},
            {"type": "audio", "originalContentUrl": audio_url, "duration": 600000}, # 最大10分 (600,000ms)
            {"type": "text", "text": url_list_text.strip()}
        ]
    }
    res = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data)
    print(f"[DEBUG][RADIO] LINE API Response: {res.status_code}")

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