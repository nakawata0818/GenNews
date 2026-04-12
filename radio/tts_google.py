from google.cloud import texttospeech
import base64
import os
import json
import uuid

def init_tts_client():
    # Renderの環境変数から認証情報を取得
    # どちらの環境変数名でも動作するように対応
    b64_creds = os.getenv("GOOGLE_CREDENTIALS_BASE64") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not b64_creds:
        raise Exception("GOOGLE_CREDENTIALS_BASE64 が設定されていません")
    creds_json = base64.b64decode(b64_creds).decode("utf-8")
    creds_dict = json.loads(creds_json)
    return texttospeech.TextToSpeechClient.from_service_account_info(creds_dict)

def generate_audio(text):
    """テキストをMP3音声ファイルに変換する (5000バイト制限対応版)"""
    client = init_tts_client()

    # 1000文字ごとに分割 (日本語は3バイト/文字なので、1000*3 = 3000バイトで安全圏。API制限5000バイト対策)
    chunk_size = 1000
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    
    combined_audio_content = b""

    for i, chunk in enumerate(chunks):
        print(f"[DEBUG][TTS] Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
        synthesis_input = texttospeech.SynthesisInput(text=chunk)

        # 声の設定
        voice = texttospeech.VoiceSelectionParams(
            language_code="ja-JP",
            name="ja-JP-Neural2-B"
        )

        # オーディオ設定
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.05
        )

        try:
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            combined_audio_content += response.audio_content
        except Exception as e:
            print(f"[TTS Error] Chunk {i+1} failed: {e}")
            if not combined_audio_content: return None
            break # 途中までできている場合はそれを返す
        
    if not combined_audio_content:
        return None

    try:
        filename = f"{uuid.uuid4()}.mp3"
        path = f"/tmp/{filename}"
        with open(path, "wb") as out:
            out.write(combined_audio_content)
        return filename, path
    except Exception as e:
        print(f"[TTS Error] {e}")
        return None