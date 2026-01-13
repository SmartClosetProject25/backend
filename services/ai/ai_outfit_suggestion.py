"""
.env に GEMINI_API_KEY が設定されていること
"""

import os
import json
from dotenv import load_dotenv
from google import genai
import sys

# 環境変数の読み込み
load_dotenv()

# utilsモジュールのパスを追加(プロジェクトルートを追加)
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from models.item_model import ItemModel

# ログ用の色コード
GREEN = '\033[92m'   # 緑（情報）
YELLOW = '\033[93m'  # 黄（警告）
RED = '\033[91m'     # 赤（エラー）
BLUE = '\033[94m'    # 青（セクション）
CYAN = '\033[96m'    # シアン（処理中）
RESET = '\033[0m'    # リセット


# 後方互換性のため、エイリアスを定義
def load_items_from_db(user_id: int) -> tuple[dict, dict]:
    """
    後方互換性のため残しておく（非推奨）
    ItemModel.load_items_for_ai()を使用してください
    """
    return ItemModel.load_items_for_ai(user_id)


def get_item_details_by_ids(item_ids: list[int]) -> dict[int, dict]:
    """
    後方互換性のため残しておく（非推奨）
    ItemModel.get_item_details_by_ids()を使用してください
    """
    return ItemModel.get_item_details_by_ids(item_ids)


def load_items_json(file_path: str = None) -> dict:
    """
    後方互換性のため残しておく(非推奨)
    """
    if file_path is None:
        # デフォルトパス: このファイルと同じディレクトリのitems.json
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, "items.json")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        items_data = json.load(f)
    
    return items_data


def generate_outfit_suggestion(
    data: dict,
    items_json_path: str = None,
    user_id: int = None
) -> dict:
    """
    コーディネート提案を生成する
    
    Args:
        data: 条件データ(date, location, weather, precipitation, humidity, plan)
        items_json_path: items.jsonのパス(後方互換性のため、指定された場合は使用)
        user_id: ユーザーID(指定された場合はデータベースから取得)
    
    Returns:
        コーディネート提案のJSONデータ
    """
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{CYAN}🤖 AIコーディネート提案生成開始{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    # アイテムデータを取得
    id_mapping = None
    if user_id is not None:
        # データベースから取得
        print(f"{CYAN}[PROCESS]{RESET} ユーザーID {user_id} のアイテムを取得中...")
        items_data, id_mapping = ItemModel.load_items_for_ai(user_id)
    elif items_json_path is not None:
        # JSONファイルから取得(後方互換性)
        print(f"{CYAN}[PROCESS]{RESET} JSONファイルからアイテムを読み込み中... ({items_json_path})")
        items_data = load_items_json(items_json_path)
    else:
        # デフォルトでJSONファイルから取得(後方互換性)
        print(f"{CYAN}[PROCESS]{RESET} デフォルトJSONファイルからアイテムを読み込み中...")
        items_data = load_items_json()
    
    # アイテムデータをJSON文字列に変換(プロンプトに含めるため)
    items_json_str = json.dumps(items_data, ensure_ascii=False, indent=2)
    print(f"{GREEN}[INFO]{RESET} アイテムデータ準備完了")
    
    # プロンプトの構築(JSON形式で出力を要求)
    prompt = f"""記憶してもらった【私のアイテム】を使って、【条件】に合ったコーディネートを提案してください。提案は3パターンお願いします。

それぞれの提案について、なぜその組み合わせを選んだのか理由と、アイテムID(トップス・ボトムス・アウター)を明記してください。

重要: アイテムIDは【私のアイテム】に記載されているidフィールドの数値（整数）を使用してください。文字列ではありません。

出力は必ず以下のJSON形式で返してください。JSON以外のテキストは含めないでください。

{{
  "proposals": [
    {{
      "pattern": 1,
      "items": {{
        "tops": 1,
        "bottoms": 2,
        "outer": 3
      }},
      "item_ids": [1, 2, 3],
      "reason": "なぜこの組み合わせを選んだのかの理由"
    }},
    {{
      "pattern": 2,
      "items": {{
        "tops": 4,
        "bottoms": 5,
        "outer": null
      }},
      "item_ids": [4, 5],
      "reason": "選んだ理由"
    }},
    {{
      "pattern": 3,
      "items": {{
        "tops": 6,
        "bottoms": 7,
        "outer": 8
      }},
      "item_ids": [6, 7, 8],
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
    if not api_key:
        print(f"{RED}[ERROR]{RESET} GEMINI_API_KEYが設定されていません")
        raise ValueError("GEMINI_API_KEYが設定されていません")
    
    client = genai.Client(api_key=api_key)
    
    # 使用するモデルIDを指定(テキスト生成用)
    MODEL_ID = "gemini-2.5-flash"  # または"gemini-1.5-pro"
    
    print(f"{CYAN}[PROCESS]{RESET} Gemini APIを呼び出し中... (モデル: {MODEL_ID})")
    # APIを呼び出してテキストを生成
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
    )
    
    # レスポンスからテキストを取得
    raw_response = response.text
    print(f"{GREEN}[INFO]{RESET} Gemini API呼び出し完了")
    
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
    
    print(f"{CYAN}[PROCESS]{RESET} JSONレスポンスをパース中...")
    # JSONをパース
    structured_data = json.loads(json_text)
    print(f"{GREEN}[INFO]{RESET} JSONパース完了 - 提案数: {len(structured_data.get('proposals', []))}件")
    
    # 提案されたIDに対して追加情報を取得（user_idが指定されている場合のみ）
    if user_id is not None:
        print(f"{CYAN}[PROCESS]{RESET} 提案されたアイテムの詳細情報を取得中...")
        # 全ての提案からアイテムIDを収集
        all_item_ids = []
        for proposal in structured_data.get('proposals', []):
            items = proposal.get('items', {})
            # itemsオブジェクトからIDを取得（nullの場合はスキップ）
            for key in ['tops', 'bottoms', 'outer']:
                item_id = items.get(key)
                if item_id and item_id != 'null':
                    # 既に実際のitem_id（int）なのでそのまま使用
                    if isinstance(item_id, int) and item_id not in all_item_ids:
                        all_item_ids.append(item_id)
        
        # データベースから追加情報を取得
        item_details = ItemModel.get_item_details_by_ids(all_item_ids)
        
        # 各提案に追加情報を含める
        for proposal in structured_data.get('proposals', []):
            items = proposal.get('items', {})
            actual_item_ids = []  # 実際のitem_id（int）のリスト
            
            # 各アイテムに追加情報を付与
            for key in ['tops', 'bottoms', 'outer']:
                item_id = items.get(key)
                # nullの場合はスキップ
                if not item_id or item_id == 'null':
                    continue
                
                # 既に実際のitem_id（int）なのでそのまま使用
                if isinstance(item_id, int) and item_id in item_details:
                    details = item_details[item_id]
                    # IDが数値として入っている場合は、オブジェクトに変換して追加情報を含める
                    items[key] = {
                        'id': item_id,  # 実際のitem_id（int）
                        'item_name': details['item_name'],
                        'image_path': details['image_path'],
                        'taste': details['taste']
                    }
                    actual_item_ids.append(item_id)
            
            # item_ids配列を実際のitem_id（int）に置き換え
            proposal['item_ids'] = actual_item_ids
        
        print(f"{GREEN}[INFO]{RESET} アイテム詳細情報の付与完了")
    
    print(f"{GREEN}[INFO]{RESET} AIコーディネート提案生成完了")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    return structured_data