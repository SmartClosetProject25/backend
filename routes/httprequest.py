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
            
        print(categories)
        
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