def get_all_users_keywords():
    client = get_client()
    sheet = client.open_by_key(os.getenv("GOOGLE_SHEET_KEY")).worksheet("keywords")
    rows = sheet.get_all_values()
    result = {}
    for row in rows[1:]:  # ヘッダーはスキップ
        user_id = row[0]
        kws = [kw for kw in row[1:] if kw]
        result[user_id] = kws
    return result

def update_keywords_for_user(user_id, keywords):
    client = get_client()
    sheet = client.open_by_key(os.getenv("GOOGLE_SHEET_KEY")).worksheet("keywords")
    rows = sheet.get_all_values()
    found = False
    for i, row in enumerate(rows):
        if row and row[0] == user_id:
            # 既存ユーザーを更新
            for j, kw in enumerate(keywords, start=1):
                sheet.update_cell(i+1, j+1, kw)
            found = True
            break
    if not found:
        # 新規ユーザー追加
        sheet.append_row([user_id] + keywords)