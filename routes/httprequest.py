import os
import uuid
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
# from db_con import get_db_connection
from utils.db_con import get_db_connection

http_request = Blueprint('http_request', __name__)

@http_request.route('/add_item', methods=['POST'])
def add_item():
    conn = None
    try:
        # --- multipart 文字データ ---
        user_id = request.form.get('userId')
        item_name = request.form.get('itemName')
        color_id = request.form.get('color')
        pattern_id = request.form.get('pattern')
        size = request.form.get('size')
        brand = request.form.get('brand')
        category_detail_id = request.form.get('category')
        material = request.form.get('material')
        feature = request.form.get('feature')
        season = request.form.get('season')
        taste = request.form.get('taste')

        # デバッグ: 受信したデータを確認
        print("=== add_item request received ===")
        print(f"Received form data: {dict(request.form)}")
        print(f"userId (raw): {user_id}, type: {type(user_id)}")

        # バリデーション: user_idが必須
        if not user_id:
            print("ERROR: userId is missing")
            return jsonify({"status": "error", "message": "userId is required"}), 400
        
        # user_idを整数に変換
        try:
            user_id = int(user_id)
            print(f"userId (converted): {user_id}, type: {type(user_id)}")
        except (ValueError, TypeError) as e:
            print(f"ERROR: Invalid userId format: {user_id}, error: {str(e)}")
            return jsonify({"status": "error", "message": f"Invalid userId format: {user_id}"}), 400

        # user_idがusersテーブルに存在するか確認
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT user_id FROM users WHERE user_id = %s AND is_deleted = 0", (user_id,))
            user_exists = cursor.fetchone()
            cursor.close()
            
            if not user_exists:
                print(f"ERROR: User with id {user_id} does not exist in users table")
                # デバッグ: usersテーブルの全user_idを確認
                try:
                    debug_cursor = conn.cursor()
                    debug_cursor.execute("SELECT user_id FROM users WHERE is_deleted = 0")
                    existing_users = [row[0] for row in debug_cursor.fetchall()]
                    debug_cursor.close()
                    print(f"Existing user_ids in database: {existing_users}")
                except Exception as debug_e:
                    print(f"Error getting existing users: {str(debug_e)}")
                    existing_users = []
                
                return jsonify({
                    "status": "error", 
                    "message": f"User with id {user_id} does not exist",
                    "debug": f"Existing user_ids: {existing_users}"
                }), 400
            
            print(f"User {user_id} verified successfully")
        finally:
            try:
                if conn and conn.is_connected():
                    conn.close()
            except Exception as close_e:
                print(f"Warning: Error closing connection: {str(close_e)}")

        # --- 画像 ---
        image_file = request.files.get('image')
        print(f"Received image file: {image_file}")

        image_path = None
        if image_file:
            # 保存フォルダ: static/images/userId/clothes
            save_dir = os.path.join("static", "images", str(user_id), "clothes")
            os.makedirs(save_dir, exist_ok=True)

            # 拡張子を保持
            ext = os.path.splitext(secure_filename(image_file.filename))[1]

            # ランダムなファイル名
            filename = f"clothes_{uuid.uuid4().hex}{ext}"

            # 保存パス
            save_path = os.path.join(save_dir, filename)
            image_file.save(save_path)

            # DB に保存する相対URL（公開URL）
            image_path = f"/static/images/{user_id}/clothes/{filename}"

        # --- DB処理 ---
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            INSERT INTO items (
                item_name,
                color_id,
                pattern_id,
                category_detail_id,
                user_id,
                size_id,
                brand,
                material,
                features,
                seasons,
                taste,
                image_path,
                created_at,
                updated_at,
                is_deleted
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), 0)
        """

        print(f"Executing SQL with user_id: {user_id}")

        cursor.execute(sql, (
            item_name,
            color_id,
            pattern_id,
            category_detail_id,
            user_id,
            size,
            brand,
            material,
            feature,
            season,
            taste,
            image_path
        ))

        conn.commit()
        print(f"SUCCESS: Item inserted with id: {cursor.lastrowid}")

        return jsonify({
            "status": "ok",
            "itemId": cursor.lastrowid,
            "imagePath": image_path
        }), 200

    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception as rollback_e:
                print(f"Warning: Error during rollback: {str(rollback_e)}")
        print({"status": "error", "message": str(e)})
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 400

    finally:
        # 接続がまだ開いている場合はクローズ
        if conn:
            try:
                if hasattr(conn, 'is_connected') and conn.is_connected():
                    conn.close()
            except Exception as close_e:
                print(f"Warning: Error closing connection in finally: {str(close_e)}")
            

@http_request.route('/get_item')
def get_item():
    try:
        user_id = request.args.get("userId")

        if not user_id:
            return jsonify({"status": "error", "message": "userId is required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT item_id, item_name, category_detail_id, image_path
            FROM items
            WHERE user_id = %s AND is_deleted = 0
            ORDER BY item_id DESC
        """

        cursor.execute(sql, (user_id,))
        rows = cursor.fetchall()

        # レスポンス形式をフロントエンドのデータクラスに合わせる
        items = []
        for r in rows:
            items.append({
                "id": r["item_id"],
                "itemName": r["item_name"],
                "category": r["category_detail_id"],
                "imageUrl": r["image_path"]  # null でも OK
            })

        return jsonify({
            "status": "ok",
            "items": items
        }), 200

    except Exception as e:
        print("--- get_item error ---")
        print(str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        if 'conn' in locals():
            conn.close()


@http_request.route('/get_item_detail', methods=['GET'])
def get_item_detail():
    conn = None
    try:
        item_id = request.args.get("itemId")

        if not item_id:
            return jsonify({
                "status": "error",
                "message": "itemId is required"
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT
                item_id,
                item_name,
                brand,
                size_id,
                category_detail_id,
                color_id,
                pattern_id,
                material,
                features,
                taste,
                seasons,
                image_path
            FROM items
            WHERE item_id = %s AND is_deleted = 0
            LIMIT 1
        """
        cursor.execute(sql, (item_id,))
        row = cursor.fetchone()

        if not row:
            return jsonify({
                "status": "error",
                "message": "item not found"
            }), 404

        # フロントのデータクラスに合わせてキー名を調整
        item = {
            "id": row["item_id"],
            "itemName": row["item_name"],
            "brandName": row["brand"],
            "size": row["size_id"],
            "category": row["category_detail_id"],
            "color": row["color_id"],
            "pattern": row["pattern_id"],
            "material": row["material"],
            "feature": row["features"],
            "taste": row["taste"],
            "season": row["seasons"],
            "imageUrl": row["image_path"], 
        }
        print(item)

        return jsonify({
            "status": "ok",
            "item": item
        }), 200

    except Exception as e:
        print("--- get_item_detail error ---")
        print(str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    finally:
        if conn:
            conn.close()

@http_request.route('/update_item', methods=['POST'])
def update_item():
    conn = None
    try:
        # --- multipart 文字データ ---
        item_id = request.form.get('itemId')
        user_id = request.form.get('userId')
        item_name = request.form.get('itemName')
        color_id = request.form.get('color')
        pattern_id = request.form.get('pattern')
        size = request.form.get('size')
        brand = request.form.get('brand')
        category_detail_id = request.form.get('category')
        material = request.form.get('material')
        feature = request.form.get('feature')
        season = request.form.get('season')
        taste = request.form.get('taste')

        if not item_id:
            return jsonify({"status": "error", "message": "itemId is required"}), 400
        
        if not user_id:
            return jsonify({"status": "error", "message": "userId is required"}), 400

        try:
            item_id = int(item_id)
            user_id = int(user_id)
        except (ValueError, TypeError) as e:
            return jsonify({"status": "error", "message": f"Invalid id format: {str(e)}"}), 400

        # アイテムが存在し、ユーザーが所有しているか確認
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT item_id, image_path FROM items WHERE item_id = %s AND user_id = %s AND is_deleted = 0",
            (item_id, user_id)
        )
        existing_item = cursor.fetchone()
        if not existing_item:
            cursor.close()
            return jsonify({"status": "error", "message": "Item not found or access denied"}), 404
        cursor.close()

        # --- 画像処理 ---
        image_file = request.files.get('image')
        image_path = None
        
        if image_file and image_file.filename:
            # 既存の画像パスを取得
            old_image_path = existing_item.get('image_path')

            # 保存フォルダ: static/images/userId/clothes
            save_dir = os.path.join("static", "images", str(user_id), "clothes")
            os.makedirs(save_dir, exist_ok=True)

            # 拡張子を保持
            ext = os.path.splitext(secure_filename(image_file.filename))[1]
            filename = f"clothes_{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(save_dir, filename)
            image_file.save(save_path)

            # DB に保存する相対URL
            image_path = f"/static/images/{user_id}/clothes/{filename}"

            # 古い画像を削除（オプション）
            if old_image_path:
                old_path = old_image_path.lstrip('/')
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception as e:
                        print(f"Warning: Failed to delete old image: {str(e)}")

        # --- DB更新処理 ---
        cursor = conn.cursor()
        
        if image_path:
            sql = """
                UPDATE items SET
                    item_name = %s,
                    color_id = %s,
                    pattern_id = %s,
                    category_detail_id = %s,
                    size_id = %s,
                    brand = %s,
                    material = %s,
                    features = %s,
                    seasons = %s,
                    taste = %s,
                    image_path = %s,
                    updated_at = NOW()
                WHERE item_id = %s AND user_id = %s
            """
            cursor.execute(sql, (
                item_name, color_id, pattern_id, category_detail_id,
                size, brand, material, feature, season, taste,
                image_path, item_id, user_id
            ))
        else:
            sql = """
                UPDATE items SET
                    item_name = %s,
                    color_id = %s,
                    pattern_id = %s,
                    category_detail_id = %s,
                    size_id = %s,
                    brand = %s,
                    material = %s,
                    features = %s,
                    seasons = %s,
                    taste = %s,
                    updated_at = NOW()
                WHERE item_id = %s AND user_id = %s
            """
            cursor.execute(sql, (
                item_name, color_id, pattern_id, category_detail_id,
                size, brand, material, feature, season, taste,
                item_id, user_id
            ))

        conn.commit()
        cursor.close()

        return jsonify({
            "status": "ok",
            "itemId": item_id
        }), 200

    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception as rollback_e:
                print(f"Warning: Error during rollback: {str(rollback_e)}")
        print({"status": "error", "message": str(e)})
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 400

    finally:
        if conn:
            try:
                if hasattr(conn, 'is_connected') and conn.is_connected():
                    conn.close()
            except Exception as close_e:
                print(f"Warning: Error closing connection in finally: {str(close_e)}")


@http_request.route('/get_master_data', methods=['GET'])
def get_master_data():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # カテゴリー詳細を取得
        cursor.execute("SELECT category_detail_id, category_detail FROM category_details ORDER BY category_detail_id")
        categories = {"0": "未選択"}
        for row in cursor.fetchall():
            categories[str(row["category_detail_id"])] = row["category_detail"]
        
        # サイズを取得
        cursor.execute("SELECT size_id, size FROM size ORDER BY size_id")
        sizes = {"0": "未選択"}
        for row in cursor.fetchall():
            sizes[str(row["size_id"])] = row["size"]
        
        # カラーを取得
        cursor.execute("SELECT color_id, color_name FROM colors ORDER BY color_id")
        colors = {"0": "未選択"}
        for row in cursor.fetchall():
            colors[str(row["color_id"])] = row["color_name"]
        
        # パターンを取得
        cursor.execute("SELECT pattern_id, pattern_name FROM patterns ORDER BY pattern_id")
        patterns = {"0": "未選択"}
        for row in cursor.fetchall():
            patterns[str(row["pattern_id"])] = row["pattern_name"]
        
        return jsonify({
            "status": "ok",
            "categories": categories,
            "sizes": sizes,
            "colors": colors,
            "patterns": patterns
        }), 200
        
    except Exception as e:
        print(f"--- get_master_data error ---")
        print(str(e))
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if conn:
            conn.close()
            
            
@http_request.route('/favorite', methods=['POST']) 
def favorite_item(): 
    conn = None 
    # debug: 受信データ確認
    data=request.get_json()
    print("Received data:", data)
    try:
        if not data:
            return jsonify({"status": "error", "message": "JSON body is required"}), 400

        item_id = data.get("itemId")
        user_id = data.get("userId")
        isfavorite = data.get("isFavorite")

        print("Received favorite request:", item_id, user_id)
        
        if not item_id:
            return jsonify({"status": "error", "message": "item_id is required"}), 400 
        
        conn = get_db_connection() 
        cursor = conn.cursor() 
        # まず現在の状態を取得 
        sql_select = "SELECT is_favorite FROM items WHERE item_id = %s" 
        cursor.execute(sql_select, (int(item_id),)) 
        result = cursor.fetchone() 
        
        if not result: 
            return jsonify({"status": "error", "message": "Item not found"}), 404 
        current_status = result[0] # 0 or 1 
        # トグル処理（0→1、 1→0） 
        new_status = 0 if current_status == 1 else 1 
        sql_update = """ UPDATE items SET is_favorite = %s, updated_at = NOW() WHERE item_id = %s """ 
        cursor.execute(sql_update, (new_status, int(item_id))) 
        conn.commit() 
        
        return jsonify({ "status": "success", "itemId": item_id, "is_favorite": new_status }) 
        
    except Exception as e: 
        print("Error:", e) 
        return jsonify({"status": "error", "message": str(e)}), 500 
    
    finally: 
        if "conn" in locals() and conn:
            conn.close()
            

@http_request.route('/update_profile', methods=['POST'])
def update_profile():
    # debug: 受信データ確認
    data=request.get_json()
    print("Received data:", data)
    conn = None
    try:
        user_id = request.form.get('user_id')
        name = request.form.get('name')
        gender = request.form.get('gender')
        height = request.form.get('height')
        weight = request.form.get('weight')
        personal_color = request.form.get('personalColor')
        skeleton = request.form.get('skeleton')

        if not user_id:
            return jsonify({"status": "error", "message": "user_id is required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 既存のプロフィールがあるか確認
        sql_check = "SELECT profile_id FROM profile WHERE user_id = %s"
        cursor.execute(sql_check, (user_id,))
        exists = cursor.fetchone()

        if exists:
            # UPDATE
            sql_update = """
                UPDATE profile
                SET name = %s,
                    gender = %s,
                    height = %s,
                    weight = %s,
                    personal_color = %s,
                    skeleton = %s,
                    updated_at = NOW()
                WHERE user_id = %s
            """
            cursor.execute(sql_update, (
                name, gender, height, weight, personal_color, skeleton, user_id
            ))
        else:
            # INSERT
            sql_insert = """
                INSERT INTO profile
                (user_id, name, gender, height, weight, personal_color, skeleton)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_insert, (
                user_id, name, gender, height, weight, personal_color, skeleton
            ))

        conn.commit()

        return jsonify({"status": "success"})

    except Exception as e:
        print("Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        if "conn" in locals() and conn:
            conn.close()

            
