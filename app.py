from flask import Flask, request
from dotenv import load_dotenv
import os
from utils.db_con import init_db

app = Flask(__name__)

# 環境変数のロード
load_dotenv()

# Blueprintの登録
# from services.hantei import hantei_bp
# app.register_blueprint(hantei_bp, url_prefix='/')

# 起動確認用のルート
@app.route('/')
def hello_world():
    return 'Hello, World!'
@app.route('/update_profile', methods=['POST'])
def update_profile():
    try:
        profile_data = request.get_json()
        print("受信したプロフィールデータ:")
        print(json.dumps(profile_data, ensure_ascii=False, indent=2))
        return 'OK', 200
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return 'Error', 400

@app.route('/login')
def login():
    return 'Login Page'

@app.route('/signup')
def signup():
    return 'Signup Page'



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

