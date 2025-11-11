# services/auth.py
from flask import Blueprint, jsonify, request
from utils.db_con import get_conn
from utils.email_service import send_password_reset_email
import time
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint("auth", __name__)

def now_ms() -> int:
    """現在時刻をミリ秒で返す"""
    return int(time.time() * 1000)

def now_datetime():
    """現在時刻をDATETIME形式の文字列で返す"""
    from datetime import datetime
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@auth_bp.post("/auth/password-reset/request")
def request_password_reset():
    """パスワード再設定メール送信リクエスト"""
    data = request.get_json(force=True) or {}
    email = data.get("email")
    
    if not email:
        return jsonify({"error": "email is required"}), 400
    
    # ユーザーが存在するか確認
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT user_id, email FROM users WHERE email=%s AND is_deleted=0", (email,))
        user = cur.fetchone()
        cur.close()
        
        if not user:
            # セキュリティのため、ユーザーが存在しない場合でも成功レスポンスを返す
            return jsonify({"ok": True, "message": "If the email exists, a password reset link has been sent"})
        
        # リセットトークンを生成
        token = secrets.token_urlsafe(32)
        
        # トークンの有効期限（1時間後）
        from datetime import datetime, timedelta
        expires_at = datetime.now() + timedelta(hours=1)
        
        # トークンをデータベースに保存
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO password_reset_tokens(user_id, token, expires_at, created_at)
               VALUES(%s, %s, %s, %s)""",
            (user["user_id"], token, expires_at.strftime('%Y-%m-%d %H:%M:%S'), now_datetime())
        )
        cur.close()
        conn.commit()
        
        # メール送信
        try:
            send_password_reset_email(user["email"], token)
            return jsonify({"ok": True, "message": "Password reset email sent"})
        except Exception as e:
            # メール送信失敗時はトークンを削除
            cur = conn.cursor()
            cur.execute("DELETE FROM password_reset_tokens WHERE token=%s", (token,))
            cur.close()
            conn.commit()
            return jsonify({"error": "Failed to send email", "details": str(e)}), 500
            
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@auth_bp.post("/auth/password-reset/verify-token")
def verify_reset_token():
    """トークンの有効性を確認（Androidアプリ用）"""
    data = request.get_json(force=True) or {}
    token = data.get("token")
    
    if not token:
        return jsonify({"error": "token is required"}), 400
    
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT user_id, expires_at, used 
               FROM password_reset_tokens 
               WHERE token=%s AND used=0""",
            (token,)
        )
        token_data = cur.fetchone()
        cur.close()
        
        if not token_data:
            return jsonify({"valid": False, "error": "Invalid token"}), 400
        
        # 有効期限チェック
        from datetime import datetime
        expires_at = token_data["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
        
        if expires_at < datetime.now():
            return jsonify({"valid": False, "error": "Token expired"}), 400
        
        return jsonify({"valid": True, "user_id": token_data["user_id"]})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@auth_bp.post("/auth/password-reset/confirm")
def confirm_password_reset():
    """パスワード再設定の実行"""
    data = request.get_json(force=True) or {}
    token = data.get("token")
    new_password = data.get("new_password")
    
    if not token or not new_password:
        return jsonify({"error": "token and new_password are required"}), 400
    
    if len(new_password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        # トークンの検証
        cur.execute(
            """SELECT token_id, user_id, expires_at, used 
               FROM password_reset_tokens 
               WHERE token=%s AND used=0""",
            (token,)
        )
        token_data = cur.fetchone()
        
        if not token_data:
            return jsonify({"error": "Invalid or expired token"}), 400
        
        # 有効期限チェック
        from datetime import datetime
        expires_at = token_data["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
        
        if expires_at < datetime.now():
            return jsonify({"error": "Token has expired"}), 400
        
        # パスワードをハッシュ化
        password_hash = generate_password_hash(new_password)
        
        # パスワードを更新
        cur.execute(
            "UPDATE users SET password=%s, updated_at=%s WHERE user_id=%s",
            (password_hash, now_datetime(), token_data["user_id"])
        )
        
        # トークンを無効化
        cur.execute(
            "UPDATE password_reset_tokens SET used=1 WHERE token_id=%s",
            (token_data["token_id"],)
        )
        
        cur.close()
        conn.commit()
        
        return jsonify({"ok": True, "message": "Password has been reset"})
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@auth_bp.post("/auth/test-email")
def test_email():
    """メール送信テストエンドポイント"""
    data = request.get_json(force=True) or {}
    email = data.get("email")
    
    if not email:
        return jsonify({"error": "email is required"}), 400
    
    try:
        from utils.email_service import send_email
        
        text_body = """
これはGmail APIのテストメールです。

メール送信機能が正常に動作しています。
"""
        
        html_body = """
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #4CAF50;">Gmail API テストメール</h2>
                <p>これはGmail APIのテストメールです。</p>
                <p>メール送信機能が正常に動作しています。</p>
            </div>
        </body>
        </html>
        """
        
        message_id = send_email(email, "Gmail API テストメール", text_body, html_body)
        return jsonify({
            "ok": True,
            "message": "Test email sent successfully",
            "message_id": message_id
        })
        
    except Exception as e:
        return jsonify({"error": "Failed to send test email", "details": str(e)}), 500


