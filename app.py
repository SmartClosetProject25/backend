from flask import Flask
from dotenv import load_dotenv
import os
from utils.db_con import init_db
import services.ai.generateImg as generateImg

app = Flask(__name__)

# 環境変数のロード
load_dotenv()

# データベースの初期化
init_db()
# Blueprintの登録
from services.hantei import hantei_bp
app.register_blueprint(hantei_bp, url_prefix='/')


@app.get("/health")
def health():
    return {"ok": True}
# 起動確認用のルート
@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/generate')
def generate():
    # 入力画像のパスを3つ指定
    image_human = "images/input/male_model.png"
    image_clothes_top = "images/input/clothes_c.png"
    image_clothes_bottom = "images/input/clothes_d.png"
    return generateImg.main(image_human, image_clothes_top, image_clothes_bottom)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
