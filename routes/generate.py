from flask import Blueprint, request, jsonify
import json
import os
import base64
import datetime
import uuid
from io import BytesIO
from PIL import Image, ImageOps
from dotenv import load_dotenv

import services.ai.generate_image as generateImg
from utils.db_con import get_db_connection

# 環境変数をロード
load_dotenv()

generate_bp = Blueprint('generate', __name__)

@generate_bp.route('/generate_image', methods=['POST'])
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
        
        # 環境変数からテストモードを取得（デフォルトはFalse = 本番モード）
        use_test_image = os.getenv('USE_TEST_IMAGE', 'false').lower() in ('true', '1', 'yes')
        
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

