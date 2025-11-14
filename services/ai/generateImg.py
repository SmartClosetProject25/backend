# ========== 必要なライブラリのインポート ==========
import os  # ファイルパス操作やディレクトリ作成に使用
import base64  # 画像データをbase64形式に変換するために使用
from io import BytesIO  # バイナリデータをメモリ上で扱うために使用
import datetime  # タイムスタンプ生成に使用
from dotenv import load_dotenv, find_dotenv  # 環境変数の読み込みに使用
from PIL import Image  # 画像処理に使用
from google import genai  # Google GenAI APIクライアント
from google.genai.types import GenerateContentConfig, Part  # API設定とパーツ生成に使用
import google.auth  # Google認証に使用

# ========== 環境変数の読み込み ==========
# .envファイルから環境変数を読み込む（APIキーや認証情報など）
_ = load_dotenv(find_dotenv())

# ========== Google Cloud認証情報の設定 ==========
# Google Cloud Platformの認証スコープを指定
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
# デフォルトの認証情報を使用してプロジェクトIDを取得
credentials, project_id = google.auth.default(scopes=SCOPES)


def convert_to_base64(file_path):
    """
    ファイルをbase64文字列に変換する関数
    file_pathは、変換するファイルのパス
    
    処理の流れ:
    1. ファイルをバイナリモードで読み込む
    2. 読み込んだバイトデータをbase64エンコード
    3. UTF-8文字列としてデコードして返す
    """
    # ファイルをバイナリモード（"rb"）で開いて読み込む
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    # バイトデータをbase64エンコードし、UTF-8文字列に変換
    base64_str = base64.b64encode(file_bytes).decode("utf-8")

    return base64_str

def base64_to_image(base64_str):
    """
    base64文字列を受け取り、画像に変換する関数
    base64_strは、base64文字列
    
    処理の流れ:
    1. base64文字列をバイナリデータにデコード
    2. BytesIOオブジェクトに変換(メモリ上のファイルとして扱う)
    3. PIL Imageオブジェクトとして開いて返す
    """
    # base64文字列をバイナリデータにデコード
    img_data = base64.b64decode(base64_str)
    
    # BytesIOオブジェクトを作成（メモリ上のバイナリストリームとして扱う）
    # PIL Imageはファイルパスまたはファイルオブジェクトを受け取るため、BytesIOを使用
    img = Image.open(BytesIO(img_data))
    
    return img

def save_image_from_base64(base64_str, file_paths=None):
    """
    base64文字列を受け取り、画像を保存する関数
    base64_strは、base64文字列
    file_pathsは、元画像のパスのリストまたは単一のパス。保存した画像に元画像の名前を利用する。
    例： outputs/sample1/sample1_2023-10-01_12-00-00.png
    複数画像の場合は、最初の画像名を使用する
    
    処理の流れ:
    1. base64文字列を画像オブジェクトに変換
    2. 現在時刻からタイムスタンプを生成
    3. 元画像のファイル名を取得（複数の場合は最初の画像名を使用）
    4. 出力ディレクトリを作成（存在しない場合）
    5. 画像をPNG形式で保存
    """ 
    # base64文字列を画像オブジェクトに変換
    img = base64_to_image(base64_str)

    # 現在時刻からタイムスタンプを生成（ファイル名の重複を防ぐため）
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    # 元画像のファイル名を取得（拡張子を除く）
    # file_pathsがリストの場合は最初の要素を使用、単一の場合はそのまま使用
    if isinstance(file_paths, list) and len(file_paths) > 0:
        # リストの場合、最初の要素のファイル名を取得
        base_name = os.path.basename(file_paths[0]).split('.')[0]
    elif file_paths:
        # 単一のパスの場合、そのファイル名を取得
        base_name = os.path.basename(file_paths).split('.')[0]
    else:
        # パスが指定されていない場合、デフォルト名を使用
        base_name = "output"
    
    # 出力ファイルパスを生成（元画像名_タイムスタンプ.png）
    filename = f"images/outputs/{base_name}_{timestamp}.png"
    # 出力ディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # 画像をPNG形式で保存
    img.save(filename)
    print(f"画像を保存しました: {filename}")

def process_dict_str_and_image(contents, file_paths=None):
    """
    LLMの出力結果を整理したcontentsを受け取り、画像を保存、テキストを表示する
    contentsは、出力がテキストの場合は`str`キーをもち、画像の場合は`base64`キーを持つ辞書のリスト
    例: [{"str": "出力テキスト"}, {"base64": "base64文字列"}]
    file_pathsは、元画像のパスのリストまたは単一のパス
    
    処理の流れ:
    1. 生成結果の区切り線を表示
    2. 画像が含まれているか確認（警告表示）
    3. contentsの各要素を処理:
       - base64キーがある場合: 画像として保存
       - strキーのみの場合: テキストとして表示
    """

    print("============ 生成結果 =============")
    
    # contents内に画像データ（base64キー）が含まれているか確認
    has_image = any('base64' in res for res in contents)
    if not has_image:
        print("⚠️  LLMの出力に画像が含まれていません")
    
    # contentsの各要素を処理
    for res in contents:
        if 'base64' in res:
            # 画像データの場合、保存処理を実行
            save_image_from_base64(res['base64'], file_paths)
        else:
            # テキストデータの場合、コンソールに表示
            print("出力テキスト:", res['str'])
    print("===================================")


def validate_and_extract_base64(response):
    """
    LLMの生の出力結果responseを受け取り、base64文字列や生成されたテキストを抽出して辞書のリストを返す関数
    responseは、Google GenAI APIからの応答
    最終的な出力は、LLM出力がテキストの場合は`str`キーをもち、画像の場合は`base64`キーを持つ辞書のリスト
    例: [{"str": "出力テキスト"}, {"base64": "base64文字列"}]
    
    処理の流れ:
    1. responseオブジェクトの構造を検証(candidates → content → parts)
    2. partsの各要素を処理:
       - テキスト部分: {"str": テキスト} として追加
       - 画像データ: {"base64": base64文字列} として追加
    3. 抽出したデータのリストを返す
    """
    # ========== responseオブジェクトの構造検証 ==========
    # responseにcandidates属性があるか確認
    if not hasattr(response, 'candidates'):
        raise ValueError("responseにcandidates属性が存在しません。")

    #print(f"response: {response}")
    
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

    # ========== partsからデータを抽出 ==========
    extracted_list = []

    # partsの各要素を処理
    for idx, part in enumerate(content.parts):
        if hasattr(part, 'text') and part.text:
            # テキスト部分の場合: テキストを辞書に格納
            extracted_list.append({"str": part.text})
            
        elif hasattr(part, 'inline_data') and part.inline_data:
            # 画像データの場合: inline_dataから画像データを取得
            image_data = part.inline_data.data
            
            # データがbase64エンコードされている場合はそのまま使用
            if isinstance(image_data, str):
                base64_str = image_data
            else:
                # バイナリデータの場合はbase64エンコードして文字列に変換
                base64_str = base64.b64encode(image_data).decode('utf-8')
            
            # base64文字列を辞書に格納
            extracted_list.append({"base64": base64_str})
        else:
            # 想定外の形式の場合、エラーを発生
            raise ValueError(f"part[{idx}] は想定外の形式です。")

    return extracted_list


def main(human_image_path, clothing_image_path_top, clothing_image_path_bottom):
    """
    メイン処理関数: Google GenAI APIを使用して画像を生成・編集する
    
    処理の流れ:
    1. GenAI APIクライアントを初期化
    2. 入力画像をbase64形式に変換
    3. 指定回数分、APIを呼び出して画像を生成
    4. 生成結果を検証し、画像を保存
    
    引数:
        human_image_path: 人間の画像のパス
        clothing_image_path: 服の画像のパス
    """
    # ========== GenAI APIクライアントの初期化 ==========
    # Vertex AIを使用してGenAIクライアントを作成
    client = genai.Client(vertexai=True, project=project_id, location="global")
    # 使用するモデルIDを指定（画像生成・編集が可能なモデル）
    MODEL_ID = "gemini-2.5-flash-image-preview"

    # ========== 生成設定 ==========
    # 一度に生成する画像の枚数を指定
    generate_images = 1

    # ========== 画像パスの設定（コメントアウトされた例） ==========
    # 複数画像を扱う場合：人間の画像と服の画像
    # human_image_path = "images/input/human.png"
    # clothing_image_path = "images/input/jacket.png"
    
    # 単一画像の場合（従来の使い方）
    # file_path = "images/inputs/human.png"

    # ========== 編集内容の指定（プロンプト） ==========
    # 以下は使用例（コメントアウト）
    #query = "女性の表情を溢れるくらいの笑顔に変更して"
    #query = "表情を笑顔に変更して"
    #query = "空を夕焼けの空に変更して、ベンチの色を赤色に変更して"
    #query = "コーヒーカップを消去して"
    #query = "画像に写っている女の子を元にした漫画を作成してください。4コマ漫画で、楽しそうに友達と遊んでいるところがいいです。"
    #query = "リアルな3dフィギュアにしてください。ただしポーズをもっとかっこいい女の子のポーズにしてください。"
    #query = "asapというアカウントのキャラクターなので、カッコよくasapというロゴを入れてください。おしゃれかつ違和感のないようにお願いします。"
    # 現在使用中のプロンプト: 人間に服を着せる処理
    query = "最初の画像に写っている人間に、2番目の画像の服を着せてください。服のサイズや形状を人間の体型に合わせて自然に調整してください。"

    # ========== 画像の前処理 ==========
    # 入力画像をbase64文字列に変換（APIに送信するため）
    human_b64 = convert_to_base64(human_image_path)
    clothing_b64_top = convert_to_base64(clothing_image_path_top)
    clothing_b64_bottom = convert_to_base64(clothing_image_path_bottom)
    print("ファイルのbase64変換が完了したので、処理を開始します。")

    # ========== 画像生成ループ ==========
    # 指定回数分、画像を生成
    for i in range(generate_images):
        print(f"画像{i+1}の生成を開始します。")
        
        # GenAI APIを呼び出して画像を生成・編集
        # contentsには、テキストプロンプトと2つの画像を指定
        response = client.models.generate_content(
            model=MODEL_ID,  # 使用するモデル
            contents=[
                Part.from_text(text=query),  # 編集指示のテキスト
                Part.from_bytes(data=base64.b64decode(human_b64), mime_type="image/png"),  # 人間の画像
                Part.from_bytes(data=base64.b64decode(clothing_b64_top), mime_type="image/png"),  # 服の画像
                Part.from_bytes(data=base64.b64decode(clothing_b64_bottom), mime_type="image/png")  # 服の画像
            ],
            config=GenerateContentConfig(
                # システムプロンプト: AIの動作を制御する指示
                system_instruction=(
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
                ),
                temperature=0.7,  # 生成のランダム性を制御（0.0-1.0、高いほど多様性が増す）
                response_modalities=["TEXT", "IMAGE"],  # テキストと画像の両方を返すように指定
                candidate_count=1,  # 生成する候補の数
            ),
        )

        # ========== 生成結果の処理 ==========
        # LLMの出力結果が正しく画像になっているかバリデーション
        # その後、画像を保存
        try:
            # APIレスポンスから画像データ（base64）とテキストを抽出
            image_str_dict = validate_and_extract_base64(response)
            # 抽出したデータを処理（画像を保存、テキストを表示）
            process_dict_str_and_image(image_str_dict, [human_image_path, clothing_image_path_top, clothing_image_path_bottom])

        except ValueError as e:
            # エラーが発生した場合、エラーメッセージを表示
            print(f"エラー発生: {e}")


# ========== スクリプト実行時の処理 ==========
# このファイルが直接実行された場合のみ、main関数を呼び出す
# （他のファイルからインポートされた場合は実行されない）
if __name__ == "__main__":
    # 注意: main関数は引数が必要なため、実際に実行する場合は引数を指定する必要がある
    # 例: main("images/input/human.png", "images/input/jacket.png")
    main()