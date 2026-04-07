import os
import time
import requests
from sheet_utils import get_user_keywords, get_sheet, get_sent_article_ids, save_sent_articles
from scoring import score_article
from rss import fetch_rss_articles
from dedup import deduplicate_articles
from summarize_gemini import summarize_article
from feature_extractor import extract_features
from profile import generate_user_profile # for more news category prioritization
from expand_keywords import expand_keywords
from line_format import create_carousel
from config import LINE_CHANNEL_ACCESS_TOKEN

def send_line_flex(user_id, flex_json):
    """Flex MessageをLINEに送信"""
    if not flex_json:
        return
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "to": user_id,
        "messages": [flex_json]
    }
    try:
        response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data)
        print(f"[LINE Flex] status: {response.status_code}")
    except Exception as e:
        print(f"[LINE Flex error] {e}")

def send_line_digest(user_id, messages): # 既存互換用
    if not messages:
        return
    text = f"【本日の厳選ニュース（{len(messages)}件）】\n\n"
    for i, (title, summary, url) in enumerate(messages, 1):
        text += f"{i}. {title}\n{summary}\n続きを読む：{url}\n\n"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "to": user_id,
        "messages": [
            {
                "type": "text",
                "text": text.strip()
            }
        ]
    }
    try:
        response = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers=headers,
            json=data
        )
        print(f"[LINE] status: {response.status_code}")
        if response.status_code != 200:
            print(response.text)
    except Exception as e:
        print(f"[LINE error] {e}")


def main():
    sheet = get_sheet()
    records = sheet.get_all_records()
    for row in records:
        user_id = row['LINE_USER_ID']
        user_keywords = get_user_keywords(user_id)
        if not user_keywords:
            continue
        user_profile = generate_user_profile(user_id) # カテゴリ優先度のため
        
        keywords_only = [kw for kw, weight in user_keywords]
        articles = fetch_rss_articles(keywords_only)
        articles = deduplicate_articles(articles)
        
        # 既に送信済みの記事を除外
        sent_ids = get_sent_article_ids(user_id)
        filtered = [a for a in articles if a['url'] not in sent_ids]
        
        # スコアリングして上位3件
        # category_scoreのためにuser_profileを渡す
        scored = [(score_article(a, user_keywords, user_profile), a) for a in filtered]
        scored.sort(key=lambda x: x[0], reverse=True)
        top_articles = [a for _, a in scored[:3]]

        for article in top_articles:
            # 記事の特徴抽出
            features = extract_features(article)
            article['extracted_keywords'] = features['keywords']
            article['category'] = features['category']

            # 記事に関連するキーワードを記録
            article['matched_keywords'] = [
                kw for kw in article['extracted_keywords']
                if any(ukw == kw for ukw, _ in user_keywords) # ユーザーの登録キーワードとマッチ
            ]
            article['summary'] = summarize_article(article['title'], article['summary'])
            time.sleep(1)
        
        # Flex Message (カルーセル形式) を作成して送信
        carousel = create_carousel(top_articles, article_id_for_log=article.get('url'), category_for_log=article.get('category'))
        send_line_flex(user_id, carousel)

        # 記事ログ保存 (Flex Message送信後)
        for article in top_articles:
            save_article_log(user_id, article['url'], article['matched_keywords'], article['category'], 'send') # 'send'アクションを追加

        # historyに保存
        save_sent_articles(user_id, [a['url'] for a in top_articles])

# 追加配信「もっと」用
def get_more_news(user_id):
    user_keywords = get_user_keywords(user_id)
    print(f"[DEBUG] get_more_news user_keywords: {user_keywords}")
    if not user_keywords:
        print(f"[DEBUG] get_more_news: user_keywords is empty for user_id={user_id}")
        return
    
    user_profile = generate_user_profile(user_id)
    
    # 類義語展開
    keywords_only = [kw for kw, _ in user_keywords]
    expanded_keywords = expand_keywords(keywords_only)

    # 記事取得
    articles = []
    articles.extend(fetch_rss_articles(expanded_keywords))

    # 重複排除
    seen = set()
    unique_articles = []
    for a in articles:
        if a['url'] not in seen:
            unique_articles.append(a)
            seen.add(a['url'])

    # 既に送信済みの記事を除外
    sent_ids = get_sent_article_ids(user_id)
    filtered = [a for a in unique_articles if a['url'] not in sent_ids]
    
    # 記事の特徴抽出とスコアリング
    processed_articles = []
    for article in filtered:
        features = extract_features(article)
        article['extracted_keywords'] = features['keywords']
        article['category'] = features['category']
        processed_articles.append(article)

    scored = [(score_article(a, user_keywords, user_profile), a) for a in processed_articles]
    scored.sort(reverse=True, key=lambda x: x[0])
    top5 = [a for _, a in scored[:5]]
    
    for article in top5:
        # 記事に関連するキーワードを記録
        article['matched_keywords'] = [
            kw for kw in article['extracted_keywords']
            if any(ukw == kw for ukw, _ in user_keywords)
        ]
        article['summary'] = summarize_article(article['title'], article['summary'])
        time.sleep(1)

    if top5:
        carousel = create_carousel(top5, article_id_for_log=article.get('url'), category_for_log=article.get('category'))
        send_line_flex(user_id, carousel)
        # historyに保存
        save_sent_articles(user_id, [a['url'] for a in top5])
        # 記事ログ保存
        for article in top5:
            save_article_log(user_id, article['url'], article['matched_keywords'], article['category'], 'send')
    else:
        # 新しい記事がなければ通知
        from config import LINE_CHANNEL_ACCESS_TOKEN
        headers = {
            "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        data = {
            "to": user_id,
            "messages": [
                {
                    "type": "text",
                    "text": "新しいニュースはありません"
                }
            ]
        }
        try:
            import requests
            response = requests.post(
                "https://api.line.me/v2/bot/message/push",
                headers=headers,
                json=data
            )
            print(f"[LINE] status: {response.status_code}")
            if response.status_code != 200:
                print(response.text)
        except Exception as e:
            print(f"[LINE error] {e}")

if __name__ == "__main__":
    main()
