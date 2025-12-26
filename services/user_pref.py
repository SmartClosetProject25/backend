from __future__ import annotations

import os
import json
import random
from typing import Any, Dict, List, Tuple, Optional

from utils.db_con import get_db_connection
import numpy as np
from mysql.connector import pooling
from flask import Blueprint, Flask, request, jsonify

user_pref = Blueprint('user_pref', __name__)

# DB接続
def db_query_one(sql, params=()):
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        row = cur.fetchone()
        cur.close()
        return row
    finally:
        conn.close()


def db_query_all(sql, params=()):
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()


def db_execute(sql, params=()):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        affected = cur.rowcount
        cur.close()
        return affected
    finally:
        conn.close()


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
# ベクトル化（itemsに“必要な特徴が全部ある”前提）
# ※ Itemsカラム名はあなたが後で合わせて修正してOK
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
    IDは 1 始まり想定。0始まりなら -1 を外してください。
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


# def cosine_sim(v1: np.ndarray, v2: np.ndarray) -> float:
#     return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6))


# =========================================================
# coordinates -> items JOIN（学習用）
# coordinate_id から top/bottom の特徴を取る
# =========================================================
def fetch_coordinate_features(user_id: int, coordinate_id: int) -> Optional[Dict[str, Any]]:
    """
    items に「欲しいデータは全部ある」前提。
    ここで items のカラム名をあなたの環境に合わせて修正してください。
    """
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


# =========================================================
# API
# =========================================================
@user_pref.route("/rate_coordinate", methods=["POST"])
def rate_coordinate():
    """
    フロント：
      coordinate_id と rating(good/bad) を送る
      user_id も送る（ログイン実装済みなら token からでもOK）

    受信例(JSON):
      { "user_id": 1, "coordinate_id": 123, "rating": "good" }
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
