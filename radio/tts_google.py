from google.cloud import texttospeech
import base64
import os
import json
import tempfile

def init_tts_client():
    # Renderの環境変数から認証情報を取得
    b64_creds = os.getenv("GOOGLE_CREDENTIALS_BASE64")
    if not b64_creds:
        raise Exception("GOOGLE_CREDENTIALS_BASE64 が設定されていません")
    creds_json = base64.b64decode(b64_creds).decode("utf-8")
    creds_dict = json.loads(creds_json)
    return texttospeech.TextToSpeechClient.from_service_account_info(creds_dict)

def generate_audio(text):
    """テキストをMP3音声ファイルに変換する"""
    client = init_tts_client()
    synthesis_input = texttospeech.SynthesisInput(text=text)

    # 声の設定（Neural2 B は落ち着いた男性の声、Neural2 C は女性の声など選択可能）
    voice = texttospeech.VoiceSelectionParams(
        language_code="ja-JP",
        name="ja-JP-Neural2-B"
    )

    # オーディオ設定（少しだけ速めることで聞きやすくする）
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
        
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        with open(tmp.name, "wb") as out:
            out.write(response.audio_content)
        return tmp.name
    except Exception as e:
        print(f"[TTS Error] {e}")
        return None