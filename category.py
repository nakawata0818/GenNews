# category.py
from category_suggester import suggest_category
from sheet_utils import get_category_map, save_category_mapping

NORMALIZE_MAP = {
    "テクノロジー": "技術",
    "IT": "技術",
    "医療": "ヘルスケア",
    "ヘルス": "ヘルスケア",
    "健康": "ヘルスケア",
    "医学": "ヘルスケア",
    "ウェルビーイング": "ヘルスケア",
    "介護": "ヘルスケア",
    "野球": "スポーツ",
    "サッカー": "スポーツ",
    "地域": "社会",
    "地方": "社会",
    "行政": "政治",
    "マネー": "ビジネス"
}

INITIAL_CATEGORIES = {
    "認知症予兆": "ヘルスケア",
    "軽度認知症": "ヘルスケア",
    "認知症診断": "ヘルスケア",
    "LLM": "技術",
    "データ利活用": "技術",
    "ドライバーモニタリングシステムCANDy判定": "技術"
}

def normalize_category(cat):
    return NORMALIZE_MAP.get(cat, cat)

def get_category(keyword):
    # 1. 初期定義チェック
    if keyword in INITIAL_CATEGORIES:
        return INITIAL_CATEGORIES[keyword]

    # 2. category_map シート確認
    cat_map = get_category_map()
    if keyword in cat_map:
        return cat_map[keyword]

    # 3. AIで推定して正規化
    suggested = suggest_category(keyword)
    normalized = normalize_category(suggested)

    # 4. シートに保存
    save_category_mapping(keyword, normalized)
    return normalized

def recategorize_user_keywords(user_id):
    """ユーザーの全キーワードを再カテゴライズする"""
    from category_suggester import suggest_categories_batch
    from sheet_utils import get_user_keywords, save_category_mapping
    
    user_kws = get_user_keywords(user_id)
    if not user_kws:
        return
    
    kw_names = [kw for kw, weight in user_kws]
    # LLMでまとめてカテゴライズ
    mapping = suggest_categories_batch(kw_names)
    
    for kw, cat in mapping.items():
        save_category_mapping(kw, normalize_category(cat))