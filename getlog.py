# services/getlog.py
"""
サーバーアクセスログ記録モジュール
全リクエスト・レスポンス・エラーを JSON ラインログで記録
"""
from __future__ import annotations

import json
import os
import time
import uuid
import traceback
import threading
from typing import Any, Dict, Optional

from flask import Flask, request, g, jsonify
from werkzeug.exceptions import HTTPException

# ログファイルパス（getlog.py と同じ階層に出力）
LOG_PATH = os.path.join(os.path.dirname(__file__), "server_log.json")
_LOCK = threading.Lock()


def _safe_int(v: Any) -> Optional[int]:
    """文字列や数値を安全に整数に変換"""
    try:
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
    except Exception:
        pass
    return None


def extract_user_id() -> Optional[int]:
    """
    リクエストから user_id を抽出（優先順: query -> JSON body -> header）
    """
    # 1) query
    uid = _safe_int(request.args.get("user_id")) or _safe_int(request.args.get("userId"))
    if uid is not None:
        return uid


    # 2) JSON body
    try:
        data = request.get_json(silent=True) or {}
        uid = _safe_int(data.get("user_id")) or _safe_int(data.get("userId"))
        if uid is not None:
            return uid
    except Exception:
        pass

    # 3) header（フロントで付けられるなら最強）
    uid = _safe_int(request.headers.get("X-User-Id"))
    return uid


def guess_event_type(path: str, method: str) -> str:
    """エンドポイントからイベント種別を推測"""
    p = (path or "").lower()
    m = (method or "").upper()

    # health
    if p == "/" and m == "GET":
        return "health_check"

    # auth
    if p == "/login" and m == "POST":
        return "auth_login"
    if p == "/signup" and m == "POST":
        return "auth_signup"
    if p.startswith("/auth/password-reset/request"):
        return "auth_pwreset_request"
    if p.startswith("/auth/password-reset/verify-token"):
        return "auth_pwreset_verify"
    if p.startswith("/auth/password-reset/confirm"):
        return "auth_pwreset_confirm"
    if p.startswith("/auth/test-email"):
        return "auth_test_email"
    

    # config
    if p.startswith("/config/test_flags") and m == "GET":
        return "config_read"
    if p.startswith("/config/test_flags") and m == "POST":
        return "config_update"

    # items
    if p == "/add_item" and m == "POST":
        return "item_add"
    if p == "/get_item" and m == "GET":
        return "item_list"
    if p == "/get_item_detail" and m == "GET":
        return "item_detail"
    if p == "/update_item" and m == "POST":
        return "item_update"
    if p == "/favorite" and m == "POST":
        return "favorite_toggle"
    if p == "/get_master_data" and m == "GET":
        return "master_data"

    # profile
    if p == "/update_profile" and m == "POST":
        return "profile_update"

    # coordinates
    if p == "/get_coordinates" and m == "GET":
        return "coord_list"
    if p == "/view_coordinate" and m == "GET":
        return "coord_view"
    if p == "/rate_coordinate" and m == "POST":
        return "coord_rate"


    # AI / weather
    if p == "/send_today_plan" and m == "POST":
        return "ai_outfit_suggest"
    if p == "/generate_image" and m == "POST":
        return "ai_image_generate"
    if p == "/get_weather" and m == "POST":
        return "weather_fetch"

    # static
    if p.startswith("/static/images/generated/"):
        return "static_generated_image"
    if p.startswith("/static/images/"):
        return "static_user_image"

    return "api_call"


def _write_json_line(obj: Dict[str, Any]) -> None:
    """
    server_log.json に 1行JSON で追記。
    例外が出てもアプリケーション本体を落とさない。
    """
    line = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    try:
        with _LOCK:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:
        # ログ書き込み失敗で本処理を巻き込まない
        pass


def _base_fields() -> Dict[str, Any]:
    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "trace_id": getattr(g, "trace_id", None),
        "user_id": getattr(g, "user_id", None),
        "method": request.method,
        "path": request.path,
        "event_type": getattr(g, "event_type", "api_call"),
        "remote_addr": request.headers.get("X-Forwarded-For", request.remote_addr),
        "app_version": request.headers.get("X-App-Version"),
        "user_agent": request.headers.get("User-Agent"),
    }


def init_request_logging(app: Flask) -> None:
    """
    Flask アプリケーションに対してリクエストログを有効化する
    - 全リクエストの時間・status・詳細を記録
    - 予期しない例外（500）を自動的に記録
    """


    @app.errorhandler(HTTPException)
    def _on_http_exception(e: HTTPException):
        trace_id = getattr(g, "trace_id", None) or uuid.uuid4().hex
        setattr(g, "trace_id", trace_id)

        obj = _base_fields()
        obj["kind"] = "http_error"
        obj["status"] = e.code
        obj["error_type"] = type(e).__name__
        obj["message"] = e.description
        _write_json_line(obj)

        # 404は404のまま返す
        return e


    @app.before_request
    def _before():
        """リクエスト開始前の前処理：トレースID・user_id・タイムスタンプを記録"""
        g.start_time = time.time()
        g.trace_id = request.headers.get("X-Trace-Id") or uuid.uuid4().hex
        g.user_id = extract_user_id()
        g.event_type = guess_event_type(request.path, request.method)

        # リクエストボディのキーを軽量に記録
        try:
            body = request.get_json(silent=True)
            g.body_keys = sorted(list(body.keys())) if isinstance(body, dict) else None
        except Exception:
            g.body_keys = None

        g.query_keys = sorted(list(request.args.keys())) if request.args else None
        g.has_file = bool(getattr(request, "files", None)) and len(request.files) > 0

    @app.after_request
    def _after(response):
        """レスポンス返却時にアクセスログを記録"""
        # /log 自体はログに記録しない
        if request.path.lower() == "/log":
            return response

        # 処理時間を計算
        start = getattr(g, "start_time", None)
        duration_ms = int((time.time() - start) * 1000) if start else None

        # 除外対象：静的ファイル
        is_static = request.path.lower().startswith("/static/")
        detail = None if is_static else {
            "status": response.status_code,
            "duration_ms": duration_ms,
            "content_length": request.content_length or 0,
            "query_keys": getattr(g, "query_keys", None),
            "body_keys": getattr(g, "body_keys", None),
            "has_file": getattr(g, "has_file", False),
        }

        obj = _base_fields()
        obj["kind"] = "access"
        obj["status"] = response.status_code
        obj["duration_ms"] = duration_ms
        if detail is not None:
            obj["detail"] = detail

        _write_json_line(obj)

        # トレースIDをレスポンスヘッダに含める（クライアント側ログとの突合用）
        response.headers["X-Trace-Id"] = getattr(g, "trace_id", "")
        return response

    @app.errorhandler(Exception)
    def _on_exception(e: Exception):
        """予期しない例外をキャッチしてエラーログに記録"""
        # トレースIDが無ければ発行
        trace_id = getattr(g, "trace_id", None) or uuid.uuid4().hex
        setattr(g, "trace_id", trace_id)

        obj = _base_fields()
        obj["kind"] = "error"
        obj["error_type"] = type(e).__name__
        obj["message"] = str(e)
        obj["stack"] = traceback.format_exc(limit=12)

        _write_json_line(obj)

        return jsonify({
            "status": "error",
            "trace_id": trace_id,
            "message": "Internal Server Error"
        }), 500
