from flask import Flask, request, jsonify
from dotenv import load_dotenv
import json

#! googleAI関係インポート＜＜これ消すと動く
# import services.ai.generate_image as generateImg
# import services.ai.ai_outfit_suggestion as aiOutfitSuggestion

# Blueprintインポート
from routes.httprequest import http_request

app = Flask(__name__)

# CORSを有効化（フロントエンドからのリクエストを許可）
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# 環境変数のロード
load_dotenv()

# Blueprintの登録
# # from services.hantei import hantei_bp
# from services.auth import auth_bp
# # app.register_blueprint(hantei_bp, url_prefix='/')
# app.register_blueprint(auth_bp, url_prefix='/')
app.register_blueprint(http_request, url_prefix='/')

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

@app.route('/outfit_suggestion')
def outfit_suggestion():
    try:
        result = aiOutfitSuggestion.generate_outfit_suggestion(
            date="2025年11月21日",
            weather="晴れ",
            temperature=15.5,
            schedule="友達とディナー"
        )
        return json.dumps(result, ensure_ascii=False, indent=2), 200, {'Content-Type': 'application/json; charset=utf-8'}
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False), 400, {'Content-Type': 'application/json; charset=utf-8'}

@app.route('/generate_image')
def generate_image():
    
    try:
        result = generateImg.main(
            human_image_path="images/input/male_model.png",
            clothing_image_path_top="images/input/clothes_a.png",
            clothing_image_path_bottom="images/input/clothes_e.png"
        )
        return json.dumps({'message': 'Check new image in images/output/output.png !!'}, ensure_ascii=False), 200, {'Content-Type': 'application/json; charset=utf-8'}
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False), 400, {'Content-Type': 'application/json; charset=utf-8'}

@app.route('/send_today_plan', methods=['POST'])
def send_today_plan():
    try:
        # 今日の予定データを取得
        data = request.get_json()
        print("受信した今日の予定データ:")
        print(json.dumps(data, ensure_ascii=False, indent=2))

        # 今日の予定データを生成
        result = aiOutfitSuggestion.generate_outfit_suggestion(data)
        print("生成されたコーディネート:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # フロントエンドに結果を返す
        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

