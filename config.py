import os
from dotenv import load_dotenv

load_dotenv()


OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

# ニュース取得キーワード
import json
with open(os.path.join(os.path.dirname(__file__), 'keywords.json'), encoding='utf-8') as f:
    KEYWORDS = json.load(f)
