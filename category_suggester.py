# category_suggester.py
import time
from google import genai
from config import GEMINI_API_KEY
from summarize_gemini import generate_content_with_retry

def suggest_category(keyword):
    """
    AIを使用してキーワードをカテゴリに分類する
    """
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
    以下のキーワードを1つの単語のカテゴリに分類してください。返答はカテゴリ名のみを返してください。
    例：
    サッカー→スポーツ
    AI→技術
    
    キーワード: {keyword}
    """
    result = generate_content_with_retry(client, prompt)
    if result:
        if "→" in result:
            result = result.split("→")[-1].strip()
        return result

    return "その他"

def suggest_categories_batch(keywords):
    """
    複数のキーワードを一度にカテゴライズする
    """
    if not keywords:
        return {}
    client = genai.Client(api_key=GEMINI_API_KEY)
    kw_list_str = "\n".join(keywords)
    prompt = f"""
    以下のキーワードリストを、それぞれ1つの単語のカテゴリに分類してください。
    結果は「キーワード: カテゴリ」の形式で1行ずつ返してください。
    
    例：
    AI: 技術
    
    キーワードリスト:
    {kw_list_str}
    """
    res_text = generate_content_with_retry(client, prompt)
    if res_text:
        mapping = {}
        for line in res_text.split('\n'):
            if ":" in line:
                k, v = line.split(":", 1)
                mapping[k.strip()] = v.strip()
        return mapping

    return {kw: "その他" for kw in keywords}