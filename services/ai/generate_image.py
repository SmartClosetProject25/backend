import os
import base64
from io import BytesIO
import datetime
import uuid
from dotenv import load_dotenv, find_dotenv
from PIL import Image
import requests
import json
from google.oauth2 import service_account
from google.auth.transport.requests import Request

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


# MARK: ファイルをbase64文字列に変換
def convert_to_base64(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# MARK: base64文字列を画像に変換
def base64_to_image(base64_str):
    return Image.open(BytesIO(base64.b64decode(base64_str)))


# MARK: base64文字列から画像を保存
def save_image_from_base64(base64_str, file_paths=None):
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


# MARK: LLMの出力結果を処理して画像を保存、テキストを表示
def process_dict_str_and_image(contents, file_paths=None):
    print("============ 生成結果 =============")
    
    if not any('base64' in res for res in contents):
        print("⚠️  LLMの出力に画像が含まれていません")
    
    for res in contents:
        if 'base64' in res:
            save_image_from_base64(res['base64'], file_paths)
        else:
            print("出力テキスト:", res['str'])
    print("===================================")


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


# MARK: メイン処理: Gemini APIを使用して画像を生成・編集
def main(human_image_path, clothing_image_path_top, clothing_image_path_bottom, clothing_image_path_outer=None, aspect_ratio="1:1", image_size="1K"):
    MODEL_ID = "gemini-2.5-flash-image"
    LOCATION = "us-central1"
    API_URL = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_ID}:generateContent"
    
    # アウターがあるかどうかでクエリを変更
    if clothing_image_path_outer:
        query = "1番目の画像に写っている被写体(人物)に、2番目、3番目、4番目の画像の服を着せ替えてください。2番目をトップス、3番目をボトムス、4番目をアウターとして着せてください。既に着ている服(トップス、ボトムス、アウターなど)は全て脱がせて、新しい服を着せてください。服のサイズや形状を被写体の体型に合わせて自然に調整してください。"
    else:
        query = "1番目の画像に写っている被写体(人物)に、2番目と3番目の画像の服を着せ替えてください。2番目をトップス、3番目をボトムスとして着せてください。既に着ている服(トップス、ボトムス、アウターなど)は全て脱がせて、新しい服を着せてください。服のサイズや形状を被写体の体型に合わせて自然に調整してください。"
    
    human_b64 = convert_to_base64(human_image_path)
    clothing_b64_top = convert_to_base64(clothing_image_path_top)
    clothing_b64_bottom = convert_to_base64(clothing_image_path_bottom)
    
    # MARK: リクエストボディのpartsリストを作成
    parts = [
        {"text": query},
        {"inlineData": {"mimeType": "image/png", "data": human_b64}},
        {"inlineData": {"mimeType": "image/png", "data": clothing_b64_top}},
        {"inlineData": {"mimeType": "image/png", "data": clothing_b64_bottom}}
    ]
    
    # MARK: アウターがある場合は追加
    if clothing_image_path_outer:
        clothing_b64_outer = convert_to_base64(clothing_image_path_outer)
        parts.append({"inlineData": {"mimeType": "image/png", "data": clothing_b64_outer}})
    
    print("ファイルのbase64変換が完了しました。")
    
    # MARK: system_instructionを動的に生成
    rules = [
        "1番目の画像の被写体(人物)のみを対象とし、背景や他の物体は一切変更しないでください。",
        "被写体が既に着ている服(トップス、ボトムス、アウター、その他の衣類)は全て脱がせてください。",
        "2番目の画像の服をトップスとして、3番目の画像の服をボトムスとして着せ替えてください。",
        "服のサイズ、形状、質感を被写体の体型に自然に合わせて調整してください。",
        "服の着こなしは自然でリアルな見た目になるようにしてください。",
        "被写体の顔、髪型、体型、姿勢、背景など、服以外の要素は1番目の画像と完全に同一に保ってください。"
    ]
    
    if clothing_image_path_outer:
        rules[2] = "2番目の画像の服をトップスとして、3番目の画像の服をボトムスとして、4番目の画像の服をアウターとして着せ替えてください。"
        rules.insert(3, "アウターはトップスの上に着せるようにしてください。")
    
    # ルールに番号を付ける
    numbered_rules = [f"{i+1}. {rule}" for i, rule in enumerate(rules)]
    
    system_instruction = (
        "# 目的\n"
        "あなたのタスクは、1番目の画像に写っている被写体(人物)に服を着せ替えることです。\n"
        "2番目以降の画像の服を、1番目の画像の被写体に着せ替えてください。\n"
        "\n"
        "# 重要なルール\n"
        + "\n".join(numbered_rules) + "\n"
        "\n"
        "# 禁止事項\n"
        "- 被写体以外の物体を変更すること\n"
        "- 既存の服を残したまま新しい服を重ね着すること\n"
        "- 被写体の体型、姿勢、顔、髪型を変更すること\n"
        "- 背景を変更すること\n"
    )
    
    print("画像の生成を開始します。")
    
    request_body = {
        "contents": [{
            "role": "user",
            "parts": parts
        }],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "generationConfig": {
            "temperature": 0.7,
            "responseModalities": ["TEXT", "IMAGE"],
            "candidateCount": 1,
            "imageConfig": {
                "aspectRatio": aspect_ratio,
                "imageSize": image_size
            }
        }
    }
    
    # MARK: APIリクエストを送信してレスポンスを取得
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
        
        # MARK: 生成された画像のbase64文字列を取得
        generated_image_base64 = None
        for res in image_str_dict:
            if 'base64' in res:
                generated_image_base64 = res['base64']
                break
        
        if generated_image_base64 is None:
            raise ValueError("生成された画像が見つかりませんでした。")
        
        # MARK: 画像をstaticフォルダに保存してURLを返す（CoilのAsyncImageで使用可能にするため）
        img = base64_to_image(generated_image_base64)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        
        # MARK: static/images/generated/フォルダに保存
        save_dir = "static/images/generated"
        os.makedirs(save_dir, exist_ok=True)
        
        filename = f"generated_{timestamp}_{unique_id}.png"
        file_path = os.path.join(save_dir, filename)
        img.save(file_path)
        print(f"画像を保存しました: {file_path}")
        
        # MARK: デバッグ用: outputsフォルダにも保存（既存の処理を維持）
        file_paths_list = [human_image_path, clothing_image_path_top, clothing_image_path_bottom]
        if clothing_image_path_outer:
            file_paths_list.append(clothing_image_path_outer)
        process_dict_str_and_image(image_str_dict, file_paths_list)
        
        # MARK: 公開URLパスを返す（CoilのAsyncImageで使用可能）
        image_url = f"/static/images/generated/{filename}"
        return image_url
        
    except requests.exceptions.RequestException as e:
        print(f"APIリクエストエラー: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"レスポンス内容: {e.response.text}")
        raise
    except ValueError as e:
        print(f"エラー発生: {e}")
        raise


if __name__ == "__main__":
    # アウターなしの場合
    #main("images/input/male_model.png", "images/input/clothes_f.png", "images/input/clothes_e.png")
    # アウターありの場合
    main("images/input/test_model_a.png", "images/input/clothes_f.png", "images/input/clothes_e.png", "images/input/clothes_b.png")
