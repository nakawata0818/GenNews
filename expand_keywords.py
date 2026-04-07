# expand_keywords.py

SYNONYMS = {
    "AI": ["人工知能", "LLM", "ChatGPT", "生成AI"],
    "経済": ["景気", "金融", "市場", "株価"],
    "健康": ["ウェルビーイング", "医学", "ダイエット"],
    "テクノロジー": ["IT", "テック", "ガジェット"]
}

def expand_keywords(keywords):
    """
    入力されたキーワードリストに類義語を追加して返す
    """
    expanded = set(keywords)
    for kw in keywords:
        if kw in SYNONYMS:
            expanded.update(SYNONYMS[kw])
    return list(expanded)