import os
import time
import random
import requests
from sheet_utils import get_user_keywords, get_all_user_ids, get_sent_article_ids, save_sent_articles, save_article_log, get_sheet_by_name, save_exposure, calculate_exposure_score_from_logs, get_all_exposure_logs, promote_keywords, get_related_keywords
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

def select_311_articles(processed_list, sent_ids, user_logs):
    """
    指示書の3:1:1構成で記事を選定する
    processed_list: [(score, article), ...]
    """
    now = datetime.now(timezone.utc)
    
    # 評価済み記事（like/dislike）のURL
    feedback_urls = {l.get('article_id') for l in user_logs if l.get('action') in ['like', 'dislike']}
    # dislikeされたURLとその時間
    disliked_info = {l.get('article_id'): datetime.fromisoformat(l.get('timestamp').replace('Z', '+00:00')) 
                     for l in user_logs if l.get('action') == 'dislike'}

    # 1. おすすめ (Top 3) - 未送信のみ
    recommended_candidates = [(s, a) for s, a in processed_list if a['url'] not in sent_ids]
    recommended_candidates.sort(key=lambda x: x[0], reverse=True)
    liked = [a for s, a in recommended_candidates[:3]]
    for a in liked: a['delivery_label'] = "おすすめ"

    # 2. 探索 (1件) - フィードバックなし & 未送信
    explore_candidates = [a for s, a in processed_list if a['url'] not in sent_ids and a['url'] not in feedback_urls and a not in liked]
    explore = random.choice(explore_candidates) if explore_candidates else (random.choice([a for s, a in processed_list]) if processed_list else None)
    if explore: explore['delivery_label'] = "新しい視点"

    # 3. 再評価 (1件) - 過去dislike & 7日以上経過
    retry_candidates = []
    for s, a in processed_list:
        if a['url'] in disliked_info:
            if (now - disliked_info[a['url']]).days > 7:
                retry_candidates.append(a)
    
    retry = random.choice(retry_candidates) if retry_candidates else (random.choice([a for s, a in processed_list if a not in liked and a != explore]) if len(processed_list) > 4 else None)
    if retry: retry['delivery_label'] = "再チェック"

    return liked + ([explore] if explore else []) + ([retry] if retry else [])


def deliver_news_to_user(user_id):
    """特定のユーザーに対してニュース配信（3:1:1構成）を実行"""
    print(f"[DEBUG] Starting deliver_news_to_user for {user_id}")
    user_keywords = get_user_keywords(user_id)
    if not user_keywords:
        print(f"[DEBUG] No keywords found for {user_id}")
        return
    
    # 1. キーワードをカテゴリ別にグループ化
    cat_to_kws = {}
    for kw, w in user_keywords:
        cat = get_category(kw)
        if cat not in cat_to_kws: cat_to_kws[cat] = []
        cat_to_kws[cat].append((kw, w))
        
    print(f"[DEBUG] Categories identified: {list(cat_to_kws.keys())}")
    user_profile = generate_user_profile(user_id)
    # 関連キーワード情報をプロファイルに追加
    user_profile['related_keywords'] = get_related_keywords(user_id)
    sent_ids = get_sent_article_ids(user_id)
    exposure_logs = get_all_exposure_logs(user_id) # ここで一度だけ取得
    all_user_articles = []
    
    # 2. カテゴリごとに記事収集・構成
    for category, kws in cat_to_kws.items():
        print(f"[DEBUG] Fetching RSS for category: {category}")
        kw_names = [k for k, w in kws]
        articles = deduplicate_articles(fetch_rss_articles(kw_names))
        
        # スコアリングと特徴付与
        processed = []
        for a in articles:
            features = extract_features(a)
            a.update(features)
            # ユーザーの登録キーワードがタイトルか要約に含まれているか直接チェック
            a['matched_keywords'] = [
                k for k in kw_names 
                if k.lower() in a.get('title', '').lower() or k.lower() in a.get('summary', '').lower()
            ]
            # 高速化されたスコア計算（ログを渡す）
            score = score_article(a, kws, user_profile, exposure_func=lambda uid, kw: calculate_exposure_score_from_logs(exposure_logs, kw))
            processed.append((score, a))
        
        # 3:1:1構成で選定
        final_articles = select_311_articles(processed, sent_ids, user_profile.get("raw_logs", []))

        for a in final_articles:
            a['category'] = category
        all_user_articles.extend(final_articles)

    if not all_user_articles:
        print(f"[DEBUG] No new articles found for {user_id}")
        return

    # 既存の関連キーワードをリスト化して要約時に渡す準備
    existing_rel_kws = [rk.get('keyword') for rk in user_profile.get('related_keywords', [])]

    # まとめて要約
    print(f"[DEBUG] Summarizing {len(all_user_articles)} articles...")
    for a in all_user_articles:
        res = summarize_article(a['title'], a['summary'], existing_related_keywords=existing_rel_kws)
        if res and "【キーワード】" in res:
            parts = res.split("【キーワード】")
            a['summary'] = parts[0].strip()
            a['relevant_keywords'] = parts[1].strip()
        else:
            a['summary'] = res if res else ""
            a['relevant_keywords'] = ""
        time.sleep(1)

    print(f"[DEBUG] Sending {len(all_user_articles)} articles to LINE...")
    # まとめて送信 (LINEカルーセルの10件制限に従って分割送信)
    for i in range(0, len(all_user_articles), 10):
        chunk = all_user_articles[i:i+10]
        carousel = create_carousel(chunk)
        send_line_flex(user_id, carousel)

    # 露出の記録
    for a in all_user_articles:
        save_exposure(user_id, a.get('matched_keywords', []))

    # 保存処理
    current_urls = [a['url'] for a in all_user_articles]
    save_sent_articles(user_id, current_urls)
    for a in all_user_articles:
        save_article_log(user_id, a['url'], a['matched_keywords'], a['category'], 'send')
    
    # キーワード昇格判定
    promote_keywords(user_id)

def main():
    user_ids = get_all_user_ids()
    for user_id in user_ids:
        deliver_news_to_user(user_id)

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

    # 最適化：露出スコアと既存関連キーワードを一度に取得
    exposure_logs = get_all_exposure_logs(user_id)
    rel_kws_data = get_related_keywords(user_id)
    user_profile['related_keywords'] = rel_kws_data
    existing_rel_kws = [rk.get('keyword') for rk in rel_kws_data]

    scored = [(score_article(a, user_keywords, user_profile, exposure_func=lambda uid, kw: calculate_exposure_score_from_logs(exposure_logs, kw)), a) for a in processed_articles]
    scored.sort(reverse=True, key=lambda x: x[0])
    top5 = [a for _, a in scored[:5]]
    
    for article in top5:
        # 記事に関連するキーワードを記録
        title_text = article.get('title', '').lower()
        summary_text = article.get('summary', '').lower()
        article['matched_keywords'] = [
            kw for kw in keywords_only
            if kw.lower() in title_text or kw.lower() in summary_text
        ]
        res = summarize_article(article['title'], article['summary'], existing_related_keywords=existing_rel_kws)
        if "【キーワード】" in res:
            parts = res.split("【キーワード】")
            article['summary'] = parts[0].strip()
            article['relevant_keywords'] = parts[1].strip()
        else:
            article['summary'] = res
            article['relevant_keywords'] = ""
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
