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

def get_models_to_try(client):
    """動的にモデルリストを取得し最新順にソートする（キャッシュ利用）"""
    global _DYNAMIC_MODELS_CACHE
    if not _DYNAMIC_MODELS_CACHE:
        try:
            discovered_models = []
            for m in client.models.list():
                # 'gemini' を含み、かつテキスト生成が可能なモデルのみを抽出
                name_lower = m.name.lower()
                if 'generateContent' in m.supported_actions and \
                   'gemini' in name_lower and \
                   not any(x in name_lower for x in ['robotics', 'vision', 'image']):
                    discovered_models.append(m.name)
            
            # 文字列の降順ソートにより、gemini-2.0 > gemini-1.5 のように最新モデルを優先する
            discovered_models.sort(reverse=True)
            _DYNAMIC_MODELS_CACHE = discovered_models
            print(f"[INFO] Dynamically discovered models (latest first): {_DYNAMIC_MODELS_CACHE}")
        except Exception as e:
            print(f"[Error] Failed to fetch models dynamically: {e}")
            # APIからの取得に失敗した場合のフォールバック
            _DYNAMIC_MODELS_CACHE = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']
    return _DYNAMIC_MODELS_CACHE

def generate_content_with_retry(client, contents):
    """モデルローテーションとリトライを伴う生成処理"""
    models_to_try = get_models_to_try(client)

    for model_name in models_to_try:
        if model_name in _DISABLED_MODELS:
            continue

        for i in range(5):  # 各モデルにつき最大5回リトライ
            try:
                response = client.models.generate_content(
                    model=model_name, contents=contents)
                return response.text.strip()
            except Exception as e:
                error_msg = str(e)
                print(f"[summarize_gemini error] model={model_name} attempt {i+1}: {e}")

                # 制限に達した(429)や存在しない(404)場合は、今回の実行ではこのモデルをスキップ対象にする
                if any(x in error_msg for x in ["429", "RESOURCE_EXHAUSTED", "404", "NOT_FOUND"]):
                    print(f"[INFO] {model_name} が利用不可（制限または未存在）なため、以降の配信ではスキップします。")
                    _DISABLED_MODELS.add(model_name)
                    break
                
                # 一時的な負荷(503)などの場合は指数バックオフで待機
                if "503" in error_msg or "high demand" in error_msg.lower():
                    time.sleep(2 ** i)
                    continue
                break
    return None

def summarize_article(title: str, summary: str, existing_related_keywords: list = None) -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # 既存のキーワードがある場合の追加命令を構築
    extra_instruction = ""
    if existing_related_keywords:
        kw_list_str = ", ".join(existing_related_keywords)
        extra_instruction = f"\n# 既存の関連キーワードリスト\n{kw_list_str}\n\n# 抽出時の追加条件\n・既存のリストに似た意味の単語がある場合は、新しく作らずに既存の単語を優先して使用してください。\n・表記揺れ（例：ChatGPTとチャットGPTなど）を防ぎ、一貫性を保ってください。"

    content = f"タイトル: {title}\n内容: {summary}"
    
    res_text = generate_content_with_retry(client, PROMPT + extra_instruction + "\n" + content)
    if res_text:
        return res_text

    # すべてのモデルが失敗した場合のフォールバック
    print(f"[WARN] All Gemini models failed for: {title}. Returning original snippet.")
    fallback_text = f"【要約制限中】\n{summary[:200]}..."
    return f"{fallback_text}\n\n【キーワード】\n(自動抽出停止中)"

if __name__ == "__main__":
    print(summarize_article("AIが進化", "AI技術が急速に発展しています。"))
