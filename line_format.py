# line_format.py

def create_news_bubble(article, article_id_for_log=None, category_for_log=None):
    """記事1件分のFlex Message Bubbleを生成"""
    title = article.get('title', 'No Title')
    summary = article.get('summary', 'No Summary')
    # HTMLタグの簡易除去
    summary = summary.replace('<b>', '').replace('</b>', '').replace('<br>', '\n')
    if len(summary) > 100:
        summary = summary[:100] + "..."
    
    # フィールドが空だと400エラーになるための対策
    title = title if title.strip() else "No Title"
    summary = summary if summary.strip() else "No Summary"
    
    url = article.get('url', 'https://news.google.com')

    # 記事に関連したキーワードを抽出（postbackデータ用）
    # matched_kwsはsend_news.pyでarticleに設定される
    matched_kws = ",".join(article.get('matched_keywords', []))
    
    # article_idとcategoryはログ保存のために必要
    article_id = article_id_for_log if article_id_for_log else article.get('url') # URLをIDとして利用
    category = category_for_log if category_for_log else article.get('category', 'その他')

    return {
      "type": "bubble",
      "body": {
        "type": "box",
        "layout": "vertical",
        "contents": [
          {"type": "text", "text": title, "weight": "bold", "size": "xl", "wrap": True},
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
                "action": {"type": "postback", "label": "👍 いいね", "data": f"action=like&article_id={article_id}&kws={matched_kws}&category={category}"}
              },
              {
                "type": "button",
                "style": "secondary",
                "height": "sm",
                "action": {"type": "postback", "label": "👎 興味なし", "data": f"action=dislike&article_id={article_id}&kws={matched_kws}&category={category}"}
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

def create_carousel(articles):
    """記事リストをカルーセル形式のFlex Messageに変換"""
    bubbles = [create_news_bubble(a) for a in articles[:10]] # 最大10件
    if not bubbles:
        return None
    return {
        "type": "flex",
        "altText": "本日の厳選ニュースをお届けします",
        "contents": {
            "type": "carousel",
            "contents": bubbles
        }
    }