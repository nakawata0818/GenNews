import os
import time
import requests
from sheet_utils import get_user_keywords, get_all_user_ids, get_sent_article_ids, save_sent_articles, save_article_log, get_sheet_by_name
from scoring import score_article
from rss import fetch_rss_articles
from dedup import deduplicate_articles
from summarize_gemini import summarize_article
from feature_extractor import extract_features
from profile import generate_user_profile # for more news category prioritization
from expand_keywords import expand_keywords
from category import get_category
from line_format import create_carousel
from config import LINE_CHANNEL_ACCESS_TOKEN
from datetime import datetime, timezone, timedelta

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
    user_ids = get_all_user_ids()
    for user_id in user_ids:
        user_keywords = get_user_keywords(user_id)
        if not user_keywords: continue
        
        # 1. キーワードをカテゴリ別にグループ化
        cat_to_kws = {}
        for kw, w in user_keywords:
            cat = get_category(kw)
            if cat not in cat_to_kws: cat_to_kws[cat] = []
            cat_to_kws[cat].append((kw, w))
            
        user_profile = generate_user_profile(user_id)
        sent_ids = get_sent_article_ids(user_id)
        all_user_articles = []
        
        # 2. カテゴリごとに記事収集・構成
        for category, kws in cat_to_kws.items():
            kw_names = [k for k, w in kws]
            articles = deduplicate_articles(fetch_rss_articles(kw_names))
            
            # スコアリングと特徴付与
            processed = []
            for a in articles:
                features = extract_features(a)
                a.update(features)
                a['matched_keywords'] = [k for k in a['keywords'] if k in kw_names]
                processed.append((score_article(a, kws, user_profile), a))
            
            processed.sort(key=lambda x: x[0], reverse=True)
            
            # --- 3:1:1 構成作成 ---
            # ① 好み (上位3件)
            liked = [a for s, a in processed if a['url'] not in sent_ids][:3]
            for a in liked: a['delivery_label'] = "おすすめ"

            # ② 未知 (低い重み or 未出現)
            explore = [a for s, a in processed if a['url'] not in sent_ids and a not in liked][-1:]
            for a in explore: a['delivery_label'] = "🆕 新しい視点"
            
            # ③ 再評価 (dislike履歴あり + 3日以上前)
            retry = [] # ロジック簡略化のため空リストを初期値に、実際はarticle_logから取得
            # TODO: 過去3日以上前のdislikeログから抽出
            for a in retry: a['delivery_label'] = "🔁 再チェック"

            final_articles = liked + explore + retry
            for a in final_articles:
                a['category'] = category
            all_user_articles.extend(final_articles)

        if not all_user_articles:
            continue

        # まとめて要約
        for a in all_user_articles:
            a['summary'] = summarize_article(a['title'], a['summary'])
            time.sleep(1)

        # まとめて送信 (LINEカルーセルの10件制限に従って分割送信)
        for i in range(0, len(all_user_articles), 10):
            chunk = all_user_articles[i:i+10]
            carousel = create_carousel(chunk)
            send_line_flex(user_id, carousel)

        # 保存処理
        current_urls = [a['url'] for a in all_user_articles]
        save_sent_articles(user_id, current_urls)
        for a in all_user_articles:
            save_article_log(user_id, a['url'], a['matched_keywords'], a['category'], 'send')

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
        carousel = create_carousel(top5)
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
