from flask import Flask
from dotenv import load_dotenv
import os

app = Flask(__name__)

# 環境変数のロード
load_dotenv()

# Blueprintの登録
from services.hantei import hantei_bp
app.register_blueprint(hantei_bp, url_prefix='/')

# 起動確認用のルート
@app.route('/')
def hello_world():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
