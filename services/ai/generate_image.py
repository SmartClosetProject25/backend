import os
import base64
from io import BytesIO
import datetime
import uuid
from dotenv import load_dotenv, find_dotenv
from PIL import Image, ImageOps
import requests
import json
from google.oauth2 import service_account
from google.auth.transport.requests import Request

load_dotenv(find_dotenv())

# ログ用の色コード
GREEN = '\033[92m'   # 緑（情報）
YELLOW = '\033[93m'  # 黄（警告）
RED = '\033[91m'     # 赤（エラー）
BLUE = '\033[94m'    # 青（セクション）
CYAN = '\033[96m'    # シアン（処理中）
RESET = '\033[0m'    # リセット

# MARK: サービスアカウント認証の設定
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "smartcloset-477908-928d0f51db40.json")
if not os.path.exists(SERVICE_ACCOUNT_FILE):
    raise FileNotFoundError(f"サービスアカウントJSONファイルが見つかりません: {SERVICE_ACCOUNT_FILE}")

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)

with open(SERVICE_ACCOUNT_FILE, 'r') as f:
    PROJECT_ID = json.load(f).get('project_id', 'smartcloset-477908')

# MARK: ファイルをbase64文字列に変換（EXIF回転情報を適用）
def convert_to_base64(file_path):
    """
    ファイルをbase64文字列に変換し、EXIFの回転情報を適用する関数
    
    Args:
        file_path: 画像ファイルのパス
    
    Returns:
        EXIF回転情報が適用された画像のbase64文字列
    """
    # 画像を開いてEXIF回転情報を適用
    img = Image.open(file_path)
    img = ImageOps.exif_transpose(img)
    
    # 画像をBytesIOに保存してbase64エンコード
    output = BytesIO()
    # 元の画像形式を保持（JPEGまたはPNG）
    if img.format == 'PNG' or file_path.lower().endswith('.png'):
        img.save(output, format='PNG')
    else:
        # RGBAモードの場合はRGBに変換
        if img.mode == 'RGBA':
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[3] if len(img.split()) == 4 else None)
            rgb_img.save(output, format='JPEG', quality=95)
        else:
            img.save(output, format='JPEG', quality=95)
    
    output.seek(0)
    return base64.b64encode(output.read()).decode("utf-8")


# MARK: base64文字列を画像に変換（EXIF回転情報を適用）
def base64_to_image(base64_str):
    """
    base64文字列を画像に変換し、EXIFの回転情報を適用する関数
    
    Args:
        base64_str: base64エンコードされた画像文字列
    
    Returns:
        EXIF回転情報が適用されたPIL Imageオブジェクト
    """
    img = Image.open(BytesIO(base64.b64decode(base64_str)))
    # EXIFの回転情報を適用（画像が横になっている問題を解決）
    img = ImageOps.exif_transpose(img)
    return img


# MARK: 画像をリサイズしてbase64文字列に変換（APIのサイズ制限に対応）
def resize_image_for_api(image_base64, max_size=(1024, 1024), quality=95):
    """
    画像をリサイズしてbase64文字列に変換する関数
    APIのサイズ制限（27,000,000文字）に対応するため、画像を適切なサイズにリサイズ
    リサイズが必要な場合のみリサイズを実行し、品質を保持します
    
    Args:
        image_base64: 元の画像のbase64文字列
        max_size: 最大サイズ（幅, 高さ）のタプル
        quality: JPEG品質（1-100、PNGの場合は無視される）
    
    Returns:
        リサイズされた画像のbase64文字列（リサイズ不要の場合は元のbase64文字列）
    """
    # base64文字列を画像に変換
    img = base64_to_image(image_base64)
    original_size = img.size
    
    # リサイズが必要かチェック（max_sizeより大きい場合のみリサイズ）
    needs_resize = original_size[0] > max_size[0] or original_size[1] > max_size[1]
    
    if needs_resize:
        # アスペクト比を保ちながらリサイズ
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # 画像をBytesIOに保存してbase64に変換
    output = BytesIO()
    
    # 画像形式を確認（PNGまたはJPEG）
    # PILのImageオブジェクトのformat属性を使用
    if img.format == 'PNG':
        img.save(output, format='PNG', optimize=True)
    else:
        # JPEG形式で保存（PNG以外はJPEGとして扱う）
        if img.mode == 'RGBA':
            # RGBAモードの場合はRGBに変換
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[3] if len(img.split()) == 4 else None)
            rgb_img.save(output, format='JPEG', quality=quality, optimize=True)
        else:
            img.save(output, format='JPEG', quality=quality, optimize=True)
    
    output.seek(0)
    return base64.b64encode(output.read()).decode("utf-8")


# MARK: Virtual Try-On APIレスポンスからbase64文字列を抽出
def validate_and_extract_virtual_try_on_response(response_json):
    """
    Virtual Try-On APIのレスポンスからbase64文字列を抽出する関数
    
    Args:
        response_json: APIレスポンスのJSONオブジェクト
    
    Returns:
        生成された画像のbase64文字列
    """
    if 'predictions' not in response_json or not response_json['predictions']:
        raise ValueError("responseにpredictionsが存在しません。")
    
    # 最初の予測結果を取得
    prediction = response_json['predictions'][0]
    
    if 'bytesBase64Encoded' not in prediction:
        raise ValueError("predictionにbytesBase64Encodedが存在しません。")
    
    return prediction['bytesBase64Encoded']


# MARK: 単一の商品画像でVirtual Try-On APIを呼び出すヘルパー関数
def _virtual_try_on_single_item(person_image_base64, product_image_base64):
    """
    1つの商品画像でVirtual Try-On APIを呼び出すヘルパー関数
    
    Args:
        person_image_base64: 人物画像のbase64文字列
        product_image_base64: 商品画像のbase64文字列
    
    Returns:
        生成された画像のbase64文字列
    """
    MODEL_ID = "virtual-try-on-preview-08-04"
    LOCATION = "us-central1"
    API_URL = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_ID}:predict"
    
    request_body = {
        "instances": [
            {
                "personImage": {
                    "image": {
                        "bytesBase64Encoded": person_image_base64
                    }
                },
                "productImages": [
                    {
                        "image": {
                            "bytesBase64Encoded": product_image_base64
                        }
                    }
                ]
            }
        ],
        "parameters": {
            "sampleCount": 1,
            "baseSteps": 32,
            "addWatermark": True,
            "personGeneration": "allow_all",
            "safetySetting": "block_medium_and_above",
            "outputOptions": {
                "mimeType": "image/jpeg",
                "compressionQuality": 85  # JPEG形式なのでcompressionQualityを指定
            }
        }
    }
    
    credentials.refresh(Request())
    response = requests.post(
        API_URL,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {credentials.token}"
        },
        json=request_body
    )
    
    if response.status_code != 200:
        print(f"{RED}[ERROR]{RESET} APIエラーステータスコード: {response.status_code}")
        print(f"{RED}[ERROR]{RESET} エラーレスポンス: {response.text}")
        try:
            error_json = response.json()
            print(f"{RED}[ERROR]{RESET} エラーJSON:")
            print(json.dumps(error_json, indent=2, ensure_ascii=False))
        except:
            pass
        response.raise_for_status()
    
    response_json = response.json()
    return validate_and_extract_virtual_try_on_response(response_json)


# MARK: メイン処理: Virtual Try-On APIを使用して画像を生成
def main(human_image_path, clothing_image_path_top, clothing_image_path_bottom, clothing_image_path_outer=None):
    """
    Virtual Try-On APIを使用して人物に服を着せた画像を生成する関数
    注意: Virtual Try-On APIは1つの商品画像のみをサポートしているため、
    複数の服を着せる場合は順次API呼び出しを行います（トップス→ボトムス→アウター）
    
    Args:
        human_image_path: 人物の画像パス
        clothing_image_path_top: トップスの画像パス
        clothing_image_path_bottom: ボトムスの画像パス
        clothing_image_path_outer: アウターの画像パス（オプション）
    
    Returns:
        生成された画像のURLパス
    """
    try:
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{CYAN}🎨 Virtual Try-On API画像生成開始{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        
        # 画像をbase64に変換（APIのサイズ制限に対応するため、2048x2048にリサイズ）
        print(f"{CYAN}[PROCESS]{RESET} 画像を読み込み、API用にリサイズしています（2048x2048）...")
        human_b64 = resize_image_for_api(convert_to_base64(human_image_path), max_size=(2048, 2048))
        clothing_b64_top = resize_image_for_api(convert_to_base64(clothing_image_path_top), max_size=(2048, 2048))
        clothing_b64_bottom = resize_image_for_api(convert_to_base64(clothing_image_path_bottom), max_size=(2048, 2048))
        
        print(f"{GREEN}[INFO]{RESET} ファイルのbase64変換が完了しました")
        print(f"{CYAN}[PROCESS]{RESET} Virtual Try-On APIは1つの商品画像のみをサポートしているため、順次処理を行います")
        
        # ステップ1: トップスを着せる
        print(f"\n{CYAN}[STEP 1]{RESET} トップスを着せています...")
        result_b64 = _virtual_try_on_single_item(human_b64, clothing_b64_top)
        print(f"{GREEN}[INFO]{RESET} トップスの着用が完了しました")
        
        # ステップ2: ボトムスを着せる（API結果は既に適切なサイズのためリサイズ不要）
        print(f"\n{CYAN}[STEP 2]{RESET} ボトムスを着せています...")
        result_b64 = _virtual_try_on_single_item(result_b64, clothing_b64_bottom)
        print(f"{GREEN}[INFO]{RESET} ボトムスの着用が完了しました")
        
        # ステップ3: アウターを着せる（オプション、API結果は既に適切なサイズのためリサイズ不要）
        if clothing_image_path_outer:
            print(f"\n{CYAN}[STEP 3]{RESET} アウターを着せています...")
            clothing_b64_outer = resize_image_for_api(convert_to_base64(clothing_image_path_outer), max_size=(2048, 2048))
            result_b64 = _virtual_try_on_single_item(result_b64, clothing_b64_outer)
            print(f"{GREEN}[INFO]{RESET} アウターの着用が完了しました")
        
        # MARK: 画像をstaticフォルダに保存してURLを返す（CoilのAsyncImageで使用可能にするため）
        print(f"\n{CYAN}[PROCESS]{RESET} 生成された画像を保存中...")
        img = base64_to_image(result_b64)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        
        # MARK: static/images/generated/フォルダに保存
        save_dir = "static/images/generated"
        os.makedirs(save_dir, exist_ok=True)
        
        # JPEG形式で保存（APIの出力がJPEG形式のため）
        filename = f"generated_{timestamp}_{unique_id}.jpg"
        file_path = os.path.join(save_dir, filename)
        
        # RGBAモードの場合はRGBに変換してからJPEGで保存
        if img.mode == 'RGBA':
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[3] if len(img.split()) == 4 else None)
            rgb_img.save(file_path, format='JPEG', quality=95, optimize=True)
        else:
            img.save(file_path, format='JPEG', quality=95, optimize=True)
        
        print(f"{GREEN}[INFO]{RESET} 画像を保存しました: {file_path}")
        
        # MARK: 公開URLパスを返す（CoilのAsyncImageで使用可能）
        image_url = f"/static/images/generated/{filename}"
        print(f"{GREEN}[INFO]{RESET} 画像生成完了: {image_url}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        return image_url
        
    except requests.exceptions.RequestException as e:
        print(f"{RED}[ERROR]{RESET} APIリクエストエラー: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"{RED}[ERROR]{RESET} レスポンスステータス: {e.response.status_code}")
            print(f"{RED}[ERROR]{RESET} レスポンス内容: {e.response.text}")
            try:
                error_json = e.response.json()
                print(f"{RED}[ERROR]{RESET} エラーJSON:")
                print(json.dumps(error_json, indent=2, ensure_ascii=False))
            except:
                pass
        raise
    except ValueError as e:
        print(f"{RED}[ERROR]{RESET} エラー発生: {e}")
        raise
    except Exception as e:
        print(f"{RED}[ERROR]{RESET} 予期しないエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        raise

