from flask import Flask, request
from dotenv import load_dotenv
import os, json
import services.ai.generate_image as generateImg
import services.ai.ai_outfit_suggestion as aiOutfitSuggestion
import mysql.connector
app = Flask(__name__)

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="your_password",
        database="your_db",
    )



# 環境変数のロード
load_dotenv()

# Blueprintの登録
# # from services.hantei import hantei_bp
# from services.auth import auth_bp
# # app.register_blueprint(hantei_bp, url_prefix='/')
# app.register_blueprint(auth_bp, url_prefix='/')


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
    
    
@app.route('/add_item', methods=['POST'])
def add_item():
    try:
        # --- multipart で送られてきた文字データを取得 ---
        user_id = request.form.get('userId')
        item_name = request.form.get('itemName')
        color_id = request.form.get('color')
        pattern_id = request.form.get('pattern')
        size = request.form.get('size')
        brand = request.form.get('brand')
        category_detail_id = request.form.get('category')
        material = request.form.get('material')
        feature = request.form.get('feature')
        season = request.form.get('season')
        taste = request.form.get('taste')



        conn = get_connection()
        cursor = conn.cursor()

        # --- INSERT ---
        sql = """
            INSERT INTO items (color_id, pattern_id, category_detail_id, user_id, size, brand, material, feature, season, taste, created_at, updated_at, is_deleted)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,NOW(), NOW(), 0)
        """

        cursor.execute(sql, ( color_id, pattern_id, category_detail_id, user_id, size, brand, material, feature, season, taste))

        return 'OK', 200
    
    except Exception as e:
        if conn:
            conn.rollback()
        print({"status": "error", "message": str(e)})
        return 'Error', 400

    finally:
        if conn:
            conn.close()
            
@app.route('/get_item')
def get_item():
    return 'get_item'


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
        data = request.get_json()
        print("受信した今日の予定データ:")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        if not data or 'plan' not in data:
            return json.dumps({'error': 'Missing plan data'}, ensure_ascii=False), 400, {'Content-Type': 'application/json; charset=utf-8'}
        plan = data['plan']
        return json.dumps({'message': 'Plan received successfully'}, ensure_ascii=False), 200, {'Content-Type': 'application/json; charset=utf-8'}
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False), 400, {'Content-Type': 'application/json; charset=utf-8'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

