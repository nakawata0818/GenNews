# scoring.py
# 精度強化版スコアリング関数

from typing import List, Dict, Tuple
from datetime import datetime, timezone
import re

SOURCE_SCORES = {
    "NHK": 1.0,
    "Reuters": 1.0,
    "ロイター": 1.0,
    "日経": 1.0,
    "その他": 0.7
}

def score_article(article: Dict, user_keywords: List[Tuple[str, float]], user_profile: Dict = None) -> float:
    """
    指示書の計算式: score = (keyword_score * 0.4 + category_score * 0.3 + freshness_score * 0.2 + source_score * 0.1)
    article: {'title', 'summary', 'url', 'published', ...}
    user_keywords: [(keyword, weight), ...]
    """
    title = article.get('title', '')
    summary = article.get('summary', '')
    
    # 1. keyword_score
    kw_score = 0.0
    for keyword, weight in user_keywords:
        if keyword and (keyword in title or keyword in summary):
            kw_score += weight

    # 2. freshness_score
    # RSSのpublished文字列を解析（簡易実装）
    freshness = 0.3
    try:
        # Google News RSS format: "Tue, 07 Apr 2026 14:33:25 GMT"
        pub_date = datetime.strptime(article.get('published', ''), '%a, %d %b %Y %H:%M:%S %Z')
        pub_date = pub_date.replace(tzinfo=timezone.utc)
        diff_hours = (datetime.now(timezone.utc) - pub_date).total_seconds() / 3600
        if diff_hours <= 24:
            freshness = 1.0
        elif diff_hours <= 48:
            freshness = 0.7
    except Exception:
        freshness = 0.5

    # 3. source_score
    # タイトルの最後にあるソース名を抽出 (例: "タイトル - NHKニュース")
    source_val = 0.7
    source_match = re.search(r" - ([^-]+)$", title)
    if source_match:
        source_name = source_match.group(1).strip()
        source_val = SOURCE_SCORES.get(source_name, SOURCE_SCORES["その他"])

    # 4. category_score
    category_score = 0.0
    if user_profile and article.get('category'):
        # user_profile["categories"]は{'技術': 12, 'ビジネス': 3}のような形式
        # 記事のカテゴリがユーザープロファイルにある場合、そのカウントをスコアに反映
        # カウントをそのまま使うと大きくなりすぎる可能性があるので、正規化するか、上限を設ける
        category_score = user_profile["categories"].get(article['category'], 0)
        # 例: 最大10件で1.0、それ以上は1.0
        category_score = min(1.0, category_score / 10.0)

    final_score = (kw_score * 0.4) + (category_score * 0.3) + (freshness * 0.2) + (source_val * 0.1)
    return final_score

def score_news(article, user_keywords):
    """互換性維持用"""
    return score_article(article, user_keywords)
