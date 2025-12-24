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
import google.auth

load_dotenv(find_dotenv())

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

# MARK: Google GenAI SDK用の認証情報（デフォルト認証を使用）
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
try:
    sdk_credentials, sdk_project_id = google.auth.default(scopes=SCOPES)
except Exception:
    # デフォルト認証が失敗した場合はサービスアカウントを使用
    sdk_credentials = credentials
    sdk_project_id = PROJECT_ID


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
def resize_image_for_api(image_base64, max_size=(1024, 1024), quality=85):
    """
    画像をリサイズしてbase64文字列に変換する関数
    APIのサイズ制限（27,000,000文字）に対応するため、画像を適切なサイズにリサイズ
    
    Args:
        image_base64: 元の画像のbase64文字列
        max_size: 最大サイズ（幅, 高さ）のタプル
        quality: JPEG品質（1-100、PNGの場合は無視される）
    
    Returns:
        リサイズされた画像のbase64文字列
    """
    # base64文字列を画像に変換
    img = base64_to_image(image_base64)
    
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


# MARK: REST APIレスポンスからbase64文字列とテキストを抽出
def validate_and_extract_base64(response_json):
    if 'candidates' not in response_json or not response_json['candidates']:
        raise ValueError("responseにcandidatesが存在しません。")
    
    candidate = response_json['candidates'][0]
    if 'content' not in candidate or 'parts' not in candidate['content']:
        raise ValueError("responseの構造が不正です。")
    
    content = candidate['content']
    if not content['parts']:
        raise ValueError("content.partsが空です。")
    
    extracted_list = []
    for idx, part in enumerate(content['parts']):
        if 'text' in part and part['text']:
            extracted_list.append({"str": part['text']})
        elif 'inlineData' in part and part['inlineData']:
            if 'data' in part['inlineData']:
                extracted_list.append({"base64": part['inlineData']['data']})
            else:
                raise ValueError(f"part[{idx}]のinlineDataにdataキーが存在しません。")
        else:
            raise ValueError(f"part[{idx}] は想定外の形式です。")
    
    return extracted_list


# MARK: SDKレスポンスからbase64文字列とテキストを抽出
def validate_and_extract_base64_from_sdk(response):
    """
    Google GenAI SDKのレスポンスからbase64文字列や生成されたテキストを抽出して辞書のリストを返す関数
    responseは、Google GenAI APIからの応答オブジェクト
    最終的な出力は、LLM出力がテキストの場合は`str`キーをもち、画像の場合は`base64`キーを持つ辞書のリスト
    例: [{"str": "出力テキスト"}, {"base64": "base64文字列"}]
    """
    # responseにcandidates属性があるか確認
    if not hasattr(response, 'candidates'):
        raise ValueError("responseにcandidates属性が存在しません。")
    
    # candidatesが存在し、要素があるか確認
    if not response.candidates or len(response.candidates) == 0:
        raise ValueError("response.candidatesが空です。")

    # 最初のcandidateのcontentを取得
    candidate = response.candidates[0]
    if not hasattr(candidate, 'content'):
        raise ValueError("candidateにcontent属性が存在しません。")
        
    content = candidate.content
    if not hasattr(content, 'parts'):
        raise ValueError("contentにparts属性が存在しません。")

    # contentのpartsがリストであり、要素があるか確認
    if not content.parts or len(content.parts) == 0:
        raise ValueError("content.partsが空です。")

    extracted_list = []

    for idx, part in enumerate(content.parts):
        if hasattr(part, 'text') and part.text:
            # テキスト部分の場合
            extracted_list.append({"str": part.text})
            
        elif hasattr(part, 'inline_data') and part.inline_data:
            # 画像データの場合
            image_data = part.inline_data.data
            
            # データがbase64エンコードされている場合はそのまま使用
            if isinstance(image_data, str):
                base64_str = image_data
            else:
                # バイナリデータの場合はbase64エンコード
                base64_str = base64.b64encode(image_data).decode('utf-8')
            
            extracted_list.append({"base64": base64_str})
        else:
            raise ValueError(f"part[{idx}] は想定外の形式です。")

    return extracted_list


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
            "personGeneration": "allow_adult",
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
        print(f"エラーステータスコード: {response.status_code}")
        print(f"エラーレスポンス: {response.text}")
        try:
            error_json = response.json()
            print(f"エラーJSON: {json.dumps(error_json, indent=2, ensure_ascii=False)}")
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
        # 画像をbase64に変換（APIのサイズ制限に対応するため、700x700にリサイズ）
        print("画像を読み込み、API用にリサイズしています（700x700）...")
        human_b64 = resize_image_for_api(convert_to_base64(human_image_path), max_size=(700, 700))
        clothing_b64_top = resize_image_for_api(convert_to_base64(clothing_image_path_top), max_size=(700, 700))
        clothing_b64_bottom = resize_image_for_api(convert_to_base64(clothing_image_path_bottom), max_size=(700, 700))
        
        print("ファイルのbase64変換が完了しました。")
        print("Virtual Try-On APIは1つの商品画像のみをサポートしているため、順次処理を行います。")
        
        # ステップ1: トップスを着せる
        print("ステップ1: トップスを着せています...")
        result_b64 = _virtual_try_on_single_item(human_b64, clothing_b64_top)
        print("トップスの着用が完了しました。")
        
        # ステップ2: ボトムスを着せる（前の結果をリサイズして使用）
        print("ステップ2: ボトムスを着せています...")
        result_b64 = resize_image_for_api(result_b64, max_size=(700, 700))  # 中間結果をリサイズ
        result_b64 = _virtual_try_on_single_item(result_b64, clothing_b64_bottom)
        print("ボトムスの着用が完了しました。")
        
        # ステップ3: アウターを着せる（オプション、前の結果をリサイズして使用）
        if clothing_image_path_outer:
            print("ステップ3: アウターを着せています...")
            clothing_b64_outer = resize_image_for_api(convert_to_base64(clothing_image_path_outer), max_size=(700, 700))
            result_b64 = resize_image_for_api(result_b64, max_size=(700, 700))  # 中間結果をリサイズ
            result_b64 = _virtual_try_on_single_item(result_b64, clothing_b64_outer)
            print("アウターの着用が完了しました。")
        
        # MARK: 画像をstaticフォルダに保存してURLを返す（CoilのAsyncImageで使用可能にするため）
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
            rgb_img.save(file_path, format='JPEG', quality=85, optimize=True)
        else:
            img.save(file_path, format='JPEG', quality=85, optimize=True)
        
        print(f"画像を保存しました: {file_path}")
        
        # MARK: 公開URLパスを返す（CoilのAsyncImageで使用可能）
        image_url = f"/static/images/generated/{filename}"
        return image_url
        
    except requests.exceptions.RequestException as e:
        print(f"APIリクエストエラー: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"レスポンスステータス: {e.response.status_code}")
            print(f"レスポンス内容: {e.response.text}")
            try:
                error_json = e.response.json()
                print(f"エラーJSON: {json.dumps(error_json, indent=2, ensure_ascii=False)}")
            except:
                pass
        raise
    except ValueError as e:
        print(f"エラー発生: {e}")
        raise
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")
        raise


# MARK: SDK版: 1枚目の被写体に2枚目以降の服を着せる関数
def dress_person_with_clothes_sdk(human_image_path, clothing_image_paths):
    """
    1枚目の被写体に2枚目以降の服を着せる関数（Google GenAI SDK版）
    
    Args:
        human_image_path: 被写体の画像パス（1枚目）
        clothing_image_paths: 服の画像パスのリスト（2枚目以降）
    
    Returns:
        生成された画像のURLパス
    """
    try:
        from google import genai
        from google.genai.types import GenerateContentConfig, Part
    except ImportError:
        raise ImportError("google-genaiパッケージがインストールされていません。pip install google-genai を実行してください。")
    
    # クライアントの定義
    client = genai.Client(vertexai=True, project=sdk_project_id, location="global")
    MODEL_ID = "gemini-2.5-flash-image-preview"
    
    # 被写体画像をbase64に変換
    human_b64 = convert_to_base64(human_image_path)
    print(f"被写体画像のbase64変換が完了しました: {human_image_path}")
    
    # 服の画像をbase64に変換
    clothing_b64_list = []
    for idx, clothing_path in enumerate(clothing_image_paths):
        clothing_b64 = convert_to_base64(clothing_path)
        clothing_b64_list.append(clothing_b64)
        print(f"服画像{idx+1}のbase64変換が完了しました: {clothing_path}")
    
    # クエリを生成（服の枚数に応じて動的に変更）
    clothing_descriptions = []
    for idx in range(len(clothing_image_paths)):
        if idx == 0:
            clothing_descriptions.append(f"{idx+2}枚目の画像をトップスとして")
        elif idx == 1:
            clothing_descriptions.append(f"{idx+2}枚目の画像をボトムスとして")
        elif idx == 2:
            clothing_descriptions.append(f"{idx+2}枚目の画像をアウターとして")
        else:
            clothing_descriptions.append(f"{idx+2}枚目の画像を追加のアイテムとして")
    
    query = (
        "これは画像編集タスクです。1枚目の画像に写っている人物を絶対に変更しないでください。\n"
        "人物の顔、体型、ポーズ、髪型、肌の色、表情、背景を変更しないでください。\n"
        "新しい人物を生成したり、人物を置き換えたりしないでください。\n"
        "あなたのタスクは、1枚目の画像の人物に、" + "、".join(clothing_descriptions) + "着せることです。\n"
        "服だけを変更してください。それ以外は1枚目の画像と完全に同一にしてください。"
    )
    
    # Partsリストを作成（被写体画像、クエリ、服画像の順）
    parts = [
        Part.from_bytes(data=base64.b64decode(human_b64), mime_type="image/png")
    ]
    
    # クエリを追加
    parts.append(Part.from_text(text=query))
    
    # 服画像を追加
    for clothing_b64 in clothing_b64_list:
        parts.append(Part.from_bytes(data=base64.b64decode(clothing_b64), mime_type="image/png"))
    
    print("画像の生成を開始します。")
    
    # 画像の編集
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=parts,
        config=GenerateContentConfig(
            system_instruction=(
                "# 目的\n"
                "あなたのタスクは画像編集です。ユーザが入力した画像を元に、ユーザが指定した内容で新しい画像を生成してください。\n"
                "\n"
                "# ルール\n"
                "1枚目の画像に写っている人物を絶対に変更しないでください。\n"
                "人物の顔、体型、ポーズ、髪型、肌の色、表情、背景を変更しないでください。\n"
                "新しい人物を生成したり、人物を置き換えたりしないでください。\n"
                "ユーザが指示した服だけを変更してください。人物は1枚目の画像と完全に同一にしてください。\n"
                "ユーザが指示した服を、2枚目以降の画像を参考にして、1枚目の人物に着せてください。\n"
            ),
            temperature=0.7,
            response_modalities=["TEXT", "IMAGE"],
            candidate_count=1,
        ),
    )
    
    # LLMの出力結果が正しく画像になっているかバリデーション
    try:
        image_str_dict = validate_and_extract_base64_from_sdk(response)
        
        # 生成された画像のbase64文字列を取得
        generated_image_base64 = None
        for res in image_str_dict:
            if 'base64' in res:
                generated_image_base64 = res['base64']
                break
        
        if generated_image_base64 is None:
            raise ValueError("生成された画像が見つかりませんでした。")
        
        # 画像をstaticフォルダに保存してURLを返す
        img = base64_to_image(generated_image_base64)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        
        # static/images/generated/フォルダに保存
        save_dir = "static/images/generated"
        os.makedirs(save_dir, exist_ok=True)
        
        filename = f"generated_{timestamp}_{unique_id}.png"
        file_path = os.path.join(save_dir, filename)
        img.save(file_path)
        print(f"画像を保存しました: {file_path}")
        
        # 公開URLパスを返す
        image_url = f"/static/images/generated/{filename}"
        return image_url
        
    except ValueError as e:
        print(f"エラー発生: {e}")
        raise
