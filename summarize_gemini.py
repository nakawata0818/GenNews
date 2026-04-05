import google.generativeai as genai
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
    genai.configure(api_key=GEMINI_API_KEY)
    content = f"タイトル: {title}\n内容: {summary}"
    try:
        model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')
        response = model.generate_content(PROMPT + "\n" + content)
        return response.text.strip()
    except Exception as e:
        print(f"[summarize_gemini error] {e}")
        return "要約に失敗しました。"

if __name__ == "__main__":
    print(summarize_article("AIが進化", "AI技術が急速に発展しています。"))
