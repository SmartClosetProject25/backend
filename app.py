from flask import Flask, request, jsonify, send_file, render_template
from dotenv import load_dotenv
import json
import os

# Blueprintインポート
from routes.httprequest import http_request
from services.auth import auth_bp
from routes.weather import weather_api
from services.user_pref import user_pref
from routes.generate import generate_bp
from routes.suggest import suggest_bp

# モデルインポート
from models.coordinate_model import CoordinateModel

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
    try:
        # user_idパラメータを取得（オプション）
        user_id = 1
        
        # coordinatesテーブルからデータを取得
        coordinates = CoordinateModel.get_coordinates_by_user(user_id)
        
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

@app.route('/view_coordinate', methods=['GET'])
def view_coordinate():
    """
    coordinate_idまたはimage_urlパラメータを受け取り、HTMLページを返す
    """
    try:
        coordinate_id = request.args.get('coordinate_id')
        image_url = request.args.get('image_url')
        
        # どちらかのパラメータが必要
        if not coordinate_id and not image_url:
            return jsonify({
                "status": "error",
                "message": "coordinate_idまたはimage_urlパラメータが必要です"
            }), 400
        
        # coordinate_idが指定されている場合、データベースから画像URLを取得
        if coordinate_id:
            try:
                coordinate_id_int = int(coordinate_id)
                coordinate = CoordinateModel.get_coordinate_by_id(coordinate_id_int)
                
                if not coordinate:
                    return jsonify({
                        "status": "error",
                        "message": f"coordinate_id {coordinate_id} が見つかりません"
                    }), 404
                
                # genimg_pathが存在する場合、それを使用
                if coordinate.get('genimg_path'):
                    image_url = coordinate['genimg_path']
                else:
                    return jsonify({
                        "status": "error",
                        "message": f"coordinate_id {coordinate_id} に画像が設定されていません"
                    }), 404
            except ValueError:
                return jsonify({
                    "status": "error",
                    "message": "coordinate_idは数値である必要があります"
                }), 400
        
        # HTMLテンプレートをレンダリングして返す
        return render_template('generated.html', image_url=image_url, coordinate_id=coordinate_id)
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

