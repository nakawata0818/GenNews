import requests
from config import LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID


def send_line_notify(title: str, summary: str, url: str) -> None:
    """1件だけ送りたい場合用（未使用）"""
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "text",
                "text": f"【{title}】\n{summary}\n\n続きを読む：\n{url}"
            }
        ]
    }
    try:
        response = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers=headers,
            json=data
        )
        print(f"[LINE] status: {response.status_code}")
        if response.status_code != 200:
            print(response.text)
    except Exception as e:
        print(f"[LINE error] {e}")

def send_line_digest(messages: list) -> None:
    """
    ニュースまとめを1通で送信
    messages: List of (title, summary, url)
    """
    if not messages:
        return
    text = f"【本日の厳選ニュース（{len(messages)}件）】\n\n"
    for i, (title, summary, url) in enumerate(messages, 1):
        text += f"{i}. {title}\n{summary}\n続きを読む：{url}\n\n"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "text",
                "text": text.strip()
            }
        ]
    }
    try:
        response = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers=headers,
            json=data
        )
        print(f"[LINE] status: {response.status_code}")
        if response.status_code != 200:
            print(response.text)
    except Exception as e:
        print(f"[LINE error] {e}")

if __name__ == "__main__":
    send_line_notify("テストタイトル", "要約テキスト", "https://example.com")
