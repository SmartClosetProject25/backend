"""
coordinatesテーブルへのデータアクセス層（DAO）
"""
from utils.db_con import get_db_connection
import json
from typing import Optional, List, Dict, Any


class CoordinateModel:
    """coordinatesテーブルへのデータアクセス層"""
    
    @staticmethod
    def update_genimg_path(coordinate_id: int, image_url: str) -> bool:
        """
        coordinate_idのgenimg_pathを更新
        
        Args:
            coordinate_id: 更新するcoordinateのID
            image_url: 生成画像のURLパス
            
        Returns:
            bool: 更新成功時True、失敗時False
        """
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            update_sql = """
                UPDATE coordinates 
                SET genimg_path = %s 
                WHERE coordinate_id = %s
            """
            cursor.execute(update_sql, (image_url, coordinate_id))
            conn.commit()
            
            print(f"coordinateテーブルのgenimg_pathを更新: {image_url}")
            return True
        except Exception as e:
            print(f"データベース更新エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def create_coordinate(user_id: int, top_id: int, bottom_id: int, 
                         outer_id: Optional[int], scene: str, 
                         features_json: str) -> Optional[int]:
        """
        新しいcoordinateを作成してIDを返す
        
        Args:
            user_id: ユーザーID
            top_id: トップスアイテムID
            bottom_id: ボトムスアイテムID
            outer_id: アウターアイテムID（オプション）
            scene: シーン
            features_json: features_json文字列
            
        Returns:
            Optional[int]: 作成されたcoordinate_id、失敗時はNone
        """
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            insert_sql = """
                INSERT INTO coordinates (user_id, top_id, bottom_id, outer_id, scene, features_json, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(insert_sql, (user_id, top_id, bottom_id, outer_id, scene, features_json))
            conn.commit()
            coordinate_id = cursor.lastrowid
            return coordinate_id
        except Exception as e:
            print(f"データベース挿入エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def get_item_info(item_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """
        アイテムIDのリストからアイテム情報（seasons, color_name）を取得
        
        Args:
            item_ids: アイテムIDのリスト
            
        Returns:
            Dict[int, Dict[str, Any]]: item_idをキーとしたアイテム情報の辞書
        """
        if not item_ids:
            return {}
        
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            placeholders = ','.join(['%s'] * len(item_ids))
            item_sql = f"""
                SELECT 
                    i.item_id,
                    i.seasons,
                    col.color_name
                FROM items i
                INNER JOIN colors col ON i.color_id = col.color_id
                WHERE i.item_id IN ({placeholders}) AND i.is_deleted = 0
            """
            cursor.execute(item_sql, tuple(item_ids))
            item_rows = cursor.fetchall()
            
            # アイテム情報を辞書に変換
            items_info = {row['item_id']: row for row in item_rows}
            return items_info
        except Exception as e:
            print(f"アイテム情報取得エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def get_coordinates_by_user(user_id: int) -> List[Dict[str, Any]]:
        """
        ユーザーのcoordinatesを取得（アイテム情報もJOIN）
        
        Args:
            user_id: ユーザーID
            
        Returns:
            List[Dict[str, Any]]: coordinate情報のリスト
        """
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
                SELECT 
                    c.coordinate_id,
                    c.user_id,
                    c.top_id,
                    c.bottom_id,
                    c.outer_id,
                    c.scene,
                    c.features_json,
                    c.genimg_path,
                    c.rating,
                    c.created_at,
                    top.item_name as top_name,
                    top.image_path as top_image_path,
                    bottom.item_name as bottom_name,
                    bottom.image_path as bottom_image_path,
                    outer_item.item_name as outer_name,
                    outer_item.image_path as outer_image_path
                FROM coordinates c
                LEFT JOIN items top ON c.top_id = top.item_id
                LEFT JOIN items bottom ON c.bottom_id = bottom.item_id
                LEFT JOIN items outer_item ON c.outer_id = outer_item.item_id
                WHERE c.user_id = %s
                ORDER BY c.created_at DESC, c.coordinate_id DESC
            """
            cursor.execute(sql, (user_id,))
            rows = cursor.fetchall()
            
            # レスポンス用のデータを整形
            coordinates = []
            for row in rows:
                # features_jsonをパース（既にJSON形式の場合はそのまま使用）
                features = row['features_json']
                if isinstance(features, str):
                    try:
                        features = json.loads(features)
                    except json.JSONDecodeError:
                        features = {}
                
                coordinate_data = {
                    "coordinate_id": row['coordinate_id'],
                    "user_id": row['user_id'],
                    "top_id": row['top_id'],
                    "bottom_id": row['bottom_id'],
                    "outer_id": row['outer_id'],
                    "scene": row['scene'],
                    "features": features,
                    "genimg_path": row['genimg_path'],
                    "rating": row['rating'],
                    "created_at": row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else None,
                    "top": {
                        "id": row['top_id'],
                        "name": row['top_name'],
                        "image_path": row['top_image_path']
                    },
                    "bottom": {
                        "id": row['bottom_id'],
                        "name": row['bottom_name'],
                        "image_path": row['bottom_image_path']
                    }
                }
                
                # outerアイテムが存在する場合のみ追加
                if row['outer_id']:
                    coordinate_data["outer"] = {
                        "id": row['outer_id'],
                        "name": row['outer_name'],
                        "image_path": row['outer_image_path']
                    }
                
                coordinates.append(coordinate_data)
            
            return coordinates
        except Exception as e:
            print(f"データベース取得エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if conn:
                conn.close()

