import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
SHEET_KEY = os.getenv('SHEET_KEY')  # シートIDは環境変数で
SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')

# シート認証・取得

def get_sheet():
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_JSON, SCOPE)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_KEY).sheet1

# ユーザーのキーワードを取得

def get_user_keywords(user_id):
    sheet = get_sheet()
    records = sheet.get_all_records()
    for row in records:
        if row['LINE_USER_ID'] == user_id:
            return [k.strip() for k in row['KEYWORDS'].split(',') if k.strip()]
    return []

# ユーザーのキーワードを登録・更新

def set_user_keywords(user_id, keywords):
    sheet = get_sheet()
    records = sheet.get_all_records()
    for idx, row in enumerate(records, start=2):  # 1行目はヘッダ
        if row['LINE_USER_ID'] == user_id:
            sheet.update_cell(idx, 2, ','.join(keywords))
            return
    # 新規
    sheet.append_row([user_id, ','.join(keywords)])
