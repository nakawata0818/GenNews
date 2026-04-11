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

def score_article(article: Dict, user_keywords: List[Tuple[str, float]], user_profile: Dict = None, exposure_func=None) -> float:
    """
    指示書の計算式: score = (keyword_score * 0.4 + category_score * 0.3 + freshness_score * 0.2 + source_score * 0.1) - exposure_penalty + related_bonus
    article: {'title', 'summary', 'url', 'published', ...}
    user_keywords: [(keyword, weight), ...]
    """
    title = article.get('title', '')
    summary = article.get('summary', '')

    # 1. keyword_score
    kw_score = 0.0
    matched_keywords = []
    for keyword, weight in user_keywords:
        if keyword and (keyword in title or keyword in summary):
            kw_score += weight
            matched_keywords.append(keyword)

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

    # 5. フィードバック反映 & 露出制御 & 関連キーワード
    if user_profile:
        user_id = user_profile.get("user_id")
        
        # 露出ペナルティ (Section 7)
        if exposure_func and user_id:
            for kw in matched_keywords:
                e_score = exposure_func(user_id, kw)
                final_score -= (e_score * 0.2)

        # フィードバック反映 & Negative管理 (Section 3, 8)
        liked_kws = user_profile.get("liked_keywords", set())
        disliked_kws = user_profile.get("disliked_keywords", set())
        negative_scores = user_profile.get("negative_scores", {})

        for kw in matched_keywords:
            if kw in liked_kws: final_score += 0.5
            if kw in disliked_kws: final_score -= 0.7
            penalty = negative_scores.get(kw, 0.0)
            final_score -= (penalty * 0.3)
            
        # 関連キーワード加点 (Section 8)
        rel_kws = user_profile.get("related_keywords", [])
        for rk in rel_kws:
            rk_word = rk.get('keyword')
            if rk_word and (rk_word in title or rk_word in summary):
                final_score += float(rk.get('score', 0)) * 0.5

    return final_score

def score_news(article, user_keywords):
    """互換性維持用"""
    return score_article(article, user_keywords)
