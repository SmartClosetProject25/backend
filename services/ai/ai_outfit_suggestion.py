"""
.env に GEMINI_API_KEY が設定されていること
"""

import os
import json
from dotenv import load_dotenv
from google import genai

# 環境変数の読み込み
load_dotenv()


def load_items_json(file_path: str = None) -> dict:
    if file_path is None:
        # デフォルトパス: このファイルと同じディレクトリのitems.json
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, "items.json")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        items_data = json.load(f)
    
    return items_data


def generate_outfit_suggestion(
    data: dict,
    items_json_path: str = None
) -> dict:

    # items.jsonを読み込む
    items_data = load_items_json(items_json_path)
    
    # アイテムデータをJSON文字列に変換(プロンプトに含めるため)
    items_json_str = json.dumps(items_data, ensure_ascii=False, indent=2)
    
    # プロンプトの構築(JSON形式で出力を要求)
    prompt = f"""記憶してもらった【私のアイテム】を使って、【条件】に合ったコーディネートを提案してください。提案は2パターンお願いします。

それぞれの提案について、なぜその組み合わせを選んだのか理由と、ID(トップス・ボトムス・アウター)を明記してください。

出力は必ず以下のJSON形式で返してください。JSON以外のテキストは含めないでください。

{{
  "proposals": [
    {{
      "pattern": 1,
      "items": {{
        "tops": "アイテムID(例: T001)",
        "bottoms": "アイテムID(例: B001)",
        "outer": "アイテムID(例: O001、不要な場合はnull)"
      }},
      "item_ids": ["T001", "B001", "O001"],
      "reason": "なぜこの組み合わせを選んだのかの理由"
    }},
    {{
      "pattern": 2,
      "items": {{
        "tops": "アイテムID",
        "bottoms": "アイテムID",
        "outer": "アイテムIDまたはnull"
      }},
      "item_ids": ["T002", "B002", "O002"],
      "reason": "選んだ理由"
    }}
  ]
}}

【条件】
- 日付: {data['date']}
- 場所: {data['location']}
- 天気: {data['weather']}
- 降水確率: {data['precipitation']}
- 湿度: {data['humidity']}
- 今日の予定: {data['plan']}

【私のアイテム】
{items_json_str}
"""
    
    # GenAI APIクライアントの初期化
    # 環境変数 GEMINI_API_KEY からAPIキーを取得
    api_key = os.getenv('GEMINI_API_KEY')
    client = genai.Client(api_key=api_key)
    
    # 使用するモデルIDを指定(テキスト生成用)
    MODEL_ID = "gemini-2.5-flash"  # または "gemini-1.5-pro"
    
    # APIを呼び出してテキストを生成
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
    )
    
    # レスポンスからテキストを取得
    raw_response = response.text
    
    # JSONを抽出(コードブロックで囲まれている場合があるため)
    json_text = raw_response.strip()
    
    # コードブロック(```json や ```)を除去
    if json_text.startswith("```"):
        # 最初の```jsonまたは```を削除
        lines = json_text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        # 最後の```を削除
        if lines[-1].strip() == "```":
            lines = lines[:-1]
        json_text = "\n".join(lines)
    
    # JSONをパース
    structured_data = json.loads(json_text)
    
    # 元のレスポンスも含めて返す
    #structured_data["raw_response"] = raw_response
    
    return structured_data