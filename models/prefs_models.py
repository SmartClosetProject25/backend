import os, json, time, uuid, random
from typing import Dict, List, Optional, Tuple

from db_con import get_conn  # ← ここがポイント：接続はdb_conから
# init_db は app.py 側で呼ぶ想定（SKIP_INIT_DB対応のため）

def now_ms() -> int:
    return int(time.time() * 1000)

def gen_id() -> str:
    return str(uuid.uuid4())

FEATURE_KEYS = ["warm", "plain", "formal", "casual"]

# ---------------------------
# Feature helpers
# ---------------------------
def item_to_features(item_row: dict) -> Dict[str, float]:
    h = item_row.get("color_h") or 0
    warm = 1.0 if (0 <= h <= 60) or (300 <= h <= 360) else 0.0
    plain = 1.0 if (item_row.get("tone_plain") or 0) == 1 else 0.0
    formal = float(item_row.get("formal_score") or 0.0)
    casual = max(0.0, 1.0 - formal)
    return {"warm": warm, "plain": plain, "formal": formal, "casual": casual}

def avg_features(items: List[dict]) -> Dict[str, float]:
    if not items:
        return {k: 0.0 for k in FEATURE_KEYS}
    sums = {k: 0.0 for k in FEATURE_KEYS}
    for it in items:
        f = item_to_features(it)
        for k in FEATURE_KEYS:
            sums[k] += f[k]
    n = float(len(items))
    return {k: sums[k] / n for k in FEATURE_KEYS}

def dict_diff(a: Dict[str, float], b: Dict[str, float]) -> Dict[str, float]:
    return {k: a.get(k, 0.0) - b.get(k, 0.0) for k in FEATURE_KEYS}

# ---------------------------
# Prefs
# ---------------------------
def init_user_prefs(user_id: str):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM user_prefs WHERE user_id=%s", (user_id,))
        if cur.fetchone():
            cur.close()
            return
        cur.execute(
            "INSERT INTO user_prefs(user_id,w_warm,w_plain,w_formal,w_casual,updated_at) VALUES(%s,0,0,0,0,%s)",
            (user_id, now_ms())
        )
        cur.close()
    finally:
        conn.close()

def get_user_prefs(user_id: str) -> Optional[dict]:
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM user_prefs WHERE user_id=%s", (user_id,))
        row = cur.fetchone()
        cur.close()
        return row
    finally:
        conn.close()

def update_prefs_delta(user_id: str, delta: Dict[str, float], lr: float = 0.05) -> dict:
    p = get_user_prefs(user_id)
    if not p:
        init_user_prefs(user_id)
        p = get_user_prefs(user_id)

    new_vals = {
        "w_warm":   p["w_warm"]   + lr * float(delta["warm"]),
        "w_plain":  p["w_plain"]  + lr * float(delta["plain"]),
        "w_formal": p["w_formal"] + lr * float(delta["formal"]),
        "w_casual": p["w_casual"] + lr * float(delta["casual"]),
        "updated_at": now_ms()
    }
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE user_prefs
               SET w_warm=%s, w_plain=%s, w_formal=%s, w_casual=%s, updated_at=%s
               WHERE user_id=%s""",
            (new_vals["w_warm"], new_vals["w_plain"], new_vals["w_formal"], new_vals["w_casual"], new_vals["updated_at"], user_id)
        )
        cur.close()
    finally:
        conn.close()
    return {
        "warm": new_vals["w_warm"],
        "plain": new_vals["w_plain"],
        "formal": new_vals["w_formal"],
        "casual": new_vals["w_casual"]
    }

# ---------------------------
# Closet items
# ---------------------------
def add_item(user_id: str, category: str, color_h: Optional[int], tone_plain: int, tone_pattern: int,
             formal_score: float, image_uri: Optional[str]) -> str:
    item_id = gen_id()
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO closet_items(item_id,user_id,category,color_h,tone_plain,tone_pattern,formal_score,image_uri,created_at)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (item_id, user_id, category, color_h, tone_plain, tone_pattern, formal_score, image_uri, now_ms())
        )
        cur.close()
    finally:
        conn.close()
    return item_id

def list_items(user_id: str) -> List[dict]:
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT * FROM closet_items
                       WHERE user_id=%s ORDER BY created_at DESC""", (user_id,))
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()

def list_items_by_category(user_id: str, category: str) -> List[dict]:
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT * FROM closet_items
                       WHERE user_id=%s AND category=%s""", (user_id, category))
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()

# ---------------------------
# Coords
# ---------------------------
def insert_coord(user_id: str, top_id: str, bottom_id: str, shoes_id: Optional[str],
                 scene: Optional[str], features: Dict[str, float]) -> str:
    coord_id = gen_id()
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO coord_combinations(coord_id,user_id,top_id,bottom_id,shoes_id,scene,style_label,features_json,created_at)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (coord_id, user_id, top_id, bottom_id, shoes_id, scene, None, json.dumps(features, ensure_ascii=False), now_ms())
        )
        cur.close()
    finally:
        conn.close()
    return coord_id

def get_coord(coord_id: str) -> Optional[dict]:
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM coord_combinations WHERE coord_id=%s", (coord_id,))
        row = cur.fetchone()
        cur.close()
        return row
    finally:
        conn.close()

def list_coords(user_id: str, scene: Optional[str] = None) -> List[dict]:
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        if scene:
            cur.execute("""SELECT * FROM coord_combinations
                           WHERE user_id=%s AND scene=%s
                           ORDER BY created_at DESC""", (user_id, scene))
        else:
            cur.execute("""SELECT * FROM coord_combinations
                           WHERE user_id=%s
                           ORDER BY created_at DESC""", (user_id,))
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()

def make_random_coords(user_id: str, scene: Optional[str], limit: int = 4) -> List[dict]:
    tops = list_items_by_category(user_id, "top")
    bottoms = list_items_by_category(user_id, "bottom")
    out = []
    for _ in range(limit):
        if not tops or not bottoms:
            break
        t = random.choice(tops)
        b = random.choice(bottoms)
        feats = avg_features([t, b])
        coord_id = insert_coord(user_id, t["item_id"], b["item_id"], None, scene, feats)
        out.append({
            "coord_id": coord_id,
            "user_id": user_id,
            "top_id": t["item_id"],
            "bottom_id": b["item_id"],
            "shoes_id": None,
            "scene": scene,
            "features": feats
        })
    return out

def get_random_pair(user_id: str) -> Tuple[dict, dict]:
    rows = list_coords(user_id)
    if len(rows) < 2:
        raise ValueError("not enough coords")
    import random as _random
    pair = _random.sample(rows, 2)
    def with_features(r):
        r2 = dict(r)
        r2["features"] = json.loads(r["features_json"])
        return r2
    return with_features(pair[0]), with_features(pair[1])

# ---------------------------
# A/B & recommend
# ---------------------------
def ab_log_and_learn(user_id: str, scene: Optional[str], temp_c: Optional[float],
                     coord_a: str, coord_b: str, chosen: str, decision_ms: Optional[int]) -> Tuple[int, dict, List[dict], dict]:
    a = get_coord(coord_a)
    b = get_coord(coord_b)
    if not a or not b:
        raise ValueError("coord not found")

    fA = json.loads(a["features_json"])
    fB = json.loads(b["features_json"])
    delta = dict_diff(fA, fB) if chosen == "A" else dict_diff(fB, fA)
    updated = update_prefs_delta(user_id, delta, lr=0.05)

    # log
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO ab_logs(user_id,scene,temp_c,coord_a,coord_b,chosen,decision_ms,created_at)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
            (user_id, scene, temp_c, coord_a, coord_b, chosen, decision_ms, now_ms())
        )
        log_id = cur.lastrowid
        cur.close()
    finally:
        conn.close()

    # candidates & recommendation
    def score(w, x):
        return w["warm"]*x["warm"] + w["plain"]*x["plain"] + w["formal"]*x["formal"] + w["casual"]*x["casual"]

    all_rows = list_coords(user_id)
    remain = [r for r in all_rows if r["coord_id"] not in (coord_a, coord_b)]
    candidates = []
    for r in remain:
        x = json.loads(r["features_json"])
        s = score(updated, x)
        candidates.append({"coord_id": r["coord_id"], "score": s})
    candidates.sort(key=lambda d: d["score"], reverse=True)
    recommended = candidates[0] if candidates else {}

    return log_id, updated, candidates, recommended
