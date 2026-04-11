import feedparser
import requests
import urllib.parse
from typing import List, Dict
from config import KEYWORDS

def fetch_rss_articles(keywords: List[str]) -> List[Dict]:
    # 指示書に基づいた除外キーワードの設定
    EXCLUDE_QUERY = "-求人 -広告 -PR -まとめ -ランキング"
    articles = []
    for keyword in keywords:
        # キーワードと除外条件を組み合わせてURLエンコード
        query = f"{keyword} {EXCLUDE_QUERY}"
        encoded_query = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ja&gl=JP&ceid=JP:ja"
        feed = feedparser.parse(url)
        for entry in feed.entries:
            articles.append({
                'title': entry.title,
                'url': entry.link,
                'summary': entry.summary if 'summary' in entry else '',
                'published': entry.published if 'published' in entry else ''
            })
    return articles

if __name__ == "__main__":
    articles = fetch_rss_articles(KEYWORDS)
    for a in articles[:5]:
        print(a['title'], a['url'])
