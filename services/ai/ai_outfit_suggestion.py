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
from utils.db_con import get_db_connection


def load_items_from_db(user_id: int) -> tuple[dict, dict]:
    """
    データベースからユーザーのアイテムを取得し、items.jsonと同じ形式に変換する
    
    Args:
        user_id: ユーザーID
    
    Returns:
        (items.jsonと同じ形式の辞書, IDマッピング辞書(生成ID -> item_id))
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # アイテムを取得(カテゴリ、カテゴリ詳細、色情報も含める)
        sql = """
            SELECT 
                i.item_id,
                i.material,
                i.brand,
                i.taste,
                i.seasons,
                i.features,
                i.category_detail_id,
                c.category_id,
                c.category,
                cd.category_detail,
                col.color_name,
                col.color_code
            FROM items i
            INNER JOIN category_details cd ON i.category_detail_id = cd.category_detail_id
            INNER JOIN categories c ON cd.category_id = c.category_id
            INNER JOIN colors col ON i.color_id = col.color_id
            WHERE i.user_id = %s AND i.is_deleted = 0
            ORDER BY c.category_id, i.item_id
        """
        
        cursor.execute(sql, (user_id,))
        rows = cursor.fetchall()
        
        # カテゴリごとのカウンター(ID生成用)
        category_counters = {
            1: 1,  # トップス
            2: 1,  # ジャケット・アウター
            3: 1,  # パンツ
            4: 1   # スカート
        }
        
        wardrobe = []
        id_mapping = {}  # 生成ID -> item_id のマッピング
        
        for row in rows:
            category_id = row['category_id']
            category_name = row['category']
            actual_item_id = row['item_id']
            
            # カテゴリに応じたIDプレフィックス
            if category_id == 1:  # トップス
                item_id_prefix = "T"
            elif category_id == 2:  # ジャケット・アウター
                item_id_prefix = "O"
            elif category_id == 3:  # パンツ
                item_id_prefix = "B"
            elif category_id == 4:  # スカート
                item_id_prefix = "S"
            else:
                item_id_prefix = "X"
            
            # IDを生成(例: T001, B001, O001)
            generated_id = f"{item_id_prefix}{category_counters[category_id]:03d}"
            category_counters[category_id] += 1
            
            # IDマッピングを保存
            id_mapping[generated_id] = actual_item_id
            
            # taste, seasons, featuresをリストに変換(カンマ区切りの文字列から)
            taste_list = [t.strip() for t in row['taste'].split(',')] if row['taste'] else []
            seasons_list = [s.strip() for s in row['seasons'].split(',')] if row['seasons'] else []
            features_list = [f.strip() for f in row['features'].split(',')] if row['features'] else []
            
            # カテゴリ名をマッピング(データベースのカテゴリ名をitems.jsonの形式に合わせる)
            category_mapping = {
                'トップス': 'トップス',
                'ジャケット・アウター': 'アウター',
                'パンツ': 'ボトムス',
                'スカート': 'ボトムス'
            }
            mapped_category = category_mapping.get(category_name, category_name)
            
            item = {
                "id": generated_id,
                "category": mapped_category,
                "subCategory": row['category_detail'],
                "color": row['color_name'],
                "material": row['material'],
                "features": features_list,
                "taste": taste_list,
                "seasons": seasons_list
            }
            
            wardrobe.append(item)
        
        return {"wardrobe": wardrobe}, id_mapping
        
    except Exception as e:
        print(f"データベースからアイテムを取得中にエラーが発生しました: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()


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
    # アイテムデータを取得
    id_mapping = None
    if user_id is not None:
        # データベースから取得
        items_data, id_mapping = load_items_from_db(user_id)
    elif items_json_path is not None:
        # JSONファイルから取得(後方互換性)
        items_data = load_items_json(items_json_path)
    else:
        # デフォルトでJSONファイルから取得(後方互換性)
        items_data = load_items_json()
    
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
        "outer": "アイテムID(例: O001, 不要な場合はnull)"
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
    MODEL_ID = "gemini-2.5-flash"  # または"gemini-1.5-pro"
    
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