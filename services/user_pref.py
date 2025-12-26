from __future__ import annotations
import json
from typing import Any, Dict, Optional
from utils.db_con import db_query_one, db_query_all, db_execute
import numpy as np
from flask import Blueprint, request, jsonify

user_pref = Blueprint('user_pref', __name__)

# =========================================================
# 次元数（マスタ件数）: colors/categories/patterns テーブルを想定
# もしテーブル名が違うなら修正してください
# =========================================================
NUM_COLORS = 26
NUM_CATEGORIES = 19
NUM_PATTERNS = 7

OFFSET_CAT = NUM_COLORS
OFFSET_PAT = NUM_COLORS + NUM_CATEGORIES
DIM = NUM_COLORS + NUM_CATEGORIES + NUM_PATTERNS

# =========================================================
# ユーザー好みベクトルの保存先テーブル
# （未作成ならこのSQLで作ってください）
#
# CREATE TABLE user_preferences (
#   user_id INT PRIMARY KEY,
#   pref_vector_json LONGTEXT NOT NULL,
#   updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
#     ON UPDATE CURRENT_TIMESTAMP
# );
#
# 評価ログ（連打・二重学習防止）
# CREATE TABLE coordinate_feedback (
#   feedback_id INT AUTO_INCREMENT PRIMARY KEY,
#   user_id INT NOT NULL,
#   coordinate_id INT NOT NULL,
#   rating ENUM('good','bad') NOT NULL,
#   created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
#   UNIQUE KEY uq_user_coordinate (user_id, coordinate_id)
# );
# =========================================================
def load_user_pref(user_id: int) -> np.ndarray:
    row = db_query_one(
        "SELECT trend FROM users WHERE user_id=%s",
        (user_id,),
    )
    if not row:
        return np.zeros(DIM, dtype=float)
    data = json.loads(row["trend"])
    vec = np.array(data, dtype=float)
    if vec.shape[0] != DIM:
        # 次元が変わってしまった場合は安全側でリセット（運用なら移行処理推奨）
        return np.zeros(DIM, dtype=float)
    return vec


def save_user_pref(user_id: int, pref: np.ndarray) -> None:
    payload = json.dumps(pref.tolist())
    # upsert
    db_execute(
        """
        INSERT INTO users (user_id, trend)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE trend=VALUES(trend)
        """,
        (user_id, payload),
    )


# =========================================================
# ベクトル化
# =========================================================
def onehot_add(vec: np.ndarray, idx: int) -> None:
    if 0 <= idx < vec.shape[0]:
        vec[idx] += 1.0

def outfit_vector_from_feature_ids(
    top_color_id: int,
    top_category_id: int,
    top_pattern_id: int,
    bottom_color_id: int,
    bottom_category_id: int,
    bottom_pattern_id: int,
) -> np.ndarray:
    """
    IDは 1 始まり想定。0始まりなら -1 を外す
    """
    v = np.zeros(DIM, dtype=float)

    # color
    onehot_add(v, (top_color_id - 1))
    onehot_add(v, (bottom_color_id - 1))

    # category
    onehot_add(v, OFFSET_CAT + (top_category_id - 1))
    onehot_add(v, OFFSET_CAT + (bottom_category_id - 1))

    # pattern
    onehot_add(v, OFFSET_PAT + (top_pattern_id - 1))
    onehot_add(v, OFFSET_PAT + (bottom_pattern_id - 1))

    return v

# =========================================================
# coordinates -> items JOIN（学習用）
# coordinate_id から top/bottom の特徴を取る
# =========================================================
def fetch_coordinate_features(user_id: int, coordinate_id: int) -> Optional[Dict[str, Any]]:
    sql = """
    SELECT
        c.coordinate_id,
        c.user_id,

        t.item_id      AS top_item_id,
        t.color_id     AS top_color_id,
        t.category_detail_id  AS top_category_id,   
        t.pattern_id   AS top_pattern_id,    

        b.item_id      AS bottom_item_id,
        b.color_id     AS bottom_color_id,
        b.category_detail_id  AS bottom_category_id, 
        b.pattern_id   AS bottom_pattern_id  

    FROM coordinates c
    JOIN items t ON t.item_id = c.top_id
    JOIN items b ON b.item_id = c.bottom_id
    WHERE c.user_id = %s AND c.coordinate_id = %s
    """
    return db_query_one(sql, (user_id, coordinate_id))

# =========================================================
# 学習（good/bad が来たら即更新）
# =========================================================
def apply_one_rating(pref: np.ndarray, outfit_vec: np.ndarray, rating: str, alpha=0.01, beta=0.005) -> np.ndarray:
    updated = pref.copy()
    if rating == "good":
        updated += alpha * outfit_vec
    elif rating == "bad":
        updated -= beta * outfit_vec
    return updated


# def save_feedback_log(user_id: int, coordinate_id: int, rating: str) -> None:
#     """
#     1コーデ1回にしたい場合は UNIQUE(user_id, coordinate_id) を貼ってください。
#     既にある場合は “無視” する実装。
#     """
#     try:
#         db_execute(
#             """
#             INSERT INTO coordinate_feedback (user_id, coordinate_id, rating)
#             VALUES (%s, %s, %s)
#             """,
#             (user_id, coordinate_id, rating),
#         )
#     except mysql.connector.Error:
#         # 重複（既に評価済み）などは無視
#         pass

# ========================================================
# 以下プロフィール表示用
# ========================================================

def _make_labels_from_db() -> tuple[list[str], list[str], list[str]]:
    """
    DBから 1..N のID順でラベル配列を作る
    """
    color_rows = db_query_all(
        "SELECT color_id AS id, color_name AS name FROM colors ORDER BY color_id",
        ()
    )  # TODO: color_name 列名が違うなら修正
    colors = [r["name"] for r in color_rows]

    cat_rows = db_query_all(
        "SELECT category_detail_id AS id, category_detail AS name FROM categories ORDER BY category_id",
        ()
    )  # TODO: category_name 列名が違うなら修正
    categories = [r["name"] for r in cat_rows]

    pat_rows = db_query_all(
        "SELECT pattern_id AS id, pattern_name AS name FROM patterns ORDER BY pattern_id",
        ()
    )  # TODO: pattern_name 列名が違うなら修正
    patterns = [r["name"] for r in pat_rows]

    # 固定値とズレた場合の保険（落とさず補完）
    if len(colors) != NUM_COLORS:
        colors = (colors + [f"Color#{i+1}" for i in range(NUM_COLORS)])[:NUM_COLORS]
    if len(categories) != NUM_CATEGORIES:
        categories = (categories + [f"Category#{i+1}" for i in range(NUM_CATEGORIES)])[:NUM_CATEGORIES]
    if len(patterns) != NUM_PATTERNS:
        patterns = (patterns + [f"Pattern#{i+1}" for i in range(NUM_PATTERNS)])[:NUM_PATTERNS]

    return colors, categories, patterns


def _topk_axes(slice_vec: np.ndarray, labels: list[str], group: str, k: int):
    idxs = np.argsort(-np.abs(slice_vec))[:k]
    out = []
    for i in idxs:
        out.append({
            "key": f"{group}:{int(i)+1}",   # 1-based ID 想定
            "label": labels[int(i)],
            "raw": float(slice_vec[int(i)]),
            "group": group
        })
    return out


def _normalize_0_1(raw_values: list[float]) -> list[float]:
    max_abs = max([abs(v) for v in raw_values] + [1e-6])
    return [((v / max_abs) + 1.0) / 2.0 for v in raw_values]

def _normalize_0_1(raw_values: list[float]) -> list[float]:
    max_abs = max([abs(v) for v in raw_values] + [1e-6])
    return [((v / max_abs) + 1.0) / 2.0 for v in raw_values]


def _count_one(sql: str, params: tuple) -> int:
    row = db_query_one(sql, params)
    if not row:
        return 0
    # COUNT(*) は n / cnt 等で返す想定
    return int(list(row.values())[0])


def _get_user_profile(user_id: int) -> dict:
    """
    ユーザー名（nullならゲスト）, 性別, 身長, 体重を返す
    TODO: usersテーブル/カラム名をあなたのDBに合わせる
    """
    row = db_query_one(
        """
        SELECT
            username,
            gender, 
            height,
            weight
        FROM users
        WHERE user_id = %s
        """,
        (user_id,)
    )

    # userが無い/NULL対策
    if not row:
        return {"userName": "ゲスト", "gender": None, "height": None, "weight": None}

    user_name = row.get("username")
    return {
        "userName": user_name if (user_name is not None and str(user_name).strip() != "") else "ゲスト",
        "gender": row.get("gender"),
        "height": row.get("height"),
        "weight": row.get("weight")
    }


def _get_counts(user_id: int) -> dict:
    item_count = _count_one(
        "SELECT COUNT(*) AS n FROM items WHERE user_id=%s AND is_deleted=0",
        (user_id,)
    )

    coordinate_count = _count_one(
        "SELECT COUNT(*) AS n FROM coordinates WHERE user_id=%s",
        (user_id,)
    )

    favorite_count = _count_one(
        "SELECT COUNT(*) AS n FROM items WHERE user_id=%s AND is_deleted=0 AND is_favorite=1",
        (user_id,)
    )

    return {
        "itemCount": item_count,
        "coordinateCount": coordinate_count,
        "favoriteCount": favorite_count
    }



def _personal_color(pref: np.ndarray, color_labels: list[str]) -> dict:
    """
    色領域（0..NUM_COLORS-1）の最大を「パーソナルカラー」として返す
    """
    colors = pref[0:NUM_COLORS]
    idx = int(np.argmax(colors))  # rawが最大（+方向）を採用
    return {
        "colorId": idx + 1,
        "colorName": color_labels[idx],
        "raw": float(colors[idx])
    }



# =========================================================
# API
# =========================================================
# 学習用エンドポイント
@user_pref.route("/rate_coordinate", methods=["POST"])
def rate_coordinate():
    """
    フロント：
      coordinate_id と rating(good/bad) を送る
      user_id も送る
    """
    print("rate_coordinate called")
    data = request.get_json(force=True)
    user_id = int(data["user_id"])
    coordinate_id = int(data["coordinate_id"])
    rating = str(data["rating"]).lower().strip()

    if rating not in ("good", "bad"):
        return jsonify({"ok": False, "error": "rating must be 'good' or 'bad'"}), 400

    row = fetch_coordinate_features(user_id, coordinate_id)
    if not row:
        return jsonify({"ok": False, "error": "coordinate not found"}), 404

    # itemsから取った特徴IDでコーデベクトル化
    outfit_vec = outfit_vector_from_feature_ids(
        top_color_id=int(row["top_color_id"]),
        top_category_id=int(row["top_category_id"]),
        top_pattern_id=int(row["top_pattern_id"]),
        bottom_color_id=int(row["bottom_color_id"]),
        bottom_category_id=int(row["bottom_category_id"]),
        bottom_pattern_id=int(row["bottom_pattern_id"]),
    )

    pref = load_user_pref(user_id)
    pref2 = apply_one_rating(pref, outfit_vec, rating)

    save_user_pref(user_id, pref2)
    # save_feedback_log(user_id, coordinate_id, rating)

    return jsonify({"ok": True})


# レーダー表示用データのみ返す
@user_pref.route("/get_profile", methods=["GET"])
def profile_summary():
    try:
        user_id = int(request.args.get("user_id", "0"))
    except ValueError:
        return jsonify({"ok": False, "error": "invalid user_id"}), 400

    if user_id <= 0:
        return jsonify({"ok": False, "error": "user_id is required"}), 400

    # ベクトル（内部用）
    pref = load_user_pref(user_id)
    if pref.shape[0] != DIM:
        pref = np.zeros(DIM, dtype=float)

    # ラベル
    color_labels, category_labels, pattern_labels = _make_labels_from_db()

    # パーソナルカラー（色の最大）
    personal = _personal_color(pref, color_labels)

    # レーダー（混合8軸）
    colors = pref[0:NUM_COLORS]
    cats = pref[OFFSET_CAT:OFFSET_CAT + NUM_CATEGORIES]
    pats = pref[OFFSET_PAT:OFFSET_PAT + NUM_PATTERNS]

    axes = (
        _topk_axes(colors, color_labels, "color", 3) +
        _topk_axes(cats, category_labels, "category", 3) +
        _topk_axes(pats, pattern_labels, "pattern", 2)
    )
    raw_vals = [a["raw"] for a in axes]
    norm_vals = _normalize_0_1(raw_vals)
    for a, nv in zip(axes, norm_vals):
        a["norm01"] = float(nv)

    # counts & user profile
    counts = _get_counts(user_id)
    profile = _get_user_profile(user_id)

    return jsonify({
        "ok": True,
        "user_id": user_id,

        # ユーザー情報
        "profile": profile,

        # 件数
        "counts": counts,

        # パーソナルカラー（色で一番伸びてるやつ）
        "personalColor": personal,

        # レーダー描画用（毎回ラベル同梱でOK）
        "labels": {
            "colors": color_labels,
            "categories": category_labels,
            "patterns": pattern_labels
        },
        "axes": axes
    })
