import os
import time
import requests
from sheet_utils import get_user_keywords, get_sheet, get_sent_article_ids, save_sent_articles
from scoring import score_news
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
        # 既存のキーワード列からキーワードリストを生成
        keywords = [k.strip() for k in row['KEYWORDS'].split(',') if k.strip()]
        if not keywords:
            continue
        # 記事取得
        articles = fetch_rss_articles(keywords)
        articles = deduplicate_articles(articles)
        # 既に送信済みの記事を除外
        sent_ids = get_sent_article_ids(user_id)
        articles = [a for a in articles if a['url'] not in sent_ids]
        # 上位3件
        messages = []
        for article in articles[:3]:
            summary = summarize_article(article['title'], article['summary'])
            messages.append((article['title'], summary, article['url']))
            time.sleep(1)
        send_line_digest(user_id, messages)
        # historyに保存
        save_sent_articles(user_id, [a['url'] for a in articles[:3]])

# 追加配信「もっと」用
def get_more_news(user_id):
    user_keywords = get_user_keywords(user_id)
    print(f"[DEBUG] get_more_news user_keywords: {user_keywords}")
    if not user_keywords:
        print(f"[DEBUG] get_more_news: user_keywords is empty for user_id={user_id}")
        return
    # キーワードごとに記事取得
    articles = []
    for kw_tuple in user_keywords:
        if isinstance(kw_tuple, (list, tuple)) and len(kw_tuple) >= 1:
            kw = kw_tuple[0]
            articles.extend(fetch_rss_articles([kw]))
    # 重複排除
    seen = set()
    unique_articles = []
    for a in articles:
        if a['url'] not in seen:
            unique_articles.append(a)
            seen.add(a['url'])
    # 既に送信済みの記事を除外
    sent_ids = get_sent_article_ids(user_id)
    filtered = [a for a in unique_articles if a['url'] not in sent_ids]
    # スコアリング
    scored = [(score_news(a, user_keywords), a) for a in filtered]
    scored.sort(reverse=True, key=lambda x: x[0])
    top5 = [a for _, a in scored[:5]]
    # 要約
    messages = []
    for article in top5:
        summary = summarize_article(article['title'], article['summary'])
        messages.append((article['title'], summary, article['url']))
        time.sleep(1)
    if messages:
        send_line_digest(user_id, messages)
        # historyに保存
        save_sent_articles(user_id, [a['url'] for a in top5])
    else:
        # 新しい記事がなければ通知
        from config import LINE_CHANNEL_ACCESS_TOKEN
        headers = {
            "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        data = {
            "to": user_id,
            "messages": [
                {
                    "type": "text",
                    "text": "新しいニュースはありません"
                }
            ]
        }
        try:
            import requests
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
    main()
