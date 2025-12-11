from flask import Flask, request, jsonify
from dotenv import load_dotenv
import json, time
import os
import shutil

#! googleAI関係インポート＜＜これ消すと動く
#import services.ai.generate_image as generateImg
#import services.ai.ai_outfit_suggestion as aiOutfitSuggestion

# Blueprintインポート
from routes.httprequest import http_request
from services.auth import auth_bp

app = Flask(__name__, static_folder='static', static_url_path='/static')

# CORSを有効化(フロントエンドからのリクエストを許可)
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
app.register_blueprint(auth_bp, url_prefix='/')
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

@app.route('/generate_image', methods=['POST'])
def generate_image():
    data = request.get_json()

    item_ids = data.get('item_ids')

    print(f"Received item IDs: {item_ids}")
    
    
    try:
        # テスト用: 既存の画像ファイルを使用（APIを呼ばない）
        test_image_path = "images/outputs/male_model_mini_2025-12-09_16-22-29.png"
        
        # テスト画像を使用する場合はコメントアウトを解除
        use_test_image = True
        # use_test_image = False
        
        if use_test_image and test_image_path and os.path.exists(test_image_path):
            # static/images/generated/フォルダにコピー
            save_dir = "static/images/generated"
            os.makedirs(save_dir, exist_ok=True)
            
            # ファイル名を取得してコピー
            filename = os.path.basename(test_image_path)
            dest_path = os.path.join(save_dir, filename)
            shutil.copy2(test_image_path, dest_path)
            
            image_url = f"/static/images/generated/{filename}"
            print(f"テスト用画像を使用: {image_url}")
        else:
            # 実際のAPIを呼び出す場合（テスト用画像を使用しない場合）
            # アウター画像はオプショナル（Noneの場合は3枚のみ使用）
            image_url = generateImg.main(
                human_image_path="images/input/male_model_mini.png",
                clothing_image_path_top="images/input/clothes_f.png",
                clothing_image_path_bottom="images/input/clothes_e.png",
                clothing_image_path_outer="images/input/clothes_a.png"
            )
            print(f"実際のAPIを呼び出しました: {image_url}")
        
        # バックエンドのベースURLを取得（リクエストから）
        # Androidアプリからアクセスする場合は、実際のサーバーURLに置き換える必要があります
        base_url = request.host_url.rstrip('/')
        full_image_url = f"{base_url}{image_url}"
        
        print(f"画像URL: {full_image_url}")
        
        return jsonify({
            'status': 'success',
            'image_url': image_url,  # 相対パス
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
                        "tops": "T008",
                        "bottoms": "B002",
                        "outer": "O003"
                    },
                    "item_ids": [
                        "T008",
                        "B002",
                        "O003"
                    ],
                    "reason": "12月にしては異例の22℃という高い気温と、降水確率90%の 雨予報に対応した、きれいめカジュア ルなコーディネートです。トップスに は、22℃でも快適に過ごせる薄手の長袖シャツ（T008）を選びました。ライト ブルーの色合いが雨でどんよりしがち な気分を明るくしてくれます。ボトム スは、雨で濡れても比較的乾きやすく 、汚れも目立ちにくいブラックスラッ クス（B002）で、きれいめな印象を保 ちつつ機能性も考慮しました。アウタ ーには、降水確率90%のため必須となるトレンチコート（O003）を。綿素材で すがロング丈で多少の雨ならしのぐこ とができ、上品さを保ちながら雨対策 もできます。"
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

