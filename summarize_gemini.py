import time
from google import genai
from config import GEMINI_API_KEY

PROMPT = """
以下の記事を日本語で要約し、関連するキーワードを抽出してください。

# 条件
・重要なポイントを3つに整理
・結論を最初に書く
・事実ベースのみ（推測禁止）
・要約は300〜400文字程度
・関連キーワードは記事内容を象徴する単語を3〜5個抽出

# 出力形式
【結論】
...

【ポイント】
・...
・...
・...

【キーワード】
キーワード1, キーワード2, キーワード3
"""

def summarize_article(title: str, summary: str) -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)
    content = f"タイトル: {title}\n内容: {summary}"

    # 試行するモデルの優先順位リスト
    models_to_try = ['gemini-3-flash-lite-preview','gemini-3-flash-pro-preview','gemini-3-flash-preview',"gemini-2.5-flash-lite", 'gemini-1.5-flash']

    for model_name in models_to_try:
        for i in range(5):  # 各モデルにつき最大5回リトライ
            try:
                response = client.models.generate_content(
                    model=model_name, contents=PROMPT + "\n" + content)
                return response.text.strip()
            except Exception as e:
                error_msg = str(e)
                print(f"[summarize_gemini error] model={model_name} attempt {i+1}: {e}")

                # 制限に達した(429)場合は、ループを抜けて次のモデルを試す
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    print(f"[INFO] {model_name} の制限に達したため、次のモデルに切り替えます。")
                    break
                
                # 一時的な負荷(503)などの場合は指数バックオフでリトライ
                if "503" in error_msg or "high demand" in error_msg.lower():
                    time.sleep(2 ** i)
                    continue
                break
    return "要約に失敗しました。"

if __name__ == "__main__":
    print(summarize_article("AIが進化", "AI技術が急速に発展しています。"))
