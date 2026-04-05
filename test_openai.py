import os
import openai
from dotenv import load_dotenv

load_dotenv()  # .env 読み込み

api_key = os.getenv("OPENAI_API_KEY")
print("APIキー:", api_key[:8] + "...")  # 確認用

openai.api_key = api_key

try:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user","content":"Hello"}],
        max_tokens=10
    )
    print("API呼び出し成功:", response.choices[0].message.content)
except Exception as e:
    print("API呼び出しエラー:", e)