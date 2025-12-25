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
            image_url = "/static/images/generated/generated_20251224_181137_d7b03acc.jpg"
            print(f"テスト用画像を使用: {image_url}")
        else:
            # 実際のAPIを呼び出す場合
            image_url = generateImg.main(
                # TODO: ユーザーIDに応じたモデル画像のパスに変更してください
                human_image_path="static/images/1/model/Image2.jpg",
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
        
        # 提案されたコーディネートをデータベースに保存
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 各提案をcoordinatesテーブルに保存
            saved_coordinate_ids = []
            if 'proposals' in result and isinstance(result['proposals'], list):
                for proposal in result['proposals']:
                    if 'items' in proposal and 'tops' in proposal['items'] and 'bottoms' in proposal['items']:
                        top_id = proposal['items']['tops']['id']
                        bottom_id = proposal['items']['bottoms']['id']
                        
                        # アイテムの詳細情報（seasons, color_name）をデータベースから取得
                        item_ids = [top_id, bottom_id]
                        placeholders = ','.join(['%s'] * len(item_ids))
                        item_sql = f"""
                            SELECT 
                                i.item_id,
                                i.seasons,
                                col.color_name
                            FROM items i
                            INNER JOIN colors col ON i.color_id = col.color_id
                            WHERE i.item_id IN ({placeholders}) AND i.is_deleted = 0
                        """
                        cursor.execute(item_sql, tuple(item_ids))
                        item_rows = cursor.fetchall()
                        
                        # アイテム情報を辞書に変換
                        items_info = {row['item_id']: row for row in item_rows}
                        
                        # sceneを決定（tasteから推測）
                        tops_taste = proposal['items']['tops'].get('taste', [])
                        bottoms_taste = proposal['items']['bottoms'].get('taste', [])
                        all_taste = list(set(tops_taste + bottoms_taste))
                        
                        # tasteからsceneを推測（優先順位: ストリート > カジュアル > きれいめ > フォーマル）
                        scene = 'カジュアル'  # デフォルト
                        if 'ストリート' in all_taste:
                            scene = 'ストリート'
                        elif 'カジュアル' in all_taste:
                            scene = 'カジュアル'
                        elif 'きれいめ' in all_taste or 'フォーマル' in all_taste:
                            scene = 'きれいめ'
                        
                        # styleはsceneと同じ値を使用
                        style = scene
                        
                        # seasonを取得（トップスとボトムスのseasonsを統合）
                        top_seasons = items_info.get(top_id, {}).get('seasons', '')
                        bottom_seasons = items_info.get(bottom_id, {}).get('seasons', '')
                        
                        # シーズンを統合（重複を除去）
                        all_seasons = []
                        if top_seasons:
                            all_seasons.extend([s.strip() for s in top_seasons.split(',')])
                        if bottom_seasons:
                            all_seasons.extend([s.strip() for s in bottom_seasons.split(',')])
                        
                        # 重複を除去してソート
                        unique_seasons = sorted(list(set([s for s in all_seasons if s])))
                        season_str = ','.join(unique_seasons) if unique_seasons else ''
                        
                        # color_schemeを生成（トップス×ボトムス）
                        top_color = items_info.get(top_id, {}).get('color_name', '')
                        bottom_color = items_info.get(bottom_id, {}).get('color_name', '')
                        color_scheme = f"{top_color}×{bottom_color}" if top_color and bottom_color else ''
                        
                        # features_jsonを作成（既存のデータ形式に合わせる）
                        features_data = {
                            "style": style,
                            "season": season_str,
                            "color_scheme": color_scheme
                        }
                        
                        features_json = json.dumps(features_data, ensure_ascii=False)
                        
                        # coordinatesテーブルに挿入
                        insert_sql = """
                            INSERT INTO coordinates (top_id, bottom_id, scene, features_json, created_at)
                            VALUES (%s, %s, %s, %s, NOW())
                        """
                        cursor.execute(insert_sql, (top_id, bottom_id, scene, features_json))
                        saved_coordinate_ids.append(cursor.lastrowid)
                        
                        print(f"コーディネートを保存しました: coordinate_id={cursor.lastrowid}, top_id={top_id}, bottom_id={bottom_id}, scene={scene}")
                        print(f"  features_json: {features_json}")
            
            conn.commit()
            print(f"合計{len(saved_coordinate_ids)}件のコーディネートをデータベースに保存しました")
            
        except Exception as db_error:
            print(f"データベース保存エラー: {str(db_error)}")
            import traceback
            traceback.print_exc()
            # データベースエラーが発生しても、提案結果は返す
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
        
        # フロントエンドに結果を返す
        return jsonify(result), 200

    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@app.route('/get_coordinates', methods=['GET'])
def get_coordinates():
    """coordinatesテーブルからデータを取得するエンドポイント"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # coordinatesテーブルからデータを取得し、関連するアイテム情報もJOINで取得
        sql = """
            SELECT 
                c.coordinate_id,
                c.top_id,
                c.bottom_id,
                c.scene,
                c.features_json,
                c.created_at,
                top.item_name as top_name,
                top.image_path as top_image_path,
                bottom.item_name as bottom_name,
                bottom.image_path as bottom_image_path
            FROM coordinates c
            LEFT JOIN items top ON c.top_id = top.item_id
            LEFT JOIN items bottom ON c.bottom_id = bottom.item_id
            ORDER BY c.created_at DESC, c.coordinate_id DESC
        """
        
        cursor.execute(sql)
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
                "top_id": row['top_id'],
                "bottom_id": row['bottom_id'],
                "scene": row['scene'],
                "features": features,
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

