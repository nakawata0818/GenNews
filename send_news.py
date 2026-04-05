import os
import time
import requests
from sheet_utils import get_user_keywords, get_sheet
from rss import fetch_rss_articles
from dedup import deduplicate_articles
from summarize_gemini import summarize_article
from config import LINE_CHANNEL_ACCESS_TOKEN

def send_line_digest(user_id, messages):
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
        "to": user_id,
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

def main():
    sheet = get_sheet()
    records = sheet.get_all_records()
    for row in records:
        user_id = row['LINE_USER_ID']
        keywords = [k.strip() for k in row['KEYWORDS'].split(',') if k.strip()]
        if not keywords:
            continue
        articles = fetch_rss_articles(keywords)
        articles = deduplicate_articles(articles)[:3]
        messages = []
        for article in articles:
            summary = summarize_article(article['title'], article['summary'])
            messages.append((article['title'], summary, article['url']))
            time.sleep(1)
        send_line_digest(user_id, messages)

if __name__ == "__main__":
    main()
