import time
from google import genai
from config import GEMINI_API_KEY

PROMPT = """
以下の記事を日本語で要約してください。

# 条件
・重要なポイントを3つに整理
・結論を最初に書く
・事実ベースのみ（推測禁止）
・100〜150文字程度

# 出力形式
【結論】
...

【ポイント】
・...
・...
・...
"""

def summarize_article(title: str, summary: str) -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)
    content = f"タイトル: {title}\n内容: {summary}"
    
    for i in range(1):  # 最大3回リトライ
        try:
            response = client.models.generate_content(
                model='gemini-3-flash-preview', contents=PROMPT + "\n" + content)
            return response.text.strip()
        except Exception as e:
            print(f"[summarize_gemini error] attempt {i+1}: {e}")
            if "503" in str(e) or "high demand" in str(e).lower():
                time.sleep(2 ** i)  # 指数バックオフで待機
                continue
            break
    return "要約に失敗しました。"

if __name__ == "__main__":
    print(summarize_article("AIが進化", "AI技術が急速に発展しています。"))
