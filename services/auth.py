# # services/auth.py
# from flask import Blueprint, jsonify, request
# from utils.db_con import get_db_connection
# from utils.email_service import send_password_reset_email
# import time
# from datetime import datetime, timedelta
# import secrets
# import hashlib
# import hmac
# from werkzeug.security import generate_password_hash, check_password_hash

# auth_bp = Blueprint("auth", __name__)

# def now_ms() -> int:
#     """現在時刻をミリ秒で返す"""
#     return int(time.time() * 1000)

# def now_datetime():
#     """現在時刻をDATETIME形式の文字列で返す"""
#     return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# def hash_token(token: str) -> str:
#     """トークンをSHA-256でハッシュ化"""
#     return hashlib.sha256(token.encode()).hexdigest()

# def verify_token(input_token: str, stored_hash: str) -> bool:
#     """トークンを検証（タイミング攻撃対策）"""
#     input_hash = hash_token(input_token)
#     return hmac.compare_digest(input_hash, stored_hash)

# @auth_bp.post("/auth/password-reset/request")
# def request_password_reset():
#     """パスワード再設定メール送信リクエスト"""
#     print("=== Password reset request received ===")
    
#     data = request.get_json(force=True) or {}
#     email = data.get("email")
    
#     print(f"Request data: {data}")
#     print(f"Email: {email}")
    
#     if not email:
#         print("ERROR: Email is missing in request")
#         return jsonify({"error": "email is required"}), 400
    
#     # ユーザーが存在するか確認
#     conn = get_db_connection()
#     try:
#         print(f"Checking if user exists: {email}")
#         cur = conn.cursor(dictionary=True)
#         cur.execute("SELECT user_id, email FROM users WHERE email=%s AND is_deleted=0", (email,))
#         user = cur.fetchone()
#         cur.close()
        
#         if not user:
#             print(f"User not found: {email}")
#             # セキュリティのため、ユーザーが存在しない場合でも成功レスポンスを返す
#             return jsonify({"ok": True, "message": "If the email exists, a password reset link has been sent"})
        
#         print(f"User found: user_id={user['user_id']}, email={user['email']}")
        
#         # リセットトークンを生成
#         token = secrets.token_urlsafe(32)
#         print(f"Token generated: {token[:20]}...")
        
#         # トークンをハッシュ化
#         token_hash = hash_token(token)
#         print(f"Token hash: {token_hash[:20]}...")
        
#         # トークンの有効期限（1時間後）
#         expires_at = datetime.now() + timedelta(hours=1)
#         print(f"Token expires at: {expires_at}")
        
#         # トークンをハッシュ化してデータベースに保存
#         cur = conn.cursor()
#         cur.execute(
#             """INSERT INTO password_reset_tokens(user_id, token, expires_at, created_at)
#                VALUES(%s, %s, %s, %s)""",
#             (user["user_id"], token_hash, expires_at.strftime('%Y-%m-%d %H:%M:%S'), now_datetime())
#         )
#         cur.close()
#         conn.commit()
#         print("Token hash saved to database")
        
#         # メール送信
#         try:
#             print(f"Attempting to send email to: {user['email']}")
#             send_password_reset_email(user["email"], token)
#             print(f"SUCCESS: Password reset email sent to: {user['email']}")
#             return jsonify({"ok": True, "message": "Password reset email sent"})
#         except Exception as e:
#             print(f"ERROR: Failed to send email: {str(e)}")
#             print(f"Exception type: {type(e).__name__}")
#             import traceback
#             traceback.print_exc()
#             # メール送信失敗時はトークンを削除（ハッシュ化されたトークンで削除）
#             cur = conn.cursor()
#             token_hash = hash_token(token)
#             cur.execute("DELETE FROM password_reset_tokens WHERE token=%s", (token_hash,))
#             cur.close()
#             conn.commit()
#             return jsonify({"error": "Failed to send email", "details": str(e)}), 500
            
#     except Exception as e:
#         print(f"ERROR in request_password_reset: {str(e)}")
#         print(f"Exception type: {type(e).__name__}")
#         import traceback
#         traceback.print_exc()
#         conn.rollback()
#         return jsonify({"error": str(e)}), 500
#     finally:
#         conn.close()
#         print("Database connection closed")
#         print("=== End of password reset request ===\n")

# @auth_bp.post("/auth/password-reset/verify-token")
# def verify_reset_token():
#     """トークンの有効性を確認（Androidアプリ用）"""
#     data = request.get_json(force=True) or {}
#     token = data.get("token")
    
#     if not token:
#         return jsonify({"error": "token is required"}), 400
    
#     conn = get_db_connection()
#     try:
#         # トークンをハッシュ化して検索
#         token_hash = hash_token(token)
#         cur = conn.cursor(dictionary=True)
#         cur.execute(
#             """SELECT user_id, expires_at, used, token
#                 FROM password_reset_tokens 
#                 WHERE token=%s AND used=0""",
#             (token_hash,)
#         )
#         token_data = cur.fetchone()
#         cur.close()
        
#         if not token_data:
#             return jsonify({"valid": False, "error": "Invalid token"}), 400
        
#         # タイミング攻撃対策のため、ハッシュを再検証
#         if not verify_token(token, token_data["token"]):
#             return jsonify({"valid": False, "error": "Invalid token"}), 400
        
#         # 有効期限チェック
#         expires_at = token_data["expires_at"]
#         if isinstance(expires_at, str):
#             expires_at = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
        
#         if expires_at < datetime.now():
#             return jsonify({"valid": False, "error": "Token expired"}), 400
        
#         return jsonify({"valid": True, "user_id": token_data["user_id"]})
        
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
#     finally:
#         conn.close()

# @auth_bp.post("/auth/password-reset/confirm")
# def confirm_password_reset():
#     """パスワード再設定の実行"""
#     data = request.get_json(force=True) or {}
#     token = data.get("token")
#     new_password = data.get("new_password")
    
#     if not token or not new_password:
#         return jsonify({"error": "token and new_password are required"}), 400
    
#     if len(new_password) < 8:
#         return jsonify({"error": "Password must be at least 8 characters"}), 400
    
#     # scrypt:32768:8:1$JmzIPKQ2zXiIdPEr$0247ff9f0bfd9958d3007e8178e267ea9cefa86a09ed8453dba24b1782478e7e9ae1f97905885ad6ebed788491ac4e7a7f37ddb25e806a78e531a5bdd91ebf3b
    
#     conn = get_db_connection()
#     try:
#         # トークンをハッシュ化して検証
#         token_hash = hash_token(token)
#         cur = conn.cursor(dictionary=True)
#         cur.execute(
#             """SELECT token_id, user_id, expires_at, used, token
#                 FROM password_reset_tokens 
#                 WHERE token=%s AND used=0""",
#             (token_hash,)
#         )
#         token_data = cur.fetchone()
        
#         if not token_data:
#             return jsonify({"error": "Invalid or expired token"}), 400
        
#         # タイミング攻撃対策のため、ハッシュを再検証
#         if not verify_token(token, token_data["token"]):
#             return jsonify({"error": "Invalid or expired token"}), 400
        
#         # 有効期限チェック
#         expires_at = token_data["expires_at"]
#         if isinstance(expires_at, str):
#             expires_at = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
        
#         if expires_at < datetime.now():
#             return jsonify({"error": "Token has expired"}), 400
        
#         # パスワードをハッシュ化
#         password_hash = generate_password_hash(new_password)
        
#         # パスワードを更新
#         cur.execute(
#             "UPDATE users SET password=%s, updated_at=%s WHERE user_id=%s",
#             (password_hash, now_datetime(), token_data["user_id"])
#         )
        
#         # トークンを無効化
#         cur.execute(
#             "UPDATE password_reset_tokens SET used=1 WHERE token_id=%s",
#             (token_data["token_id"],)
#         )
        
#         cur.close()
#         conn.commit()
        
#         return jsonify({"ok": True, "message": "Password has been reset"})
        
#     except Exception as e:
#         conn.rollback()
#         return jsonify({"error": str(e)}), 500
#     finally:
#         conn.close()

# @auth_bp.get("/auth/test-email")
# def test_email():
#     """メール送信テストエンドポイント"""
#     email = request.args.get("email")
    
#     if not email:
#         return jsonify({"error": "email is required"}), 400
    
#     try:
#         from utils.email_service import send_email
        
#         text_body = """
# これはGmail APIのテストメールです。

# メール送信機能が正常に動作しています。
# """
        
#         html_body = """
#         <html>
#         <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
#             <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
#                 <h2 style="color: #4CAF50;">Gmail API テストメール</h2>
#                 <p>これはGmail APIのテストメールです。</p>
#                 <p>メール送信機能が正常に動作しています。</p>
#             </div>
#         </body>
#         </html>
#         """
        
#         message_id = send_email(email, "Gmail API テストメール", text_body, html_body)
#         return jsonify({
#             "ok": True,
#             "message": "Test email sent successfully",
#             "message_id": message_id
#         })
        
#     except Exception as e:
#         return jsonify({"error": "Failed to send test email", "details": str(e)}), 500

# @auth_bp.post("/login")
# def login():
#     """ログイン処理"""
#     print("=== Login request received ===")
    
#     data = request.get_json(force=True) or {}
#     email = data.get("email")
#     password = data.get("password")
    
#     print(f"Request data: {data}")
#     print(f"Email: {email}")
    
#     if not email or not password:
#         print("ERROR: Email or password is missing")
#         return jsonify({"error": "email and password are required"}), 400
    
#     conn = get_db_connection()
#     try:
#         print(f"Checking user credentials: {email}")
#         cur = conn.cursor(dictionary=True)
#         cur.execute(
#             "SELECT user_id, email, password FROM users WHERE email=%s AND is_deleted=0",
#             (email,)
#         )
#         user = cur.fetchone()
#         cur.close()
        
#         if not user:
#             print(f"User not found: {email}")
#             return jsonify({"error": "Invalid email or password"}), 401
        
#         # パスワード検証
#         if not check_password_hash(user["password"], password):
#             print(f"Password mismatch for user: {email}")
#             return jsonify({"error": "Invalid email or password"}), 401
        
#         print(f"SUCCESS: Login successful for user_id={user['user_id']}, email={user['email']}")
#         return jsonify({
#             "ok": True,
#             "message": "Login successful",
#             "user_id": user["user_id"],
#             "email": user["email"]
#         }), 200
        
#     except Exception as e:
#         print(f"ERROR in login: {str(e)}")
#         print(f"Exception type: {type(e).__name__}")
#         import traceback
#         traceback.print_exc()
#         return jsonify({"error": str(e)}), 500
#     finally:
#         conn.close()
#         print("Database connection closed")
#         print("=== End of login request ===\n")

# @auth_bp.post("/signup")
# def signup():
#     """新規登録処理"""
#     print("=== Signup request received ===")
    
#     data = request.get_json(force=True) or {}
#     email = data.get("email")
#     password = data.get("password")
#     image_path = data.get("image_path")  # オプション（画像パス）
    
#     print(f"Request data: {data}")
#     print(f"Email: {email}")
#     print(f"Image path: {image_path}")
    
#     if not email or not password:
#         print("ERROR: Email or password is missing")
#         return jsonify({"error": "email and password are required"}), 400
    
#     if len(password) < 8:
#         print("ERROR: Password too short")
#         return jsonify({"error": "Password must be at least 8 characters"}), 400
    
#     # メールアドレスの簡易バリデーション
#     if "@" not in email:
#         print("ERROR: Invalid email format")
#         return jsonify({"error": "Invalid email format"}), 400
    
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor(dictionary=True)
        
#         # 既存ユーザー確認
#         cur.execute("SELECT user_id FROM users WHERE email=%s", (email,))
#         existing = cur.fetchone()
        
#         if existing:
#             print(f"ERROR: Email already registered: {email}")
#             return jsonify({"error": "Email already registered"}), 400
        
#         # パスワードをハッシュ化
#         password_hash = generate_password_hash(password)
#         print(f"Password hashed successfully")
        
#         # ユーザー登録
#         cur.execute(
#             "INSERT INTO users (email, password, created_at, updated_at) VALUES (%s, %s, %s, %s)",
#             (email, password_hash, now_datetime(), now_datetime())
#         )
#         user_id = cur.lastrowid
#         cur.close()
#         conn.commit()
        
#         print(f"SUCCESS: User registered successfully - user_id={user_id}, email={email}")
#         return jsonify({
#             "ok": True,
#             "message": "Signup successful",
#             "user_id": user_id,
#             "email": email
#         }), 201
        
#     except Exception as e:
#         print(f"ERROR in signup: {str(e)}")
#         print(f"Exception type: {type(e).__name__}")
#         import traceback
#         traceback.print_exc()
#         conn.rollback()
#         return jsonify({"error": str(e)}), 500
#     finally:
#         conn.close()
#         print("Database connection closed")
#         print("=== End of signup request ===\n")


