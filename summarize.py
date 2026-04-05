import openai
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

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
    content = f"タイトル: {title}\n内容: {summary}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": content}
            ],
            max_tokens=200,
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[summarize error] {e}")
        return "要約に失敗しました。"

if __name__ == "__main__":
    print(summarize_article("AIが進化", "AI技術が急速に発展しています。"))
