# スマクロバックエンド

このプロジェクトでは、Google AI Studio (Gemini API) と Google Cloud (Vertex AI) OpenWeatherMap API(WeatherAPI) を使用しています。

##　開発環境
- Python 3.11.13
- Flask 3.1.2
- Werkzeug 3.1.3
- MySQL 8.0.31
- 依存ライブラリは `requirements.txt` を参照

## セットアップ

実行には以下の2種類の認証設定が必要です。
プロジェクトルートに.envファイルを作成して下さい。

### 1. Google AI Studio (Gemini API)
1. [Google AI Studio](https://aistudio.google.com/) で API キーを発行します。
2. プロジェクトルートの `.env` ファイルに以下の内容を追記してください。

```env
GEMINI_API_KEY=あなたのAPIキー
```

### 2. Vertex AI (Google Cloud)
Vertex AI の利用にはサービスアカウントの JSON キーファイルが必要です。

Google Cloud Console から「サービスアカウント」を作成し、Vertex AI ユーザー などの適切な権限を付与します。

「キー」タブから JSON形式 の秘密鍵をダウンロードします。

ダウンロードしたファイルを projectname-xxxx-xxxx.json という名前（または任意の名称）でプロジェクトのルートディレクトリに配置してください。

環境変数でこのパスを指定します（.env にパスを記述します）。

```env
GOOGLE_APPLICATION_CREDENTIALS="projectname-xxxx-xxxx.json"
```

コード スニペット
GOOGLE_APPLICATION_CREDENTIALS="projectname-xxxx-xxxx.json"
⚠️ セキュリティに関する重要事項
認証情報（.env および .json ファイル）を絶対に Git リポジトリにコミットしないでください。

```env
# 認証情報
projectname-xxxx-xxxx.json
```

### 3. OpenWeatherMap API(WeatherAPI)
1. [Open Weather](https://openweathermap.org/api)で API キーを発行します。
2. プロジェクトルートの `.env` ファイルに以下の内容を追記してください。

```env
OPENWEATHER_API_KEY=あなたのAPIキー
```
---
## 環境構築
1. 仮想環境を作成・有効化
2. 依存ライブラリのインポート
3. 20250823_dump.sqlを使用しmysql上でDBを作成
4. .envをapp.pyと同階層に作成し次の内容を記述する
    DB_HOST=your_db_hostname
    DB_NAME=your_db_name
    DB_USER=your_db_user
    DB_PASSWORD=your_db_password
---
## 実行
1. flaskの起動(以下コマンドで)
    flask run --host=0.0.0.0 --port=5000
2. 起動ポート確認
    以下リンクを確認する
    Running on http://192.168.00.00:0000/
3. 2のサーバーURLをフロントエンドの設定画面のSERVER_URLに記述
    参考画像
    [参考画像](https://github.com/SmartClosetProject25/backend/issues/54#issue-3982063336)
---
