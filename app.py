from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv
import json
import os

#! googleAI関係インポート＜＜これ消すと動く
# generate_imageとsend_today_planはroutes/generate.pyとroutes/suggest.pyに移動したため、ここでは不要
# import services.ai.generate_image as generateImg
# import services.ai.ai_outfit_suggestion as aiOutfitSuggestion

# Blueprintインポート
from routes.httprequest import http_request
from services.auth import auth_bp
from routes.weather import weather_api
from services.user_pref import user_pref
from routes.generate import generate_bp
from routes.suggest import suggest_bp

# データベース接続インポート
from utils.db_con import get_db_connection

app = Flask(__name__, static_folder='static', static_url_path='/static')

# CORSを有効化(フロントエンドからのリクエストを許可)
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# 画像送信の共通処理（CoilのAsyncImage対応）
def serve_image(image_path):
    """Content-Lengthを設定してチャンクエンコーディングを無効化"""
    if not os.path.exists(image_path):
        return jsonify({'error': 'Image not found'}), 404
    
    file_size = os.path.getsize(image_path)
    ext = os.path.splitext(image_path)[1].lower()
    mimetype = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', 
                '.gif': 'image/gif', '.webp': 'image/webp'}.get(ext, 'image/png')
    
    response = send_file(image_path, mimetype=mimetype, as_attachment=False)
    response.headers['Content-Length'] = str(file_size)
    response.headers.pop('Transfer-Encoding', None)
    return response

@app.route('/static/images/generated/<path:filename>')
def serve_generated_image(filename):
    return serve_image(os.path.join('static', 'images', 'generated', filename))

@app.route('/static/images/<int:user_id>/<path:subpath>')
def serve_user_image(user_id, subpath):
    return serve_image(os.path.join('static', 'images', str(user_id), subpath))

# 環境変数のロード
load_dotenv()

# Blueprintの登録
# from services.hantei import hantei_bp
# from services.auth import auth_bp
# app.register_blueprint(hantei_bp, url_prefix='/')
app.register_blueprint(auth_bp, url_prefix='/')
app.register_blueprint(http_request, url_prefix='/')
app.register_blueprint(weather_api, url_prefix='/')
app.register_blueprint(user_pref, url_prefix='/')
app.register_blueprint(generate_bp, url_prefix='/')
app.register_blueprint(suggest_bp, url_prefix='/')

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

# /generate_image と /send_today_plan は routes/generate.py と routes/suggest.py に移動しました

@app.route('/get_coordinates', methods=['GET'])
def get_coordinates():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # user_idパラメータを取得（オプション）
        user_id = 1
        
        # coordinatesテーブルからデータを取得し、関連するアイテム情報もJOINで取得
        sql = """
            SELECT 
                c.coordinate_id,
                c.user_id,
                c.top_id,
                c.bottom_id,
                c.outer_id,
                c.scene,
                c.features_json,
                c.genimg_path,
                c.rating,
                c.created_at,
                top.item_name as top_name,
                top.image_path as top_image_path,
                bottom.item_name as bottom_name,
                bottom.image_path as bottom_image_path,
                outer_item.item_name as outer_name,
                outer_item.image_path as outer_image_path
            FROM coordinates c
            LEFT JOIN items top ON c.top_id = top.item_id
            LEFT JOIN items bottom ON c.bottom_id = bottom.item_id
            LEFT JOIN items outer_item ON c.outer_id = outer_item.item_id
        """
        
        # user_idが指定されている場合はフィルタリング
        params = []
        if user_id:
            sql += " WHERE c.user_id = %s"
            params.append(user_id)
        
        sql += " ORDER BY c.created_at DESC, c.coordinate_id DESC"
        
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        
        # レスポンス用のデータを整形
        coordinates = []
        for row in rows:
            # features_jsonをパース（既にJSON形式の場合はそのまま使用）
            features = row['features_json']
            if isinstance(features, str):
                try:
                    features = json.loads(features)
                except json.JSONDecodeError:
                    features = {}
            
            coordinate_data = {
                "coordinate_id": row['coordinate_id'],
                "user_id": row['user_id'],
                "top_id": row['top_id'],
                "bottom_id": row['bottom_id'],
                "outer_id": row['outer_id'],
                "scene": row['scene'],
                "features": features,
                "genimg_path": row['genimg_path'],
                "rating": row['rating'],
                "created_at": row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else None,
                "top": {
                    "id": row['top_id'],
                    "name": row['top_name'],
                    "image_path": row['top_image_path']
                },
                "bottom": {
                    "id": row['bottom_id'],
                    "name": row['bottom_name'],
                    "image_path": row['bottom_image_path']
                }
            }
            
            # outerアイテムが存在する場合のみ追加
            if row['outer_id']:
                coordinate_data["outer"] = {
                    "id": row['outer_id'],
                    "name": row['outer_name'],
                    "image_path": row['outer_image_path']
                }
            
            coordinates.append(coordinate_data)
        
        return jsonify({
            "status": "success",
            "coordinates": coordinates,
            "count": len(coordinates)
        }), 200
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
        
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

