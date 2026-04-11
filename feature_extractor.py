# feature_extractor.py

def extract_features(article):
    """
    記事からキーワードとカテゴリを抽出する（ルールベース）
    """
    title = article.get('title', '')
    summary = article.get('summary', '')
    text = title + " " + summary

    # キーワード抽出 (簡易版: 記事タイトル/要約に含まれる特定の単語をキーワードとして抽出)
    extracted_keywords = []
    if "AI" in text or "人工知能" in text:
        extracted_keywords.append("AI")
    if "LLM" in text or "ChatGPT" in text:
        extracted_keywords.append("LLM")
    if "経済" in text or "金融" in text or "市場" in text or "株価" in text:
        extracted_keywords.append("経済")
    if "テクノロジー" in text or "テック" in text or "ガジェット" in text:
        extracted_keywords.append("テクノロジー")
    if "健康" in text or "医療" in text or "医学" in text or "ダイエット" in text:
        extracted_keywords.append("健康")

    # カテゴリ分類（ルールベース）
    category = "その他"
    if any(word in text for word in ["技術", "開発", "LLM", "AI", "テクノロジー", "テック", "ガジェット"]):
        category = "技術"
    elif any(word in text for word in ["企業", "市場", "投資", "経済", "金融", "ビジネス", "株価", "経営", "起業", "財政"]):
        category = "ビジネス"
    elif any(word in text for word in ["健康", "医療", "医学", "ダイエット", "ウェルビーイング", "ヘルスケア", "介護", "認知症", "病院"]):
        category = "ヘルスケア"
    elif any(word in text for word in ["政治", "政府", "選挙", "外交", "政権", "国会"]):
        category = "政治"
    elif any(word in text for word in ["社会", "環境", "災害", "教育", "地域", "横浜", "事件", "事故"]):
        category = "社会"
    elif any(word in text for word in ["エンタメ", "映画", "音楽", "芸能"]):
        category = "エンタメ"
    elif any(word in text for word in ["スポーツ", "野球", "サッカー", "プロ野球", "ベイスターズ", "DeNA", "五輪"]):
        category = "スポーツ"
    
    return {
        "keywords": list(set(extracted_keywords)), # 重複排除
        "category": category
    }