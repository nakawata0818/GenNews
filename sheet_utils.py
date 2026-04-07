def get_user_keywords(user_id):
    """
    keywordsシートからユーザーのキーワードと重みを取得
    return: [(keyword, weight), ...]
    """
    sheet = get_sheet_by_name('keywords')
    records = sheet.get_all_records()
    print(f"[DEBUG] keywords records: {records}")
    result = []
    for row in records:
        print(f"[DEBUG] row: {row}")
        if row.get('user_id') == user_id:
            kw = row.get('keyword')
            try:
                weight = float(row.get('weight', 1.0))
            except Exception:
                weight = 1.0
            result.append((kw, weight))
    print(f"[DEBUG] get_user_keywords({user_id}) -> {result}")
    return result

def get_sent_article_ids(user_id):
    """
    historyシートからユーザーが既に受信した記事IDセットを返す
    """
    sheet = get_sheet_by_name('history')
    records = sheet.get_all_records()
    return set(row['article_id'] for row in records if row.get('user_id') == user_id)

def save_sent_articles(user_id, article_ids):
    """
    historyシートに送信済み記事を追加
    """
    sheet = get_sheet_by_name('history')
    for aid in article_ids:
        sheet.append_row([user_id, aid])

def update_keyword_weight(user_id, keyword, delta):
    """
    keywordsシートのweightを増減。なければ新規追加。
    """
    sheet = get_sheet_by_name('keywords')
    records = sheet.get_all_records()
    for idx, row in enumerate(records, start=2):
        if row.get('user_id') == user_id and row.get('keyword') == keyword:
            try:
                weight = float(row.get('weight', 1.0))
            except Exception:
                weight = 1.0
            new_weight = max(0.0, weight + delta)
            sheet.update_cell(idx, 3, new_weight)
            return
    # 新規
    sheet.append_row([user_id, keyword, max(0.0, 1.0 + delta)])

def get_sheet_by_name(name):
    print(f"[DEBUG] get_sheet_by_name({name})")
    creds_path = setup_google_credentials()
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(GOOGLE_SHEET_KEY).worksheet(name)
    print(f"[DEBUG] sheet columns: {sheet.row_values(1)}")
    return sheet

import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import tempfile
import base64
from config import GOOGLE_SHEET_KEY, SHEET_NAME, GOOGLE_SHEETS_CRED_JSON

SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

def setup_google_credentials():
    b64 = os.getenv("GOOGLE_CREDENTIALS_BASE64")
    if b64:
        json_bytes = base64.b64decode(b64)
        tmp_path = os.path.join(tempfile.gettempdir(), "service_account.json")
        with open(tmp_path, "wb") as f:
            f.write(json_bytes)
        return tmp_path
    elif GOOGLE_SHEETS_CRED_JSON:
        return GOOGLE_SHEETS_CRED_JSON
    else:
        raise Exception("Google認証情報が設定されていません")

def get_sheet():
    creds_path = setup_google_credentials()
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, SCOPE)
    client = gspread.authorize(creds)
    if GOOGLE_SHEET_KEY:
        return client.open_by_key(GOOGLE_SHEET_KEY).sheet1
    else:
        return client.open(SHEET_NAME).sheet1

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
