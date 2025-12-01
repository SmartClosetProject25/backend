import os
import base64
from io import BytesIO
import datetime
from dotenv import load_dotenv, find_dotenv
from PIL import Image
import requests
import json
from google.oauth2 import service_account
from google.auth.transport.requests import Request

load_dotenv(find_dotenv())

# サービスアカウント認証の設定
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "smartcloset-477908-928d0f51db40.json")
if not os.path.exists(SERVICE_ACCOUNT_FILE):
    raise FileNotFoundError(f"サービスアカウントJSONファイルが見つかりません: {SERVICE_ACCOUNT_FILE}")

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)

with open(SERVICE_ACCOUNT_FILE, 'r') as f:
    PROJECT_ID = json.load(f).get('project_id', 'smartcloset-477908')


def convert_to_base64(file_path):
    # ファイルをbase64文字列に変換
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def base64_to_image(base64_str):
    # base64文字列を画像に変換
    return Image.open(BytesIO(base64.b64decode(base64_str)))


def save_image_from_base64(base64_str, file_paths=None):
    # base64文字列から画像を保存
    img = base64_to_image(base64_str)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    if isinstance(file_paths, list) and len(file_paths) > 0:
        base_name = os.path.basename(file_paths[0]).split('.')[0]
    elif file_paths:
        base_name = os.path.basename(file_paths).split('.')[0]
    else:
        base_name = "output"
    
    filename = f"images/outputs/{base_name}_{timestamp}.png"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    img.save(filename)
    print(f"画像を保存しました: {filename}")


def process_dict_str_and_image(contents, file_paths=None):
    # LLMの出力結果を処理して画像を保存、テキストを表示
    print("============ 生成結果 =============")
    
    if not any('base64' in res for res in contents):
        print("⚠️  LLMの出力に画像が含まれていません")
    
    for res in contents:
        if 'base64' in res:
            save_image_from_base64(res['base64'], file_paths)
        else:
            print("出力テキスト:", res['str'])
    print("===================================")


def validate_and_extract_base64(response_json):
    # REST APIレスポンスからbase64文字列とテキストを抽出
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


def main(human_image_path, clothing_image_path_top, clothing_image_path_bottom):
    # メイン処理: Gemini APIを使用して画像を生成・編集
    MODEL_ID = "gemini-2.5-flash-image"
    LOCATION = "us-central1"
    API_URL = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_ID}:generateContent"
    
    query = "最初の画像に写っている人間に、2番目と3番目の画像の服を着せてください。服のサイズや形状を人間の体型に合わせて自然に調整してください。"
    
    human_b64 = convert_to_base64(human_image_path)
    clothing_b64_top = convert_to_base64(clothing_image_path_top)
    clothing_b64_bottom = convert_to_base64(clothing_image_path_bottom)
    print("ファイルのbase64変換が完了しました。")
    
    system_instruction = (
        "# 目的\n"
        "あなたのタスクは画像編集です。ユーザが入力した画像を元に、ユーザが指定した内容で新しい画像を生成してください。\n"
        "\n"
        "# ルール\n"
        "ユーザが指示した内容に関係のない物体は、元の画像と全く同一にしてください。\n"
        "ユーザが指示した内容だけをユーザの指示に忠実に編集して、画像を生成してください。\n"
        "ユーザからの指示が変更依頼の場合は、そのオブジェクトと指定されたオブジェクトを元の画像から入れ替える形で編集してください。\n"
        "ユーザからの指示が消去依頼の場合は、そのオブジェクトを元の画像から消去してください。\n"
        "ユーザからの指示が追加依頼の場合は、そのオブジェクトを元の画像に追加してください。\n"
        "複数の画像が提供された場合、最初の画像をベースとして使用し、2番目以降の画像の要素を適切に統合してください。\n"
        "服を着せる場合、服のサイズ、形状、質感を人間の体型に自然に合わせて調整してください。\n"
    )
    
    print("画像の生成を開始します。")
    
    request_body = {
        "contents": [{
            "role": "user",
            "parts": [
                {"text": query},
                {"inlineData": {"mimeType": "image/png", "data": human_b64}},
                {"inlineData": {"mimeType": "image/png", "data": clothing_b64_top}},
                {"inlineData": {"mimeType": "image/png", "data": clothing_b64_bottom}}
            ]
        }],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "generationConfig": {
            "temperature": 0.7,
            "responseModalities": ["TEXT", "IMAGE"],
            "candidateCount": 1
        }
    }
    
    try:
        credentials.refresh(Request())
        response = requests.post(
            API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {credentials.token}"
            },
            json=request_body
        )
        response.raise_for_status()
        response_json = response.json()
        
        image_str_dict = validate_and_extract_base64(response_json)
        process_dict_str_and_image(image_str_dict, [human_image_path, clothing_image_path_top, clothing_image_path_bottom])
        
    except requests.exceptions.RequestException as e:
        print(f"APIリクエストエラー: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"レスポンス内容: {e.response.text}")
        raise
    except ValueError as e:
        print(f"エラー発生: {e}")


if __name__ == "__main__":
    main("images/input/male_model.png", "images/input/clothes_a.png", "images/input/clothes_e.png")
