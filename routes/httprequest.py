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

        # --- 画像 ---
        image_file = request.files.get('image')

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

        return jsonify({
            "status": "ok",
            "itemId": cursor.lastrowid,
            "imagePath": image_path
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        print({"status": "error", "message": str(e)})
        return jsonify({"status": "error", "message": str(e)}), 400

    finally:
        if conn:
            conn.close()
            

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


@http_request.route('/get_item_detail', methods=['POST'])
def get_item_detail():
    conn = None
    try:
        item_id = request.form.get("itemId")

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
            
            
@http_request.route('/delete_item', methods=['POST'])
def delete_item():
    conn = None
    try:
        item_id = request.form.get('item_id')
        
        if not item_id:
            return jsonify({"status": "error", "message": "itemId is required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            UPDATE items
            SET is_deleted = 1, updated_at = NOW()
            WHERE item_id = %s
        """
        cursor.execute(sql, (int(item_id),))
        conn.commit()

        return jsonify({"status": "success", "itemId": item_id})

    except Exception as e:
        print("Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        if "conn" in locals() and conn:
            conn.close()

        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = ""
        
        
@http_request.route('/favorite_item', methods=['POST'])
def favorite_item():
    conn = None
    try:
        item_id = request.form.get('item_id')
        user_id = request.form.get('user_id')

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

        current_status = result[0]  # 0 or 1

        # トグル処理（0→1、 1→0）
        new_status = 0 if current_status == 1 else 1

        sql_update = """
            UPDATE items
            SET is_favorite = %s,
                updated_at = NOW()
            WHERE item_id = %s
        """
        cursor.execute(sql_update, (new_status, int(item_id)))
        conn.commit()

        return jsonify({
            "status": "success",
            "itemId": item_id,
            "is_favorite": new_status
        })

    except Exception as e:
        print("Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        if "conn" in locals() and conn:
            conn.close()
