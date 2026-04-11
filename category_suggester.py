# category_suggester.py
import time
from google import genai
from config import GEMINI_API_KEY

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
    
    for i in range(3):
        try:
            response = client.models.generate_content(
                model='gemini-1.5-flash', contents=prompt)
            result = response.text.strip()
            if "→" in result:
                result = result.split("→")[-1].strip()
            return result
        except Exception as e:
            print(f"[category_suggester error] {e}")
            time.sleep(1)
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
    for i in range(3):
        try:
            response = client.models.generate_content(
                model='gemini-1.5-flash', contents=prompt)
            mapping = {}
            for line in response.text.strip().split('\n'):
                if ":" in line:
                    k, v = line.split(":", 1)
                    mapping[k.strip()] = v.strip()
            return mapping
        except Exception:
            time.sleep(1)
    return {kw: "その他" for kw in keywords}