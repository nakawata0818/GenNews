import time
from google import genai
from config import GEMINI_API_KEY

# クォータ制限や存在しないモデルを一時的に記録して、今回の実行（プロセス内）で再試行しないようにする
_DISABLED_MODELS = set()

# 利用可能なモデルのキャッシュ
_DYNAMIC_MODELS_CACHE = []

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

def list_available_models():
    """利用可能なモデル一覧を表示する（デバッグ用）"""
    client = genai.Client(api_key=GEMINI_API_KEY)
    print("利用可能なモデル一覧:")
    for model in client.models.list():
        if 'generateContent' in model.supported_actions:
            print(f"Name: {model.name}, Display: {model.display_name}")

def summarize_article(title: str, summary: str) -> str:
    global _DYNAMIC_MODELS_CACHE
    client = genai.Client(api_key=GEMINI_API_KEY)
    content = f"タイトル: {title}\n内容: {summary}"

    # 初回呼び出し時に動的にモデルリストを取得して最新順にソート
    if not _DYNAMIC_MODELS_CACHE:
        try:
            discovered_models = []
            for m in client.models.list():
                if 'generateContent' in m.supported_actions:
                    # 'models/' プレフィックスを削除して名前を統一
                    clean_name = m.name.replace('models/', '')
                    discovered_models.append(clean_name)
            
            # 文字列の降順ソートにより、gemini-2.0 > gemini-1.5 のように最新モデルを優先する
            discovered_models.sort(reverse=True)
            _DYNAMIC_MODELS_CACHE = discovered_models
            print(f"[INFO] Dynamically discovered models (latest first): {_DYNAMIC_MODELS_CACHE}")
        except Exception as e:
            print(f"[Error] Failed to fetch models dynamically: {e}")
            # APIからの取得に失敗した場合のフォールバック
            _DYNAMIC_MODELS_CACHE = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']

    models_to_try = _DYNAMIC_MODELS_CACHE

    for model_name in models_to_try:
        if model_name in _DISABLED_MODELS:
            continue

        for i in range(5):  # 各モデルにつき最大5回リトライ
            try:
                response = client.models.generate_content(
                    model=model_name, contents=PROMPT + "\n" + content)
                return response.text.strip()
            except Exception as e:
                error_msg = str(e)
                print(f"[summarize_gemini error] model={model_name} attempt {i+1}: {e}")

                # 制限に達した(429)や存在しない(404)場合は、今回の実行ではこのモデルをスキップ対象にする
                if any(x in error_msg for x in ["429", "RESOURCE_EXHAUSTED", "404", "NOT_FOUND"]):
                    print(f"[INFO] {model_name} が利用不可（制限または未存在）なため、以降の配信ではスキップします。")
                    _DISABLED_MODELS.add(model_name)
                    break
                
                # 一時的な負荷(503)などの場合は指数バックオフでリトライ
                if "503" in error_msg or "high demand" in error_msg.lower():
                    time.sleep(2 ** i)
                    continue
                break
    return "要約に失敗しました。"

if __name__ == "__main__":
    print(summarize_article("AIが進化", "AI技術が急速に発展しています。"))
