# AI画像生成サービス 環境構築手順

このドキュメントでは、AI画像生成サービスを実行する前に必要な環境構築手順を説明します。

## 目次

1. [前提条件](#前提条件)
2. [Google Cloud Platform の設定](#google-cloud-platform-の設定)
3. [データベースの設定](#データベースの設定)
4. [Python環境の構築](#python環境の構築)
5. [環境変数ファイル（.env）の作成](#環境変数ファイルenvの作成)
6. [動作確認](#動作確認)

---

## 前提条件

- Python 3.11 以上がインストールされていること
- Google Cloud アカウントを持っていること
- MySQL データベースが利用可能であること（ローカルまたはリモート）

---

## Google Cloud Platform の設定

### 1. Google Cloud プロジェクトの作成

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 画面上部のプロジェクト選択ドロップダウンをクリック
3. 「新しいプロジェクト」をクリック
4. プロジェクト名を入力（例: `smaclo`）
5. 「作成」をクリック
6. 作成したプロジェクトを選択

### 2. Vertex AI API の有効化

1. Google Cloud Console で、左側のメニューから「APIとサービス」→「ライブラリ」を選択
2. 検索バーで「Vertex AI API」を検索
3. 「Vertex AI API」を選択
4. 「有効にする」ボタンをクリック

**注意**: API の有効化には数分かかる場合があります。

### 3. 認証情報の設定

このサービスは **Application Default Credentials (ADC)** を使用して認証を行います。以下のいずれかの方法で認証を設定してください。

#### gcloud CLI を使用

1. [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) をインストール（まだインストールしていない場合）

2. ターミナルで以下のコマンドを実行してログイン：
   ```bash
   gcloud auth login
   ```

3. デフォルトのプロジェクトを設定：
   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```
   （`YOUR_PROJECT_ID` は作成したプロジェクトのIDに置き換えてください）

4. Application Default Credentials を設定：
   ```bash
   gcloud auth application-default login
   ```
   このコマンドを実行すると、ブラウザが開いて認証を求められます。認証が完了すると、認証情報がローカルに保存されます。

---

## データベースの設定
スマクロのデータベースを追加。

---

## Python環境の構築
各々の環境を構築

---

## 環境変数ファイル（.env）の作成

プロジェクトルート（`backend` ディレクトリ）に `.env` ファイルを作成し、以下の環境変数を設定します。

### .env ファイルの例

```env
# データベース接続情報
DB_HOST=localhost
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password

# Google Cloud プロジェクトID（オプション）
# GOOGLE_CLOUD_PROJECT=your-project-id
```

### ファイルの場所

`.env` ファイルはプロジェクトルート（`backend` ディレクトリ）に配置してください：

```
backend/
├── .env          ← ここに配置
├── app.py
├── requirements.txt
└── ...
```

**重要**: `.env` ファイルには機密情報が含まれているため、Git にコミットしないでください。`.gitignore` に `.env` が含まれていることを確認してください。

---

## 動作確認

### 1. 環境変数の確認

ターミナルで以下のコマンドを実行して、環境変数が正しく読み込まれているか確認します：

```bash
# Python で確認
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('DB_HOST:', os.getenv('DB_HOST')); print('DB_NAME:', os.getenv('DB_NAME'))"
```

### 2. Google Cloud 認証の確認

```bash
# gcloud CLI がインストールされている場合
gcloud auth list
gcloud config get-value project
```

### 3. アプリケーションの起動

```bash
# 仮想環境が有効になっていることを確認
python app.py
```

アプリケーションが正常に起動すれば、環境構築は完了です。

### 4. AI画像生成サービスのテスト

ブラウザまたは curl で以下のエンドポイントにアクセスしてテストします：

```bash
# ブラウザでアクセス
http://localhost:5000/generate

# または curl で
curl http://localhost:5000/generate
```
