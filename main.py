from rss import fetch_rss_articles
from dedup import deduplicate_articles
from summarize_gemini import summarize_article
from notifier import send_line_notify
from config import KEYWORDS

import time

def main():
    print("[START] ニュースBot実行")
    try:
        # 1. RSS取得
        articles = fetch_rss_articles(KEYWORDS)
        print(f"[INFO] 記事取得: {len(articles)}件")
        # 2. 重複排除
        articles = deduplicate_articles(articles)
        print(f"[INFO] 重複排除後: {len(articles)}件")
        # 3. 上位3件抽出
        articles = articles[:3]
        # 4. 要約＋LINE送信（まとめて送信）
        messages = []
        for article in articles:
            summary = summarize_article(article['title'], article['summary'])
            messages.append((article['title'], summary, article['url']))
            time.sleep(1)  # API制限対策
        from notifier import send_line_digest
        send_line_digest(messages)
    except Exception as e:
        print(f"[main error] {e}")
    print("[END] ニュースBot実行")

if __name__ == "__main__":
    main()
