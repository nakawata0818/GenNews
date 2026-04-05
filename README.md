# ニュース要約LINE Bot

## 概要

個人向けパーソナライズニュース配信Botです。指定キーワードのニュースを毎朝LINEに要約配信します。

---

## ディレクトリ構成

```
/news-bot
├── main.py
├── rss.py
├── summarize.py
├── dedup.py
├── notifier.py
├── config.py
├── requirements.txt
├── .env.example
└── .github/workflows/cron.yml
```

---

## 環境変数の設定

1. `.env` ファイルを作成し、以下を記入：

```
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

2. GitHub Actionsで利用する場合は、リポジトリの「Settings」→「Secrets and variables」→「Actions」から同名で登録してください。

---

## ローカル実行手順

1. 依存パッケージのインストール

```
pip install -r requirements.txt
```

2. `.env` を用意

3. 実行

```
python main.py
```

---

## GitHub Actionsでの自動実行

1. `.github/workflows/cron.yml` が毎日7時(JST)に自動実行します。
2. 必要なシークレット（OPENAI_API_KEY, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）を登録してください。

---

## 注意事項

- ニュース本文全文は取得しません（著作権配慮）
- 要約＋リンク形式で配信します
- API使用量を抑えるため最大5件のみ配信
- ログはprintで出力
- エラー時もfail-safeで継続

---

## 拡張予定

- いいね/興味なし
- パーソナライズ強化
- 音声化
- Web UI

## Google Sheets連携

- Google SheetsのシートID（SHEET_KEY）とサービスアカウントJSON（GOOGLE_SERVICE_ACCOUNT_JSON）を用意
- .envに下記を追加

```
SHEET_KEY=your-google-sheet-id
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json
```

- シート構成例：
    - 1列目: LINE_USER_ID
    - 2列目: KEYWORDS

## Renderデプロイ

- requirements.txt, Procfile, gunicorn対応済み
- Webhookエンドポイント `/linewebhook` をLINE Developersに設定
- サービスアカウントJSONはRenderの環境変数または永続ストレージに配置
