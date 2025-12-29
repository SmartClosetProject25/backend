from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv
import json, time
import os
import shutil
import base64
import datetime
import uuid
from io import BytesIO
from PIL import Image, ImageOps

#! googleAI関係インポート＜＜これ消すと動く
import services.ai.generate_image as generateImg
import services.ai.ai_outfit_suggestion as aiOutfitSuggestion

# Blueprintインポート
from routes.httprequest import http_request
from services.auth import auth_bp
from routes.weather import weather_api
from services.user_pref import user_pref

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
    user_id = 1

    print("================================")
    print("【受信】data:")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print("================================")

    image_paths = data.get('image_paths', [])
    human_image_base64 = data.get('model_image_base64') or data.get('human_image_data') or data.get('human_image_base64')
    coordinate_id = data.get('coordinate_id')

    print("画像パスの分類処理")
    clothing_image_path_outer = None
    clothing_image_path_top = None
    clothing_image_path_bottom = None
    if len(image_paths) > 0:
        clothing_image_path_outer = image_paths[0].lstrip('/')
    if len(image_paths) > 1:
        clothing_image_path_top = image_paths[1].lstrip('/')
    if len(image_paths) > 2:
        clothing_image_path_bottom = image_paths[2].lstrip('/')
    print("--------------------------------")
    print(f"画像パスの分類結果:")
    print(f"  Top: {clothing_image_path_top}")
    print(f"  Bottom: {clothing_image_path_bottom}")
    print(f"  Outer: {clothing_image_path_outer}")
    print("--------------------------------")

    print("人物画像の取得方法を判定")
    model_template = data.get('model_template')
    human_image_path = None
    
    if human_image_base64:
        print("カメラ撮影画像を使用")
        try:
            # base64データを画像に変換
            img_data = base64.b64decode(human_image_base64)
            img = Image.open(BytesIO(img_data))
            img = ImageOps.exif_transpose(img)  # EXIF回転情報を適用
            
            # 保存先ディレクトリを作成（ユーザーIDに応じたパス、デフォルトは1）
            save_dir = f"static/images/{user_id}/model"
            os.makedirs(save_dir, exist_ok=True)
            
            # ファイル名を生成
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = uuid.uuid4().hex[:8]
            filename = f"human_{timestamp}_{unique_id}.jpg"
            file_path = os.path.join(save_dir, filename)
            
            # 画像を保存（RGBAモードの場合はRGBに変換）
            if img.mode == 'RGBA':
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3] if len(img.split()) == 4 else None)
                rgb_img.save(file_path, format='JPEG', quality=95, optimize=True)
            else:
                img.save(file_path, format='JPEG', quality=95, optimize=True)
            
            human_image_path = file_path
            print(f"人物画像を保存しました: {human_image_path}")
        except Exception as e:
            print(f"人物画像の保存エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'status': 'error',
                'message': f'人物画像の保存に失敗しました: {str(e)}'
            }), 400
    elif model_template:
        print(f"テンプレート画像を使用します: {model_template}")
        
        # テンプレート名に応じた画像ファイル名を決定
        template_image_map = {
            'mannequin': 'Image1.jpg',  # マネキン画像
            'profile': 'Image3.jpg'  # プロフィール画像（デフォルト）
        }
        
        template_filename = template_image_map.get(model_template.lower())
        if not template_filename:
            # 不明なテンプレート名の場合はデフォルトを使用
            print(f"不明なテンプレート名 '{model_template}' が指定されました。デフォルト画像を使用します。")
            template_filename = 'Image2.jpg'
        
        # テンプレート画像のパスを構築
        human_image_path = f"static/images/{user_id}/model/{template_filename}"
        
        # ファイルが存在するか確認
        if not os.path.exists(human_image_path):
            print(f"警告: テンプレート画像が見つかりません: {human_image_path}")
            # デフォルトの画像を使用
            human_image_path = f"static/images/1/model/{template_filename}"
            if not os.path.exists(human_image_path):
                return jsonify({
                    'status': 'error',
                    'message': f'テンプレート画像が見つかりません: {human_image_path}'
                }), 400
        
        print(f"テンプレート画像パス: {human_image_path}")
    else:
        # 人物画像もテンプレートも指定されていない場合
        return jsonify({
            'status': 'error',
            'message': '人物画像のbase64データ(model_image_base64)またはテンプレート(model_template)が必要です'
        }), 400
    
    try:
        
        #MARK: テスト
        use_test_image = True
        # use_test_image = False
        
        if use_test_image:
            # テスト画像のURLを返すだけ
            image_url = "/static/images/generated/generated_20251224_181137_d7b03acc.jpg"
            print(f"テスト用画像を使用: {image_url}")
        else:
            # 実際のAPIを呼び出す場合
            image_url = generateImg.main(
                human_image_path=human_image_path,
                clothing_image_path_top=clothing_image_path_top,
                clothing_image_path_bottom=clothing_image_path_bottom,
                clothing_image_path_outer=clothing_image_path_outer
            )
            print(f"画像を生成し、static/images/generated/に保存しました: {image_url}")
        
        # coordinate_idが指定されている場合、coordinatesテーブルのgenimg_pathを更新
        if coordinate_id:
            conn = None
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                update_sql = """
                    UPDATE coordinates 
                    SET genimg_path = %s 
                    WHERE coordinate_id = %s
                """
                cursor.execute(update_sql, (image_url, coordinate_id))
                conn.commit()
                
                print(f"coordinateテーブルのgenimg_pathを更新: {image_url}")
                
            except Exception as db_error:
                print(f"データベース更新エラー: {str(db_error)}")
                import traceback
                traceback.print_exc()
                # データベース更新に失敗しても画像生成は成功しているので、エラーは返さない
                if conn:
                    conn.rollback()
            finally:
                if conn:
                    conn.close()
        
        # バックエンドのベースURLを取得（リクエストから）
        # Androidアプリからアクセスする場合は、実際のサーバーURLに置き換える必要があります
        base_url = request.host_url.rstrip('/')
        full_image_url = f"{base_url}{image_url}"
        
        print("--------------------------------")
        print("画像URLの取得:")
        print(f"画像URL(相対パス): {image_url}")
        print(f"画像URL(完全URL): {full_image_url}")
        print("--------------------------------")
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
        print("================================")
        print("【受信】今日の予定データ:")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        print("================================")

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
        
        # user_idを固定値1に設定
        user_id = 1
        
        #MARK: テスト
        use_test_data = True
        # use_test_data = False
        
        if use_test_data:
            result = test_data
            print("テストデータを使用しました")
        else:
            # 今日の予定データを生成(データベースからアイテムを取得)
            result = aiOutfitSuggestion.generate_outfit_suggestion(data, user_id=user_id)
            print("実際のAPIを呼び出しました")
        
        # print("生成されたコーディネート:")
        # print(json.dumps(result, ensure_ascii=False, indent=2))
        
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
                        outer_id = proposal['items'].get('outer', {}).get('id') if 'outer' in proposal['items'] else None
                        
                        # アイテムの詳細情報（seasons, color_name）をデータベースから取得
                        item_ids = [top_id, bottom_id]
                        if outer_id:
                            item_ids.append(outer_id)
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
                        # outerのtasteも考慮
                        outer_taste = proposal['items'].get('outer', {}).get('taste', []) if 'outer' in proposal['items'] else []
                        all_taste = list(set(tops_taste + bottoms_taste + outer_taste))
                        
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
                        
                        # seasonを取得（トップス、ボトムス、アウターのseasonsを統合）
                        top_seasons = items_info.get(top_id, {}).get('seasons', '')
                        bottom_seasons = items_info.get(bottom_id, {}).get('seasons', '')
                        outer_seasons = items_info.get(outer_id, {}).get('seasons', '') if outer_id else ''
                        
                        # シーズンを統合（重複を除去）
                        all_seasons = []
                        if top_seasons:
                            all_seasons.extend([s.strip() for s in top_seasons.split(',')])
                        if bottom_seasons:
                            all_seasons.extend([s.strip() for s in bottom_seasons.split(',')])
                        if outer_seasons:
                            all_seasons.extend([s.strip() for s in outer_seasons.split(',')])
                        
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
                            INSERT INTO coordinates (user_id, top_id, bottom_id, outer_id, scene, features_json, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        """
                        cursor.execute(insert_sql, (user_id, top_id, bottom_id, outer_id, scene, features_json))
                        coordinate_id = cursor.lastrowid
                        saved_coordinate_ids.append(coordinate_id)
                        
                        # 提案データにcoordinate_idを追加
                        proposal['coordinate_id'] = coordinate_id
                        
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

