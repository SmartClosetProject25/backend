"""
itemsテーブルへのデータアクセス層（DAO）
"""
from utils.db_con import get_db_connection
from typing import Dict, List, Tuple, Optional

# ログ用の色コード
GREEN = '\033[92m'   # 緑（情報）
YELLOW = '\033[93m'  # 黄（警告）
RED = '\033[91m'     # 赤（エラー）
CYAN = '\033[96m'    # シアン（処理中）
RESET = '\033[0m'    # リセット


class ItemModel:
    """itemsテーブルへのデータアクセス層"""
    
    @staticmethod
    def load_items_for_ai(user_id: int) -> Tuple[dict, dict]:
        """
        データベースからユーザーのアイテムを取得し、AI提案用の形式に変換する
        
        Args:
            user_id: ユーザーID
        
        Returns:
            (items.jsonと同じ形式の辞書, IDマッピング辞書(生成ID -> item_id))
        """
        conn = None
        try:
            print(f"{CYAN}[PROCESS]{RESET} データベースからアイテムを取得中... (user_id: {user_id})")
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
                    "id": actual_item_id,  # 実際のitem_id（int）
                    "category": mapped_category,
                    "subCategory": row['category_detail'],
                    "color": row['color_name'],
                    "material": row['material'],
                    "features": features_list,
                    "taste": taste_list,
                    "seasons": seasons_list
                }
                
                wardrobe.append(item)
            
            print(f"{GREEN}[INFO]{RESET} アイテム取得完了 - 合計{len(wardrobe)}件")
            return {"wardrobe": wardrobe}, id_mapping
            
        except Exception as e:
            print(f"{RED}[ERROR]{RESET} データベースからアイテムを取得中にエラーが発生しました: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def get_item_details_by_ids(item_ids: List[int]) -> Dict[int, Dict]:
        """
        複数のitem_idに対して、item_name, image_path, tasteを取得する
        
        Args:
            item_ids: アイテムIDのリスト
        
        Returns:
            {item_id: {item_name, image_path, taste}} の辞書
        """
        if not item_ids:
            return {}
        
        conn = None
        try:
            print(f"{CYAN}[PROCESS]{RESET} アイテム詳細を取得中... (item_ids: {item_ids})")
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # プレースホルダーを生成
            placeholders = ','.join(['%s'] * len(item_ids))
            
            sql = f"""
                SELECT 
                    item_id,
                    item_name,
                    image_path,
                    taste
                FROM items
                WHERE item_id IN ({placeholders}) AND is_deleted = 0
            """
            
            cursor.execute(sql, tuple(item_ids))
            rows = cursor.fetchall()
            
            # 辞書に変換
            result = {}
            for row in rows:
                # tasteをリストに変換(カンマ区切りの文字列から)
                taste_list = [t.strip() for t in row['taste'].split(',')] if row['taste'] else []
                
                result[row['item_id']] = {
                    'item_name': row['item_name'],
                    'image_path': row['image_path'],
                    'taste': taste_list
                }
            
            print(f"{GREEN}[INFO]{RESET} アイテム詳細取得完了 - {len(result)}件")
            return result
            
        except Exception as e:
            print(f"{RED}[ERROR]{RESET} アイテム詳細を取得中にエラーが発生しました: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            if conn:
                conn.close()

