# line_format.py

def create_news_bubble(article):
    """記事1件分のFlex Message Bubbleを生成"""
    title = article.get('title', 'No Title')
    summary = article.get('summary', 'No Summary')
    delivery_label = article.get('delivery_label', '')
    category = article.get('category', 'その他')

    # HTMLタグの簡易除去
    summary = summary.replace('<b>', '').replace('</b>', '').replace('<br>', '\n')
    if len(summary) > 100:
        summary = summary[:100] + "..."
    
    # フィールドが空だと400エラーになるための対策
    prefix = f"【{category}】"
    if delivery_label:
        prefix += f"{delivery_label} "

    display_title = f"{prefix}{title}"
    title = display_title if display_title.strip() else "No Title"
    summary = summary if summary.strip() else "No Summary"
    
    url = article.get('url', 'https://news.google.com')
    # 記事に関連したキーワードを抽出（postbackデータ用）
    # 300文字制限対策としてキーワード文字列を50文字でカット
    matched_kws = ",".join(article.get('matched_keywords', []))[:50]
    
    # article_idとcategoryはログ保存のために必要
    article_id = article.get('url') # URLをIDとして利用
    category = article.get('category', 'その他')

    # LINE Postback data 300文字制限対策
    # 150文字では超過する可能性があるため、より安全な100文字に制限
    short_id = article_id[:100] if article_id else ""

    return {
      "type": "bubble",
      "body": {
        "type": "box",
        "layout": "vertical",
        "contents": [
          {"type": "text", "text": title, "weight": "bold", "size": "md", "wrap": True},
          {"type": "text", "text": summary, "size": "sm", "color": "#666666", "wrap": True, "margin": "md"}
        ]
      },
      "footer": {
        "type": "box",
        "layout": "vertical",
        "spacing": "sm",
        "contents": [
          {
            "type": "button",
            "style": "link",
            "height": "sm",
            # PostbackではURLを開けないため、確実に開くuriアクションに戻します
            "action": {"type": "uri", "label": "続きを読む", "uri": url}
          },
          {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [
              {
                "type": "button",
                "style": "secondary",
                "height": "sm",
                "action": {"type": "postback", "label": "👍 いいね", "data": f"action=like&article_id={short_id}&kws={matched_kws}&category={category}"}
              },
              {
                "type": "button",
                "style": "secondary",
                "height": "sm",
                "action": {"type": "postback", "label": "👎 興味なし", "data": f"action=dislike&article_id={short_id}&kws={matched_kws}&category={category}"}
              }
            ]
          },
          {
            "type": "button",
            "style": "primary",
            "height": "sm",
            "action": {"type": "postback", "label": "もっとニュースを見る", "data": "action=more"}
          }
        ]
      }
    }

def create_carousel(articles, category_name=None):
    """記事リストをカルーセル形式のFlex Messageに変換"""
    bubbles = [create_news_bubble(a) for a in articles[:10]]
    if not bubbles:
        return None
    alt_text = f"【{category_name}】ニュース" if category_name else "本日の厳選ニュース"
    return {
        "type": "flex",
        "altText": alt_text,
        "contents": {
            "type": "carousel",
            "contents": bubbles
        }
    }