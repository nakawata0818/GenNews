import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import tempfile
import base64
from datetime import datetime, timezone
from config import GOOGLE_SHEET_KEY, SHEET_NAME, GOOGLE_SHEETS_CRED_JSON

SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

def get_user_keywords(user_id):
    """
    keywordsシートからユーザーのキーワードと重みを取得
    return: [(keyword, weight), ...]
    """
    sheet = get_sheet_by_name('keywords')
    records = sheet.get_all_records()
    if records:
        print(f"[DEBUG] keywords headers found: {list(records[0].keys())}")
    
    result = []
    for row in records:
        # user_id のキーが存在し、かつ値が一致するか（文字列として比較）
        if str(row.get('user_id', '')).strip() == str(user_id).strip():
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
        sheet.append_row([user_id, aid, datetime.now(timezone.utc).isoformat()])

def get_all_user_ids():
    """keywordsシートからユニークなユーザーID一覧を取得"""
    sheet = get_sheet_by_name('keywords')
    records = sheet.get_all_records()
    user_ids = set()
    for row in records:
        uid = str(row.get('user_id', '')).strip()
        if uid:
            user_ids.add(uid)
    return list(user_ids)

def get_category_map():
    """category_mapシートから全マッピングを取得"""
    try:
        sheet = get_sheet_by_name('category_map')
        records = sheet.get_all_records()
        return {row['keyword']: row['category'] for row in records}
    except Exception:
        return {}

def save_category_mapping(keyword, category):
    """category_mapシートに新しい分類を保存"""
    try:
        sheet = get_sheet_by_name('category_map')
        sheet.append_row([keyword, category])
    except Exception as e:
        print(f"[sheet_utils error] save_category_mapping: {e}")

def save_article_log(user_id, article_id, keywords, category, action):
    """
    article_logシートにユーザー行動ログを保存
    """
    sheet = get_sheet_by_name('article_log')
    timestamp = datetime.now(timezone.utc).isoformat() # ISO 8601形式
    # keywordsはリストで渡されるのでカンマ区切り文字列に変換
    keywords_str = ",".join(keywords) if isinstance(keywords, list) else keywords
    sheet.append_row([user_id, article_id, keywords_str, category, action, timestamp])

    # user_profileシートのキャッシュ更新（簡易版、後で最適化）
    # ここでは直接更新せず、profile.pyで集計する前提
    pass

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
            # 列番号を間違えないよう注意（1:user_id, 2:keyword, 3:weight想定）
            sheet.update_cell(idx, 3, float(new_weight))
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

def set_user_keywords(user_id, keywords):
    """
    ユーザーのキーワードを登録・更新 (keywordsシートのみを更新)
    """
    # 1. keywordsシートへの登録
    for kw in keywords:
        update_keyword_weight(user_id, kw, 0.0) # 初期値1.0で登録
