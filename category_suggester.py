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