from google.cloud import storage
import base64
import json
import os
from datetime import datetime
from config import GCS_BUCKET_NAME

def upload_to_gcs(file_path, user_id):
    """ファイルをGCSにアップロードして公開URLを返す"""
    b64_creds = os.getenv("GOOGLE_CREDENTIALS_BASE64")
    if not b64_creds:
        raise Exception("GOOGLE_CREDENTIALS_BASE64 が設定されていません")
    creds_json = base64.b64decode(b64_creds).decode("utf-8")
    creds_dict = json.loads(creds_json)
    
    client = storage.Client.from_service_account_info(creds_dict)
    if not GCS_BUCKET_NAME:
        raise Exception("GCS_BUCKET_NAME が設定されていません。.env ファイルまたはRenderの環境変数を確認してください。")

    bucket = client.bucket(GCS_BUCKET_NAME)

    # コスト削減：同じユーザーの古いラジオファイルを削除
    try:
        blobs = bucket.list_blobs(prefix=f"radio_{user_id}_")
        for old_blob in blobs:
            old_blob.delete()
            print(f"[STORAGE] Deleted old radio file: {old_blob.name}")
    except Exception as e:
        print(f"[STORAGE WARNING] Failed to cleanup old files: {e}")
    
    # ファイル名にタイムスタンプとユーザーIDを含めて衝突を避ける
    filename = f"radio_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp3"
    blob = bucket.blob(filename)
    
    blob.upload_from_filename(file_path)
    
    # LINEからアクセスできるように公開設定にする（バケットの設定によるが、ここでは明示的に公開）
    blob.make_public()
    
    return blob.public_url