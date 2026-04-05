def get_sheet():

import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import base64

SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
SHEET_KEY = os.getenv('SHEET_KEY')  # シートIDは環境変数で
SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')

def setup_google_credentials():
    b64 = os.getenv("GOOGLE_CREDENTIALS_BASE64")
    if b64:
        json_bytes = base64.b64decode(b64)
        path = "/tmp/service_account.json"
        with open(path, "wb") as f:
            f.write(json_bytes)
        return path
    elif SERVICE_ACCOUNT_JSON:
        return SERVICE_ACCOUNT_JSON
    else:
        raise Exception("Google認証情報が設定されていません")

# シート認証・取得
def get_sheet():
    creds_path = setup_google_credentials()
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, SCOPE)
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
