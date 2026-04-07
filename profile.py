# profile.py
from sheet_utils import get_sheet_by_name
from datetime import datetime, timedelta, timezone

def generate_user_profile(user_id):
    """
    ユーザーの行動ログからプロファイルを生成する
    直近7日間のログを集計
    """
    article_log_sheet = get_sheet_by_name('article_log')
    records = article_log_sheet.get_all_records()

    # 直近7日間のログをフィルタリング
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_logs = [
        r for r in records
        if r.get('user_id') == user_id and
           datetime.fromisoformat(r.get('timestamp').replace('Z', '+00:00')) >= seven_days_ago
    ]

    keyword_counts = {}
    category_counts = {}

    for log in recent_logs:
        # keywordはカンマ区切りで保存されている可能性があるので分割
        keywords_in_log = [kw.strip() for kw in log.get('keyword', '').split(',') if kw.strip()]
        for kw in keywords_in_log:
            keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
        
        category = log.get('category')
        if category:
            category_counts[category] = category_counts.get(category, 0) + 1
    
    return {
        "keywords": keyword_counts,
        "categories": category_counts
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