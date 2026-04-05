import feedparser
import requests
from typing import List, Dict
from config import KEYWORDS

def fetch_rss_articles(keywords: List[str]) -> List[Dict]:
    articles = []
    for keyword in keywords:
        url = f"https://news.google.com/rss/search?q={keyword}&hl=ja&gl=JP&ceid=JP:ja"
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
