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
    """
    items.jsonファイルを読み込む関数
    
    Args:
        file_path: items.jsonのパス(デフォルト: services/ai/items.json)
    
    Returns:
        items.jsonの内容を辞書として返す
    """
    if file_path is None:
        # デフォルトパス: このファイルと同じディレクトリのitems.json
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, "items.json")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        items_data = json.load(f)
    
    return items_data


def generate_outfit_suggestion(
    date: str,
    weather: str,
    temperature: float,
    schedule: str,
    items_json_path: str = None
) -> dict:
    """
    GEMINI APIを使用してコーディネート提案を生成する関数
    
    Args:
        date: 日付(例: "2024年1月15日")
        weather: 天気(例: "晴れ")
        temperature: 気温(例: 15.5)
        schedule: 今日の予定(例: "会議、ランチ")
        items_json_path: items.jsonのパス(オプション)
    
    Returns:
        構造化された辞書型データ:
        {
            "proposals": [
                {
                    "pattern": 1,
                    "items": {
                        "tops": "T001",
                        "bottoms": "B001",
                        "outer": "O001"  # オプション
                    },
                    "item_ids": ["T001", "B001", "O001"],
                    "reason": "選んだ理由の説明"
                },
                ...
            ],
            "raw_response": "元のレスポンステキスト"
        }
    """
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
- 日付: {date}
- 天気: {weather}
- 気温: {temperature}℃
- 今日の予定: {schedule}

【私のアイテム】
{items_json_str}
"""
    
    # GenAI APIクライアントの初期化
    # 環境変数 GEMINI_API_KEY からAPIキーを自動取得
    client = genai.Client()
    
    # 使用するモデルIDを指定(テキスト生成用)
    MODEL_ID = "gemini-2.5-flash"  # または "gemini-1.5-pro"
    
    try:
        # APIを呼び出してテキストを生成
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
        )
        
        # レスポンスからテキストを取得
        if hasattr(response, 'text') and response.text:
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
            try:
                structured_data = json.loads(json_text)
                
                # 元のレスポンスも含めて返す
                structured_data["raw_response"] = raw_response
                
                return structured_data
            except json.JSONDecodeError as e:
                # JSONパースに失敗した場合、元のテキストを返す
                raise ValueError(f"レスポンスのJSONパースに失敗しました: {str(e)}\nレスポンス: {raw_response[:500]}")
        else:
            raise ValueError("レスポンスにテキストが含まれていません")
    
    except Exception as e:
        raise Exception(f"GEMINI API呼び出し中にエラーが発生しました: {str(e)}")


# テスト用のメイン関数
if __name__ == "__main__":
    # テストデータ
    test_date = "2025年11月21日"
    test_weather = "晴れ"
    test_temperature = 15.5
    test_schedule = "友達とディナー"
    
    try:
        result = generate_outfit_suggestion(
            date=test_date,
            weather=test_weather,
            temperature=test_temperature,
            schedule=test_schedule
        )
        
        print("=" * 50)
        print("コーディネート提案結果(構造化データ):")
        print("=" * 50)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("=" * 50)
        
        # 構造化データの各要素を変数に格納する例
        proposals = result.get("proposals", [])
        
        print("\n【各提案の詳細】")
        for proposal in proposals:
            pattern = proposal.get("pattern")
            item_ids = proposal.get("item_ids", [])
            reason = proposal.get("reason", "")
            items = proposal.get("items", {})
            
            print(f"\nパターン {pattern}:")
            print(f"  アイテムIDリスト: {item_ids}")
            print(f"  トップス: {items.get('tops')}")
            print(f"  ボトムス: {items.get('bottoms')}")
            print(f"  アウター: {items.get('outer')}")
            print(f"  選んだ理由: {reason}")
        
    except Exception as e:
        print(f"エラー: {e}")

