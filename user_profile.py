# user_profile.py
from sheet_utils import get_sheet_by_name
from datetime import datetime, timedelta, timezone

def generate_user_profile(user_id):
    """
    ユーザーの行動ログからプロファイルを生成する
    直近7日間のログを集計
    """
    article_log_sheet = get_sheet_by_name('article_log')
    records = article_log_sheet.get_all_records()

    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    
    recent_logs = []
    for r in records:
        try:
            if str(r.get('user_id', '')).strip() == str(user_id).strip() and r.get('timestamp'):
                ts = datetime.fromisoformat(r.get('timestamp').replace('Z', '+00:00'))
                r['_dt'] = ts # 計算用に保持
                if ts >= seven_days_ago:
                    recent_logs.append(r)
        except Exception:
            continue

    keyword_counts = {}
    category_counts = {}
    liked_keywords = set()
    disliked_keywords = set()
    negative_scores = {} # keyword -> score (with decay)

    for log in recent_logs:
        keywords_in_log = [kw.strip() for kw in log.get('keyword', '').split(',') if kw.strip()]
        action = log.get('action')
        
        for kw in keywords_in_log:
            keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
            if action == "like":
                liked_keywords.add(kw)
            elif action == "dislike":
                disliked_keywords.add(kw)
                # ネガティブスコア計算 (0.9^経過日数 で減衰)
                days_passed = (now - log['_dt']).days
                decayed_val = 1.0 * (0.9 ** days_passed)
                negative_scores[kw] = negative_scores.get(kw, 0.0) + decayed_val
        
        category = log.get('category')
        if category:
            category_counts[category] = category_counts.get(category, 0) + 1
    
    return {
        "user_id": user_id,
        "keywords": keyword_counts,
        "categories": category_counts,
        "liked_keywords": liked_keywords,
        "disliked_keywords": disliked_keywords,
        "negative_scores": negative_scores,
        "raw_logs": [r for r in records if str(r.get('user_id', '')).strip() == str(user_id).strip()]
    }

def generate_profile_summary(profile):
    """
    ユーザープロファイルから説明文を生成する
    """
    summary_lines = ["📊 あなたの興味傾向（直近7日）\n"]

    # キーワード傾向
    if profile["keywords"]:
        sorted_keywords = sorted(profile["keywords"].items(), key=lambda item: item[1], reverse=True)
        top_keyword, top_keyword_count = sorted_keywords[0]
        summary_lines.append(f"・{top_keyword}関連の記事への反応が多いです（{top_keyword_count}件）")
    
    # カテゴリ傾向
    if profile["categories"]:
        sorted_categories = sorted(profile["categories"].items(), key=lambda item: item[1], reverse=True)
        top_category, top_category_count = sorted_categories[0]
        summary_lines.append(f"・特に{top_category}系の記事が多く選ばれています（{top_category_count}件）")
    
    if not profile["keywords"] and not profile["categories"]:
        summary_lines.append("まだ十分な行動ログがありません。ニュースを評価すると傾向が分かります。")
    else:
        summary_lines.append("\nこの傾向をもとに配信しています")

    return "\n".join(summary_lines)