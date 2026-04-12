import os
from google import genai
from config import GEMINI_API_KEY
from summarize_gemini import generate_content_with_retry

def generate_radio_script(articles):
    """記事リストをラジオ用台本に変換する"""
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    article_text = ""
    # 記事が多すぎる場合は上位7件程度に絞る
    for a in articles[:7]:
        article_text += f"カテゴリ: {a.get('category', '一般')}\nタイトル: {a.get('title')}\n内容: {a.get('summary')}\n\n"

    prompt = f"""
あなたはベテランのラジオニュースキャスターです。
以下のニュース記事を、リスナーが家事や通勤をしながらでも内容を理解できるよう、自然で聞き取りやすい日本語のラジオ台本に整形してください。

# 条件
・冒頭に「おはようございます。本日のニュースラジオです」といった挨拶を入れる
・カテゴリごとに区切って紹介する
・各記事の要点を分かりやすく話す
・最後に短いまとめと「それでは、良い一日をお過ごしください」といった締めの言葉を入れる
・全体で1200文字以内、話した時に60〜90秒程度になる量にする
・事実に基づき、読み上げやすい文章（句読点の位置など）にする

# ニュース記事データ
{article_text}
"""
    
    res_text = generate_content_with_retry(client, prompt)
    if res_text:
        return res_text
    return "本日のニュースをお届けします。申し訳ありません。台本の生成に失敗しました。"