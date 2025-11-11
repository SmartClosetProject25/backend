# email_service.py (Gmail API版)
import os
import base64
import pickle
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def get_gmail_service():
    """Gmail API サービスを取得"""
    creds = None
    token_file = os.getenv('GMAIL_TOKEN_FILE', 'token.pickle')
    
    # 既存のトークンを読み込む
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
    
    # トークンが無効または存在しない場合は再認証
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_secret_file = os.getenv('GMAIL_CLIENT_SECRET_FILE', 'client_secret.json')
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # トークンを保存
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
    
    return build("gmail", "v1", credentials=creds)

def send_email(to: str, subject: str, text_body: str, html_body: str = None):
    """汎用メール送信関数"""
    # メッセージ作成
    if html_body:
        message = MIMEMultipart('alternative')
        part1 = MIMEText(text_body, 'plain', 'utf-8')
        part2 = MIMEText(html_body, 'html', 'utf-8')
        message.attach(part1)
        message.attach(part2)
    else:
        message = MIMEText(text_body, 'plain', 'utf-8')
    
    message['to'] = to
    message['subject'] = subject
    
    # Base64エンコード
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    # Gmail APIで送信
    try:
        service = get_gmail_service()
        send_message = service.users().messages().send(
            userId="me",
            body={"raw": encoded_message}
        ).execute()
        return send_message["id"]
    except Exception as e:
        raise Exception(f"Failed to send email: {str(e)}")

def send_password_reset_email(email: str, token: str):
    """パスワード再設定メールを送信（Android Deep Link対応）"""
    # Android Deep Link URLスキーム
    android_deep_link = os.getenv('ANDROID_DEEP_LINK_SCHEME', 'smartcloset://reset-password')
    reset_url = f"{android_deep_link}?token={token}"
    
    # フォールバック用のWeb URL（オプション）
    web_url = os.getenv('WEB_RESET_URL', '')
    
    # HTMLメール本文
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #4CAF50;">パスワード再設定のご案内</h2>
            <p>パスワード再設定のリクエストを受け付けました。</p>
            
            <p><strong>Androidアプリがインストールされている場合：</strong></p>
            <a href="{reset_url}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0;">
                パスワードを再設定する
            </a>
            
            <p style="margin-top: 30px;">または、アプリ内で以下のトークンを入力してください：</p>
            <div style="background-color: #f0f0f0; padding: 15px; font-family: monospace; word-break: break-all; border-radius: 5px; margin: 10px 0;">
                {token}
            </div>
            
            <p style="color: #666; font-size: 12px; margin-top: 30px;">
                このリンクは1時間有効です。<br>
                もしこのリクエストをしていない場合は、このメールを無視してください。
            </p>
        </div>
    </body>
    </html>
    """
    
    # テキストメール本文（フォールバック）
    text_body = f"""
パスワード再設定のご案内

パスワード再設定のリクエストを受け付けました。

Androidアプリがインストールされている場合は、以下のリンクをタップしてください：
{reset_url}

アプリがインストールされていない場合は、以下のURLからアプリをダウンロードしてください：
{web_url}

このリンクは1時間有効です。

もしこのリクエストをしていない場合は、このメールを無視してください。

リセットトークン: {token}
（アプリで直接入力することも可能です）
"""
    
    return send_email(email, "パスワード再設定のご案内", text_body, html_body)
