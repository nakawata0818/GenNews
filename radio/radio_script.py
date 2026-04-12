import os
from google import genai
from config import GEMINI_API_KEY
from summarize_gemini import generate_content_with_retry, cleanup_llm_output

def generate_radio_script(articles, time_of_day_label):
    """記事リストをラジオ用台本に変換する"""
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    article_text = ""
    # すべての記事を台本に含める
    for a in articles:
        article_text += f"カテゴリ: {a.get('category', '一般')}\nタイトル: {a.get('title')}\n内容: {a.get('summary')}\n\n"

    prompt = f"""
あなたはベテランのラジオニュースキャスターです。
以下のニュース記事を、リスナーが家事や通勤をしながらでも内容を理解できるよう、自然で聞き取りやすい日本語のラジオ台本に整形してください。
冒頭の挨拶は「{time_of_day_label}のニュースをお知らせします」というフレーズを必ず含めてください。

# 条件
・カテゴリごとに区切って紹介する
・各記事の要点を分かりやすく話す
・最後に短いまとめと「それでは、良い一日をお過ごしください」といった締めの言葉を入れる
・事実に基づき、読み上げやすい文章（句読点の位置など）にする
・「アスタリスク」などの記号は一切含めず、純粋な話し言葉のみを出力してください
・返答の冒頭に「承知しました」などの挨拶は不要です。台本の本文から始めてください。

# ニュース記事データ
{article_text}
"""
    
    res_text = generate_content_with_retry(client, prompt)
    if res_text:
        return cleanup_llm_output(res_text)
    return "本日のニュースをお届けします。申し訳ありません。台本の生成に失敗しました。"