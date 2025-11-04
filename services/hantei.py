# routes/hantei.py
from flask import Blueprint, jsonify, request
from models.prefs_models import(
    init_user_prefs, get_user_prefs, update_prefs_delta,
    add_item, list_items, make_random_coords, list_coords,
    get_random_pair, ab_log_and_learn
)

hantei_bp = Blueprint("hantei", __name__)

# ---------- Prefs ----------
@hantei_bp.post("/users/<user_id>/prefs/init")
def init_prefs(user_id):
    init_user_prefs(user_id)
    return jsonify({"ok": True, "user_id": user_id})

@hantei_bp.get("/users/<user_id>/prefs")
def get_prefs(user_id):
    p = get_user_prefs(user_id)
    if not p:
        return jsonify({"error": "prefs not found"}), 404
    return jsonify({
        "user_id": p["user_id"],
        "w": {"warm": p["w_warm"], "plain": p["w_plain"], "formal": p["w_formal"], "casual": p["w_casual"]},
        "updated_at": p["updated_at"],
    })

# ---------- Items ----------
@hantei_bp.post("/users/<user_id>/items")
def add_item_api(user_id):
    data = request.get_json(force=True) or {}
    if not data.get("category"):
        return jsonify({"error": "category is required"}), 400
    item_id = add_item(
        user_id=user_id,
        category=data["category"],
        color_h=data.get("color_h"),
        tone_plain=data.get("tone_plain", 1 if data.get("pattern") in (None, "plain") else 0),
        tone_pattern=data.get("tone_pattern", 0 if data.get("pattern") in (None, "plain") else 1),
        formal_score=float(data.get("formal_score", 0.5)),
        image_uri=data.get("image_uri"),
    )
    return jsonify({"ok": True, "item_id": item_id})

@hantei_bp.get("/users/<user_id>/items")
def list_item_api(user_id):
    return jsonify(list_items(user_id))

# ---------- Coords ----------
@hantei_bp.post("/users/<user_id>/coords/random")
def make_coords_api(user_id):
    data = request.get_json(silent=True) or {}
    scene = data.get("scene")
    limit = int(data.get("limit", 4))
    out = make_random_coords(user_id, scene, limit)
    return jsonify({"ok": True, "generated": out})

@hantei_bp.get("/users/<user_id>/coords")
def list_coords_api(user_id):
    scene = request.args.get("scene")
    return jsonify(list_coords(user_id, scene))

@hantei_bp.get("/users/<user_id>/pair")
def pair_api(user_id):
    try:
        A, B = get_random_pair(user_id)
        return jsonify({"A": A, "B": B})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

# ---------- AB判定 ----------
@hantei_bp.post("/users/<user_id>/judge")
def judge_api(user_id):
    data = request.get_json(force=True) or {}
    a_id = data.get("a_coord")
    b_id = data.get("b_coord")
    chosen = (data.get("chosen") or "").upper()
    if chosen not in ("A", "B"):
        return jsonify({"error": "chosen must be 'A' or 'B'"}), 400

    try:
        log_id, updated, candidates, recommended = ab_log_and_learn(
            user_id=user_id,
            scene=data.get("scene"),
            temp_c=data.get("temp_c"),
            coord_a=a_id,
            coord_b=b_id,
            chosen=chosen,
            decision_ms=data.get("decision_ms")
        )
        return jsonify({
            "ok": True,
            "log_id": log_id,
            "updated_prefs": updated,
            "candidates": candidates,
            "recommended": recommended
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
