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
    print("  [get_gmail_service] Starting Gmail service initialization")
    creds = None
    token_file = os.getenv('GMAIL_TOKEN_FILE', 'token.pickle')
    print(f"  [get_gmail_service] Token file: {token_file}")
    
    # 既存のトークンを読み込む
    if os.path.exists(token_file):
        print(f"  [get_gmail_service] Token file exists, loading...")
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
        print(f"  [get_gmail_service] Token loaded")
    else:
        print(f"  [get_gmail_service] Token file not found")
    
    # トークンが無効または存在しない場合は再認証
    if not creds or not creds.valid:
        print(f"  [get_gmail_service] Token is invalid or missing")
        if creds and creds.expired and creds.refresh_token:
            print(f"  [get_gmail_service] Refreshing expired token...")
            try:
                creds.refresh(Request())
                print(f"  [get_gmail_service] Token refreshed")
            except Exception as refresh_error:
                print(f"  [get_gmail_service] Token refresh failed: {str(refresh_error)}")
                print(f"  [get_gmail_service] Refresh token is invalid, starting OAuth flow...")
                creds = None  # リフレッシュ失敗時はクリアして再認証
        else:
            print(f"  [get_gmail_service] Starting OAuth flow...")
        
        # トークンがまだ無効な場合はOAuthフローを開始
        if not creds or not creds.valid:
            client_secret_file = os.getenv('GMAIL_CLIENT_SECRET_FILE', 'client_secret.json')
            print(f"  [get_gmail_service] Client secret file: {client_secret_file}")
            if not os.path.exists(client_secret_file):
                raise FileNotFoundError(f"Client secret file not found: {client_secret_file}")
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
            creds = flow.run_local_server(port=0)
            print(f"  [get_gmail_service] OAuth flow completed")
        
        # トークンを保存
        print(f"  [get_gmail_service] Saving token to {token_file}")
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
        print(f"  [get_gmail_service] Token saved")
    else:
        print(f"  [get_gmail_service] Token is valid")
    
    print(f"  [get_gmail_service] Building Gmail service...")
    service = build("gmail", "v1", credentials=creds)
    print(f"  [get_gmail_service] Gmail service ready")
    return service

def send_email(to: str, subject: str, text_body: str, html_body: str = None):
    """汎用メール送信関数"""
    print(f"  [send_email] Starting email send")
    print(f"  [send_email] To: {to}")
    print(f"  [send_email] Subject: {subject}")
    print(f"  [send_email] Has HTML body: {html_body is not None}")
    
    # メッセージ作成
    if html_body:
        print(f"  [send_email] Creating multipart message (text + HTML)")
        message = MIMEMultipart('alternative')
        part1 = MIMEText(text_body, 'plain', 'utf-8')
        part2 = MIMEText(html_body, 'html', 'utf-8')
        message.attach(part1)
        message.attach(part2)
    else:
        print(f"  [send_email] Creating plain text message")
        message = MIMEText(text_body, 'plain', 'utf-8')
    
    message['to'] = to
    message['subject'] = subject
    
    # Base64エンコード
    print(f"  [send_email] Encoding message to Base64...")
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    print(f"  [send_email] Message encoded (length: {len(encoded_message)})")
    
    # Gmail APIで送信
    try:
        print(f"  [send_email] Getting Gmail service...")
        service = get_gmail_service()
        print(f"  [send_email] Sending email via Gmail API...")
        send_message = service.users().messages().send(
            userId="me",
            body={"raw": encoded_message}
        ).execute()
        message_id = send_message["id"]
        print(f"  [send_email] Email sent successfully! Message ID: {message_id}")
        return message_id
    except Exception as e:
        print(f"  [send_email] ERROR: Failed to send email: {str(e)}")
        print(f"  [send_email] Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Failed to send email: {str(e)}")

def send_password_reset_email(email: str, token: str):
    """パスワード再設定メールを送信（Android Deep Link対応）"""
    print(f"  [send_password_reset_email] Starting password reset email")
    print(f"  [send_password_reset_email] Email: {email}")
    print(f"  [send_password_reset_email] Token: {token[:20]}...")
    
    # Android Deep Link URLスキーム
    android_deep_link = os.getenv('ANDROID_DEEP_LINK_SCHEME', 'smartcloset://reset-password')
    reset_url = f"{android_deep_link}?token={token}"
    print(f"  [send_password_reset_email] Android deep link: {android_deep_link}")
    print(f"  [send_password_reset_email] Reset URL: {reset_url}")
    
    # フォールバック用のWeb URL（オプション）
    web_url = os.getenv('WEB_RESET_URL', '')
    if web_url:
        print(f"  [send_password_reset_email] Web URL: {web_url}")
    else:
        print(f"  [send_password_reset_email] Web URL not set")
    
    # テキストメール本文のみ
    print(f"  [send_password_reset_email] Creating text email body...")
    text_body = f"""
パスワード再設定のご案内

パスワード再設定のリクエストを受け付けました。

以下のリンクをタップしてパスワードを再設定してください：
{reset_url}

このリンクは1時間有効です。

もしこのリクエストをしていない場合は、このメールを無視してください。
"""
    
    print(f"  [send_password_reset_email] Calling send_email (text only, no HTML)...")
    result = send_email(email, "パスワード再設定のご案内", text_body, html_body=None)
    print(f"  [send_password_reset_email] Email sent successfully! Message ID: {result}")
    return result
