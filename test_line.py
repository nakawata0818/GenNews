import requests
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

url = "https://api.line.me/v2/bot/message/push"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

data = {
    "to": USER_ID,
    "messages": [
        {
            "type": "text",
            "text": "GenNews テスト送信"
        }
    ]
}

response = requests.post(url, headers=headers, json=data)

print("status:", response.status_code)
print("body:", response.text)

print("TOKEN:", TOKEN[:10])
print("USER_ID:", USER_ID)
print("RESPONSE:", response.status_code)
print("DETAIL:", response.text)