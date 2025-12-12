from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv
import json, time
import os
import shutil

#! googleAI関係インポート＜＜これ消すと動く
import services.ai.generate_image as generateImg
import services.ai.ai_outfit_suggestion as aiOutfitSuggestion

# Blueprintインポート
from routes.httprequest import http_request
from services.auth import auth_bp
from routes.weather import weather_api

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
# # from services.hantei import hantei_bp
from services.auth import auth_bp
# # app.register_blueprint(hantei_bp, url_prefix='/')
app.register_blueprint(auth_bp, url_prefix='/')
app.register_blueprint(http_request, url_prefix='/')
app.register_blueprint(weather_api, url_prefix='/')

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

@app.route('/generate_image', methods=['POST'])
def generate_image():
    data = request.get_json()

    print(f"Received data: {data}")

    image_paths = data.get('image_paths', [])

    print(f"Received image paths: {image_paths}")
    
    # image_pathsから各画像パスを順序で取得（最初から順にトップス、ボトムス、アウター）
    clothing_image_path_top = image_paths[0].lstrip('/') if len(image_paths) > 0 else None
    clothing_image_path_bottom = image_paths[1].lstrip('/') if len(image_paths) > 1 else None
    clothing_image_path_outer = image_paths[2].lstrip('/') if len(image_paths) > 2 else None
    
    print(f"分類された画像パス:")
    print(f"  Top: {clothing_image_path_top}")
    print(f"  Bottom: {clothing_image_path_bottom}")
    print(f"  Outer: {clothing_image_path_outer}")
    
    # 必須パス（top、bottom）のチェック
    if not clothing_image_path_top or not clothing_image_path_bottom:
        return jsonify({
            'status': 'error',
            'message': 'トップスとボトムスの画像パスが必要です'
        }), 400
    
    try:
        # テスト画像を使用する場合はコメントアウトを解除
        use_test_image = True
        # use_test_image = False
        
        if use_test_image:
            # テスト画像のURLを返すだけ
            image_url = "/static/images/generated/test_generated.png"
            print(f"テスト用画像を使用: {image_url}")
        else:
            # 実際のAPIを呼び出す場合
            image_url = generateImg.main(
                # TODO: ユーザーIDに応じたモデル画像のパスに変更してください
                human_image_path="static/images/1/model/male_model.png",
                clothing_image_path_top=clothing_image_path_top,
                clothing_image_path_bottom=clothing_image_path_bottom,
                clothing_image_path_outer=clothing_image_path_outer
            )
            print(f"画像を生成し、static/images/generated/に保存しました: {image_url}")
        
        # バックエンドのベースURLを取得（リクエストから）
        # Androidアプリからアクセスする場合は、実際のサーバーURLに置き換える必要があります
        base_url = request.host_url.rstrip('/')
        full_image_url = f"{base_url}{image_url}"
        
        print(f"画像URL(相対パス): {image_url}")
        print(f"画像URL(完全URL): {full_image_url}")
        
        return jsonify({
            'status': 'success',
            'image_url': image_url,  # 相対パス（/static/images/generated/{filename}）
            'image_url_full': full_image_url  # 完全なURL（CoilのAsyncImageで使用可能）
        }), 200
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/send_today_plan', methods=['POST'])
def send_today_plan():
    try:
        # 今日の予定データを取得
        data = request.get_json()
        print("受信した今日の予定データ:")
        print(json.dumps(data, ensure_ascii=False, indent=2))

        # テスト用: 固定のテストデータを使用（APIを呼ばない）
        test_data = {
            "proposals": [
                {
                    "pattern": 1,
                    "items": {
                        "tops": {
                            "id": 6,
                            "item_name": "白シャツ",
                            "image_path": "/static/images/1/clothes/t003.jpg",
                            "taste": [
                                "きれいめ",
                                "カジュアル",
                                "フォーマル"
                            ]
                        },
                        "bottoms": {
                            "id": 13,
                            "item_name": "黒スラックス",
                            "image_path": "/static/images/1/clothes/b002.jpg",
                            "taste": [
                                "きれいめ",
                                "フォーマル"
                            ]
                        },
                        "outer": {
                            "id": 18,
                            "item_name": "ネイビーテーラードジャケット",
                            "image_path": "/static/images/1/clothes/o001.jpg",
                            "taste": [
                                "きれいめ",
                                "フォーマル"
                            ]
                        }
                    },
                    "item_ids": [
                        6,
                        13,
                        18
                    ],
                    "reason": "22℃でディナー、降水確率90%という条件に対し、室内での食事をメインに想定した、 きちんと感のあるきれいめコーディネートです。ホ ワイトの長袖シャツとブラックスラックスは、気温 に合っており、ディナーに相応しい上品さがありま す。ブラックのテーラードジャケットを羽織ること で、フォーマルな場にも適応しつつ、ポリエステル 素材は小雨程度なら対応しやすいでしょう。全体を モノトーンでまとめ、洗練された印象を与えます。"
                },
                {
                    "pattern": 2,
                    "items": {
                        "tops": {
                            "id": 10,
                            "item_name": "サックスブルーシャツ",
                            "image_path": "/static/images/1/clothes/t007.jpg",
                            "taste": [
                                "きれいめ",
                                "カジュアル"
                            ]
                        },
                        "bottoms": {
                            "id": 16,
                            "item_name": "黒デニムパンツ",
                            "image_path": "/static/images/1/clothes/b005.jpg",
                            "taste": [
                                "カジュアル",
                                "きれいめ"
                            ]
                        },
                        "outer": {
                            "id": 20,
                            "item_name": "ベージュトレンチコート",
                            "image_path": "/static/images/1/clothes/o003.jpg",
                            "taste": [
                                "きれいめ",
                                "トラッド"
                            ]
                        }
                    },
                    "item_ids": [
                        10,
                        16,
                        20
                    ],
                    "reason": "22℃で雨のディナーに対応する、 きれいめカジュアルなコーディネートです。ライト ブルーのシャツとブラックスリムデニムで、清潔感 とスマートさを演出します。アウターにはベージュ のトレンチコートを選び、ディナーの場にふさわし い上品さと季節感をプラス。綿素材ですが、22℃という気温には適しており、降水確率90%に対しては傘を併用することで対応し、屋内に入れば脱いで快適に 過ごすことを想定しています。"
                }
            ]
        }
        
        # テストデータを使用する場合はコメントアウトを解除
        use_test_data = True
        # use_test_data = False
        
        if use_test_data:
            result = test_data
            print("テストデータを使用しました")
        else:
            # user_idを取得(dataから、またはリクエストパラメータから)
            user_id = 1
            # user_id = data.get('user_id') or request.args.get('user_id')
            if user_id:
                user_id = int(user_id)
            else:
                # user_idが指定されていない場合はエラーを返す
                return jsonify({'error': 'user_id is required'}), 400

            # 今日の予定データを生成(データベースからアイテムを取得)
            result = aiOutfitSuggestion.generate_outfit_suggestion(data, user_id=user_id)
            print("実際のAPIを呼び出しました")
        
        print("生成されたコーディネート:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # フロントエンドに結果を返す
        return jsonify(result), 200

    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

