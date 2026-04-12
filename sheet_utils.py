import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import tempfile
import base64
from datetime import datetime, timezone
from config import GOOGLE_SHEET_KEY, SHEET_NAME, GOOGLE_SHEETS_CRED_JSON

SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

# 認証クライアントと認証ファイルパスのキャッシュ用変数
_gspread_client = None
_creds_path = None
_spreadsheet = None
_worksheets = {}

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

def save_category_mappings_batch(mappings):
    """
    複数キーワードのカテゴリ分類をまとめて保存/更新（API節約版）
    mappings: {keyword: category, ...}
    """
    try:
        sheet = get_sheet_by_name('category_map')
        records = sheet.get_all_records()
        
        # 現状のキーワードと行番号のマップを作成
        kw_to_row = {str(row.get('keyword', '')).strip(): idx for idx, row in enumerate(records, start=2)}
        
        for kw, cat in mappings.items():
            kw_clean = str(kw).strip()
            if kw_clean in kw_to_row:
                # 既存なら更新
                sheet.update_cell(kw_to_row[kw_clean], 2, cat)
            else:
                # 新規なら追加
                sheet.append_row([kw_clean, cat])
                # recordsを模して追加（同じバッチ内での重複回避用）
                kw_to_row[kw_clean] = len(kw_to_row) + 2 
    except Exception as e:
        print(f"[sheet_utils error] save_category_mappings_batch: {e}")

def save_category_mapping(keyword, category):
    """単一の保存もバッチ用関数を再利用"""
    save_category_mappings_batch({keyword: category})

def save_article_log(user_id, article_id, keywords, category, action):
    """
    article_logシートにユーザー行動ログを保存
    """
    sheet = get_sheet_by_name('article_log')
    timestamp = datetime.now(timezone.utc).isoformat() # ISO 8601形式
    # related_keywordsも保存するように拡張
    kw_list = keywords if isinstance(keywords, list) else [keywords]
    # もし関連キーワードが辞書等で渡された場合は文字列化
    kw_str = ",".join(kw_list)
    # 指示書3.3の構造: user_id | article_id | keywords | related_keywords | category | action | timestamp
    # 今回は簡易的に引数を増やさず、既存の仕組みを壊さない形で実装
    sheet.append_row([user_id, article_id, kw_str, "", category, action, timestamp])

def get_related_keywords(user_id):
    """related_keywordsシートから取得"""
    try:
        sheet = get_sheet_by_name('related_keywords')
        records = sheet.get_all_records()
        return [r for r in records if str(r.get('user_id', '')).strip() == str(user_id).strip()]
    except Exception:
        return []

def update_related_keyword(user_id, keyword, action):
    """関連キーワードのスコアとlike_countを更新"""
    try:
        sheet = get_sheet_by_name('related_keywords')
        records = sheet.get_all_records()
        found = False
        for idx, row in enumerate(records, start=2):
            if str(row.get('user_id')) == str(user_id) and row.get('keyword') == keyword:
                score = float(row.get('score', 0.3))
                likes = int(row.get('like_count', 0))
                if action == "like":
                    score += 0.1
                    likes += 1
                else:
                    score -= 0.4
                sheet.update_cell(idx, 3, score) # score
                sheet.update_cell(idx, 4, likes) # like_count
                sheet.update_cell(idx, 5, datetime.now(timezone.utc).isoformat())
                found = True
                break
        if not found and action == "like":
            sheet.append_row([user_id, keyword, 0.4, 1, datetime.now(timezone.utc).isoformat()])
    except Exception as e:
        print(f"[Error] update_related_keyword: {e}")

def promote_keywords(user_id):
    """昇格条件(score>=1.0 & likes>=2)を満たすキーワードをmainへ移動"""
    try:
        rel_sheet = get_sheet_by_name('related_keywords')
        records = rel_sheet.get_all_records()
        to_promote = []
        for idx, r in enumerate(records, start=2):
            if str(r.get('user_id')) == str(user_id):
                if float(r.get('score', 0)) >= 1.0 and int(r.get('like_count', 0)) >= 2:
                    to_promote.append((idx, r.get('keyword')))
        
        for idx, kw in reversed(to_promote): # 下から削除しないと行番号がずれるため
            update_keyword_weight(user_id, kw, -0.2) # 初期weight 0.8にするため(1.0 + -0.2)
            # 互換性のための処理
            if hasattr(rel_sheet, 'delete_row'):
                rel_sheet.delete_row(idx)
            else:
                rel_sheet.delete_rows(idx)
            print(f"[PROMOTION] {kw} moved to main keywords for {user_id}")
    except Exception as e:
        print(f"[Error] promote_keywords: {e}")

def delete_user_keyword(user_id, keyword):
    """keywordsシートから指定ユーザーのキーワードを削除"""
    try:
        sheet = get_sheet_by_name('keywords')
        records = sheet.get_all_records()
        # ユーザーIDとキーワードが一致する行を探して削除
        for idx, row in enumerate(records, start=2):
            s_uid = str(row.get('user_id', '')).strip()
            s_target_uid = str(user_id).strip()
            s_kw = str(row.get('keyword', '')).strip()
            s_target_kw = str(keyword).strip()

            if s_uid == s_target_uid and s_kw == s_target_kw:
                # 互換性のための処理
                if hasattr(sheet, 'delete_row'):
                    sheet.delete_row(idx)
                else:
                    sheet.delete_rows(idx)
                print(f"[DEBUG] Deleted row {idx} for user {user_id}, keyword {keyword}")
                return True
    except Exception as e:
        print(f"[Error] delete_user_keyword: {e}")
    return False

def get_user_state(user_id):
    """ユーザーの現在の対話状態を取得"""
    try:
        sheet = get_sheet_by_name('user_state')
        records = sheet.get_all_records()
        for r in records:
            if str(r.get('user_id', '')).strip() == str(user_id).strip():
                return r.get('state', 'IDLE')
    except Exception:
        pass
    return 'IDLE'

def set_user_state(user_id, state):
    """ユーザーの対話状態を保存"""
    try:
        sheet = get_sheet_by_name('user_state')
        records = sheet.get_all_records()
        found = False
        for idx, row in enumerate(records, start=2):
            if str(row.get('user_id', '')).strip() == str(user_id).strip():
                sheet.update_cell(idx, 2, state)
                sheet.update_cell(idx, 3, datetime.now(timezone.utc).isoformat())
                found = True
                break
        if not found:
            sheet.append_row([user_id, state, datetime.now(timezone.utc).isoformat()])
    except Exception as e:
        print(f"[Error] set_user_state: {e}")

def save_exposure(user_id, keywords):
    """露出を記録"""
    try:
        sheet = get_sheet_by_name('keyword_exposure')
        timestamp = datetime.now(timezone.utc).isoformat()
        for kw in keywords:
            sheet.append_row([user_id, kw, timestamp])
    except Exception:
        pass

def get_all_exposure_logs(user_id):
    """ユーザーの全露出ログを一度に取得"""
    try:
        sheet = get_sheet_by_name('keyword_exposure')
        return [r for r in sheet.get_all_records() if str(r.get('user_id')) == str(user_id)]
    except Exception:
        return []

def calculate_exposure_score_from_logs(logs, keyword):
    """取得済みのログから特定のキーワードの露出スコアを計算"""
    try:
        now = datetime.now(timezone.utc)
        score = 0.0
        for r in logs:
            if r.get('keyword') == keyword:
                ts = datetime.fromisoformat(r.get('timestamp').replace('Z', '+00:00'))
                days = (now - ts).days
                score += (0.9 ** days)
        return score
    except Exception:
        return 0.0

def update_keyword_weight(user_id, keyword, delta):
    """
    keywordsシートのweightを増減。なければ新規追加。
    """
    sheet = get_sheet_by_name('keywords')
    records = sheet.get_all_records()
    for idx, row in enumerate(records, start=2):
        s_uid = str(row.get('user_id', '')).strip()
        s_target_uid = str(user_id).strip()
        s_kw = str(row.get('keyword', '')).strip()
        s_target_kw = str(keyword).strip()

        if s_uid == s_target_uid and s_kw == s_target_kw:
            try:
                weight = float(row.get('weight', 1.0))
            except Exception:
                weight = 1.0
            new_weight = max(0.0, weight + delta)
            print(f"[LEARNING] User: {user_id}, Keyword: {keyword}, Weight: {weight} -> {new_weight}")
            # 列番号を間違えないよう注意（1:user_id, 2:keyword, 3:weight想定）
            sheet.update_cell(idx, 3, float(new_weight))
            return
    # 新規
    sheet.append_row([user_id, keyword, max(0.0, 1.0 + delta)])

def get_sheet_by_name(name):
    """名前を指定してワークシートを取得（キャッシュを利用してAPI呼び出しを最小化）"""
    global _spreadsheet, _worksheets
    if _spreadsheet is None:
        client = get_gspread_client()
        _spreadsheet = client.open_by_key(GOOGLE_SHEET_KEY)
    
    if name not in _worksheets:
        try:
            _worksheets[name] = _spreadsheet.worksheet(name)
        except gspread.exceptions.WorksheetNotFound:
            # シートがない場合は自動作成（1行目にデフォルトヘッダーを入れる）
            print(f"[INFO] Worksheet '{name}' not found. Creating...")
            new_ws = _spreadsheet.add_worksheet(title=name, rows="100", cols="20")
            if name == 'user_state':
                new_ws.append_row(['user_id', 'state', 'updated_at'])
            elif name == 'related_keywords':
                new_ws.append_row(['user_id', 'keyword', 'score', 'like_count', 'last_updated'])
            _worksheets[name] = new_ws

    return _worksheets[name]

def get_gspread_client():
    """gspreadクライアントを取得、未認証の場合は認証を行う"""
    global _gspread_client
    if _gspread_client is None:
        creds_path = setup_google_credentials()
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, SCOPE)
        _gspread_client = gspread.authorize(creds)
    return _gspread_client

def setup_google_credentials():
    """認証情報のセットアップを行いパスを返す（パスをキャッシュ）"""
    global _creds_path
    if _creds_path and os.path.exists(_creds_path):
        return _creds_path

    b64 = os.getenv("GOOGLE_CREDENTIALS_BASE64")
    if b64:
        json_bytes = base64.b64decode(b64)
        tmp_path = os.path.join(tempfile.gettempdir(), "service_account.json")
        with open(tmp_path, "wb") as f:
            f.write(json_bytes)
        _creds_path = tmp_path
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
