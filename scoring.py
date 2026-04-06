# scoring.py
# ニュース記事のスコアリング関数

def score_news(article, user_keywords):
    """
    記事とユーザーのキーワードリスト（(keyword, weight)）からスコアを計算
    article: {'id', 'title', 'summary', ...}
    user_keywords: [(keyword, weight), ...]
    return: float
    """
    score = 0.0
    title = article.get('title', '')
    summary = article.get('summary', '')
    for keyword, weight in user_keywords:
        # キーワードがタイトルまたは要約に含まれていれば加点
        if keyword and (keyword in title or keyword in summary):
            score += weight
    return score
