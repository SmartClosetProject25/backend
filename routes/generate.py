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
from models.coordinate_model import CoordinateModel

# 環境変数をロード
load_dotenv()

# ログ用の色コード
GREEN = '\033[92m'   # 緑（情報）
YELLOW = '\033[93m'  # 黄（警告・リクエスト）
RED = '\033[91m'     # 赤（エラー）
BLUE = '\033[94m'    # 青（セクション）
CYAN = '\033[96m'    # シアン（処理中）
RESET = '\033[0m'    # リセット

generate_bp = Blueprint('generate', __name__)

@generate_bp.route('/generate_image', methods=['POST'])
def generate_image():
    data = request.get_json()
    user_id = 1

    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{YELLOW}📥 REQUEST: POST /generate_image{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"{CYAN}受信データ:{RESET}")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"{BLUE}{'='*60}{RESET}\n")

    image_paths = data.get('image_paths', [])
    human_image_base64 = data.get('model_image_base64') or data.get('human_image_data') or data.get('human_image_base64')
    coordinate_id = data.get('coordinate_id')

    print(f"{CYAN}[PROCESS]{RESET} 画像パスの分類処理を開始")
    clothing_image_path_outer = None
    clothing_image_path_top = None
    clothing_image_path_bottom = None
    if len(image_paths) > 0:
        clothing_image_path_outer = image_paths[0].lstrip('/')
    if len(image_paths) > 1:
        clothing_image_path_top = image_paths[1].lstrip('/')
    if len(image_paths) > 2:
        clothing_image_path_bottom = image_paths[2].lstrip('/')
    print(f"{GREEN}[INFO]{RESET} 画像パス分類完了:")
    print(f"  Top: {clothing_image_path_top}")
    print(f"  Bottom: {clothing_image_path_bottom}")
    print(f"  Outer: {clothing_image_path_outer}")

    print(f"{CYAN}[PROCESS]{RESET} 人物画像の取得方法を判定")
    model_template = data.get('model_template')
    human_image_path = None
    
    if human_image_base64:
        print(f"{GREEN}[INFO]{RESET} カメラ撮影画像を使用")
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
            print(f"{GREEN}[INFO]{RESET} 人物画像を保存しました: {human_image_path}")
        except Exception as e:
            print(f"{RED}[ERROR]{RESET} 人物画像の保存エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'status': 'error',
                'message': f'人物画像の保存に失敗しました: {str(e)}'
            }), 400
    elif model_template:
        print(f"{GREEN}[INFO]{RESET} テンプレート画像を使用します: {model_template}")
        
        # テンプレート名に応じた画像ファイル名を決定
        template_image_map = {
            'mannequin': 'mannequin.png',  # マネキン画像
            'profile': 'Image5.jpg'  # プロフィール画像（デフォルト）
        }
        
        template_filename = template_image_map.get(model_template.lower())
        if not template_filename:
            # 不明なテンプレート名の場合はデフォルトを使用
            print(f"{YELLOW}[WARN]{RESET} 不明なテンプレート名 '{model_template}' が指定されました。デフォルト画像を使用します。")
            template_filename = 'Image2.jpg'
        
        # テンプレート画像のパスを構築
        human_image_path = f"static/images/{user_id}/model/{template_filename}"
        
        # ファイルが存在するか確認
        if not os.path.exists(human_image_path):
            print(f"{YELLOW}[WARN]{RESET} テンプレート画像が見つかりません: {human_image_path}")
            # デフォルトの画像を使用
            human_image_path = f"static/images/1/model/{template_filename}"
            if not os.path.exists(human_image_path):
                return jsonify({
                    'status': 'error',
                    'message': f'テンプレート画像が見つかりません: {human_image_path}'
                }), 400
        
        print(f"{GREEN}[INFO]{RESET} テンプレート画像パス: {human_image_path}")
    else:
        # 人物画像もテンプレートも指定されていない場合
        return jsonify({
            'status': 'error',
            'message': '人物画像のbase64データ(model_image_base64)またはテンプレート(model_template)が必要です'
        }), 400
    
    try:
        
        # 環境変数からテストモードを取得（デフォルトはFalse = 本番モード）
        # USE_TEST_IMAGEが存在しない場合、または'false'の場合はテスト画像を使用しない
        use_test_image = os.getenv('USE_TEST_IMAGE', '').lower() in ('true', '1', 'yes')
        
        print(f"{CYAN}[PROCESS]{RESET} 画像生成処理を開始")
        if use_test_image:
            # テスト画像のURLを返すだけ
            image_url = "/static/images/generated/generated_20260116_155608_455f59a2.jpg"
            print(f"{GREEN}[INFO]{RESET} テストモード: テスト用画像を使用 - {image_url}")
        else:
            # 実際のAPIを呼び出す場合
            print(f"{CYAN}[PROCESS]{RESET} AI画像生成APIを呼び出し中...")
            image_url = generateImg.main(
                human_image_path=human_image_path,
                clothing_image_path_top=clothing_image_path_top,
                clothing_image_path_bottom=clothing_image_path_bottom,
                clothing_image_path_outer=clothing_image_path_outer
            )
            print(f"{GREEN}[INFO]{RESET} 画像生成完了: {image_url}")
        
        # coordinate_idが指定されている場合、coordinatesテーブルのgenimg_pathを更新
        if coordinate_id:
            print(f"{CYAN}[PROCESS]{RESET} データベース更新中 (coordinate_id: {coordinate_id})")
            # データベース更新に失敗しても画像生成は成功しているので、エラーは返さない
            CoordinateModel.update_genimg_path(coordinate_id, image_url)
            print(f"{GREEN}[INFO]{RESET} データベース更新完了")
        
        # バックエンドのベースURLを取得（リクエストから）
        # Androidアプリからアクセスする場合は、実際のサーバーURLに置き換える必要があります
        base_url = request.host_url.rstrip('/')
        full_image_url = f"{base_url}{image_url}"
        
        response_data = {
            'status': 'success',
            'image_url': image_url,  # 相対パス（/static/images/generated/{filename}）
            'image_url_full': full_image_url  # 完全なURL（CoilのAsyncImageで使用可能）
        }
        
        print(f"\n{GREEN}{'─'*60}{RESET}")
        print(f"{GREEN}📤 RESPONSE: success (HTTP 200){RESET}")
        print(f"{GREEN}  画像URL(相対パス): {image_url}{RESET}")
        print(f"{GREEN}  画像URL(完全URL): {full_image_url}{RESET}")
        print(f"{GREEN}{'─'*60}{RESET}\n")
        
        return jsonify(response_data), 200
    except Exception as e:
        print(f"{RED}[ERROR]{RESET} エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        error_response = {
            'status': 'error',
            'message': str(e)
        }
        print(f"\n{RED}{'─'*60}{RESET}")
        print(f"{RED}📤 RESPONSE: error (HTTP 400){RESET}")
        print(f"{RED}{'─'*60}{RESET}\n")
        return jsonify(error_response), 400

