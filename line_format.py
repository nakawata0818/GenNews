# line_format.py

def create_news_bubble(article):
    """記事1件分のFlex Message Bubbleを生成"""
    title = article.get('title', 'No Title')
    summary = article.get('summary', 'No Summary')
    # HTMLタグの簡易除去
    summary = summary.replace('<b>', '').replace('</b>', '').replace('<br>', '\n')
    if len(summary) > 100:
        summary = summary[:100] + "..."
    
    url = article.get('url', 'https://news.google.com')

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
                "action": {"type": "postback", "label": "👍 いいね", "data": f"action=like&url={url}"}
              },
              {
                "type": "button",
                "style": "secondary",
                "height": "sm",
                "action": {"type": "postback", "label": "👎 興味なし", "data": f"action=dislike&url={url}"}
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