import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 設定

from config import GOOGLE_SHEETS_CRED_JSON, SHEET_NAME

# Google Sheets 認証
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SHEETS_CRED_JSON, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1  # 1シート目を利用
print(sheet.get_all_values())  # シートの内容を表示
# テストデータ
test_user_id = "U1234567890"
test_keywords = "AI,経済,健康"
sheet.append_row([test_user_id, test_keywords])
print(f"新規ユーザー追加: {test_user_id} -> {test_keywords}")