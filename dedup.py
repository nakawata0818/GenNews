import re
from typing import List, Dict

NG_WORDS = ["PR", "広告", "まとめ", "速報", "アフィリエイト"]

def is_valid(title: str) -> bool:
    return not any(word in title for word in NG_WORDS)

def normalize_title(title: str) -> str:
    # 小文字化・記号除去

    return re.sub(r'[^\w\s]', '', title.lower())

def deduplicate_articles(articles: List[Dict]) -> List[Dict]:
    seen = set()
    unique_articles = []
    for article in articles:
        title = article['title']
        if not is_valid(title):
            continue
        norm_title = normalize_title(title)
        if any(norm_title in s or s in norm_title for s in seen):
            continue
        seen.add(norm_title)
        unique_articles.append(article)
    return unique_articles

if __name__ == "__main__":
    # テスト用
    test = [
        {'title': 'AIが進化', 'url': 'a'},
        {'title': 'AIが進化!', 'url': 'b'},
        {'title': '経済ニュース', 'url': 'c'},
        {'title': '【PR】新商品', 'url': 'd'},
        {'title': '速報：事件発生', 'url': 'e'}
    ]
    print(deduplicate_articles(test))
