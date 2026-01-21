# services/showlog.py
"""
サーバーログ表示モジュール
/log エンドポイントで server_log.json の内容をHTMLで表示・フィルタリング
"""
from __future__ import annotations

import json
import os
from collections import deque

from flask import Flask, request, render_template_string

# getlog.py の LOG_PATH を使う（ログファイル場所を一元化）
try:
    from getlog import LOG_PATH
except Exception:
    # getlog.py と同階層にない場合の保険
    LOG_PATH = os.path.join(os.path.dirname(__file__), "server_log.json")


def _read_last_logs(limit: int = 200, filters: dict | None = None):
    """
    server_log.json(JSONL) から最後の limit 件を読み取り、フィルタ条件に合うものを返す
    
    フィルタ条件:
      - kind: "access" / "error" / "http_error"
      - event_type: イベントタイプ（ai_outfit_suggest など）
      - status: HTTPステータスコード
      - user_id: ユーザーID
      - duration_min: 最小処理時間（ms）
      - hide_static: "1" の場合 /static/ を除外
    """
    filters = filters or {}
    buf = deque(maxlen=max(10, min(limit, 5000)))  # 安全のため上限

    if not os.path.exists(LOG_PATH):
        return []

    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue

            # --- フィルタ適用 ---
            # kind / event_type
            for k in ("kind", "event_type"):
                v = filters.get(k)
                if v:
                    if str(obj.get(k, "")) != str(v):
                        break
            else:
                # status フィルタ
                st = filters.get("status")
                if st and str(obj.get("status")) != str(st):
                    continue

                # user_id フィルタ
                uid = filters.get("user_id")
                if uid and str(obj.get("user_id")) != str(uid):
                    continue

                # duration_min フィルタ（指定ms以上）
                dmin = filters.get("duration_min")
                if dmin:
                    try:
                        d = obj.get("duration_ms")
                        if d is None or int(d) < int(dmin):
                            continue
                    except Exception:
                        continue

                # static除外フィルタ
                if filters.get("hide_static") == "1":
                    p = str(obj.get("path", "")).lower()
                    if p.startswith("/static/"):
                        continue

                buf.append(obj)

    return list(buf)


def register_log_view(app: Flask) -> None:
    """
    Flask アプリケーションに /log エンドポイント（ログビューア）を登録
    
    クエリパラメータでフィルタ可能:
      - /log?limit=200
      - /log?kind=error
      - /log?event_type=ai_outfit_suggest
      - /log?status=500
      - /log?user_id=1
      - /log?duration_min=1000
      - /log?hide_static=1
    """

    TEMPLATE = r"""
<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Server Log</title>
<style>
  body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial; margin:16px;}
  h1{margin:0 0 12px 0;}
  .bar{display:flex; gap:8px; flex-wrap:wrap; align-items:end; margin-bottom:12px;}
  label{font-size:12px; color:#444; display:block; margin-bottom:4px;}
  input,select{padding:6px 8px; border:1px solid #ccc; border-radius:10px;}
  .btn{padding:7px 10px; border:1px solid #444; background:#111; color:#fff; border-radius:10px; cursor:pointer;}
  .btn2{padding:7px 10px; border:1px solid #aaa; background:#fff; color:#111; border-radius:10px; cursor:pointer; text-decoration:none; display:inline-block;}
  table{width:100%; border-collapse:collapse; font-size:12px;}
  th,td{border-bottom:1px solid #eee; padding:8px; vertical-align:top;}
  th{position:sticky; top:0; background:#fafafa; z-index:1; text-align:left;}
  .row-error{background:#fff3f3;}
  .row-slow{background:#fffbe6;}
  .pill{display:inline-block; padding:2px 8px; border-radius:999px; border:1px solid #ddd; font-size:11px;}
  .muted{color:#666;}
  details{white-space:pre-wrap;}
  .summary{display:flex; gap:8px; flex-wrap:wrap; margin:10px 0 16px 0;}
</style>
</head>
<body>
  <h1>Server Log</h1>

  <form method="get" class="bar">
    <div>
      <label>limit</label>
      <input name="limit" value="{{ q.limit }}" size="6">
    </div>
    <div>
      <label>kind</label>
      <select name="kind">
        <option value="">(all)</option>
        {% for x in kinds %}
          <option value="{{x}}" {% if q.kind==x %}selected{% endif %}>{{x}}</option>
        {% endfor %}
      </select>
    </div>
    <div>
      <label>event_type</label>
      <input name="event_type" value="{{ q.event_type }}" placeholder="ai_outfit_suggest" size="22">
    </div>
    <div>
      <label>status</label>
      <input name="status" value="{{ q.status }}" placeholder="200/404/500" size="10">
    </div>
    <div>
      <label>user_id</label>
      <input name="user_id" value="{{ q.user_id }}" placeholder="1" size="10">
    </div>
    <div>
      <label>duration_min(ms)</label>
      <input name="duration_min" value="{{ q.duration_min }}" placeholder="1000" size="12">
    </div>
    <div>
      <label>hide_static</label>
      <select name="hide_static">
        <option value="0" {% if q.hide_static=='0' %}selected{% endif %}>0</option>
        <option value="1" {% if q.hide_static=='1' %}selected{% endif %}>1</option>
      </select>
    </div>
    <div>
      <button class="btn" type="submit">Filter</button>
      <a class="btn2" href="/log">Reset</a>
    </div>
  </form>

  <div class="summary">
    <span class="pill">rows: {{ summary.rows }}</span>
    <span class="pill">errors: {{ summary.errors }}</span>
    <span class="pill">slow(>=1000ms): {{ summary.slow }}</span>
    <span class="pill">avg(ms): {{ summary.avg }}</span>
    <span class="pill">max(ms): {{ summary.max }}</span>
  </div>

  <table>
    <thead>
      <tr>
        <th>ts</th><th>kind</th><th>event</th><th>status</th><th>ms</th>
        <th>method</th><th>path</th><th>user</th><th>trace</th><th>detail / stack</th>
      </tr>
    </thead>
    <tbody>
      {% for r in rows %}
      <tr class="{% if r.kind in ['error','http_error'] or (r.status and r.status|int >= 500) %}row-error{% elif r.duration_ms and r.duration_ms|int >= 1000 %}row-slow{% endif %}">
        <td class="muted">{{ r.ts }}</td>
        <td><span class="pill">{{ r.kind }}</span></td>
        <td>{{ r.event_type }}</td>
        <td>{{ r.status if r.status is not none else '' }}</td>
        <td>{{ r.duration_ms if r.duration_ms is not none else '' }}</td>
        <td>{{ r.method }}</td>
        <td>{{ r.path }}</td>
        <td>{{ r.user_id if r.user_id is not none else '' }}</td>
        <td class="muted" style="max-width:160px; overflow:hidden; text-overflow:ellipsis;">{{ r.trace_id }}</td>
        <td style="max-width:520px;">
          {% if r.kind in ['error','http_error'] %}
            <details>
              <summary>{{ r.error_type }}: {{ r.message }}</summary>
              {{ r.stack }}
            </details>
          {% else %}
            {% if r.detail %}
              <details>
                <summary>detail</summary>
                {{ r.detail_pretty }}
              </details>
            {% else %}
              <span class="muted">(no detail)</span>
            {% endif %}
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</body>
</html>
"""

    @app.get("/log")
    def _log_view():
        """ログビューアのリクエスト処理"""
        # クエリパラメータ取得
        def _q(name: str, default: str = "") -> str:
            return request.args.get(name, default)

        try:
            limit = int(_q("limit", "200"))
        except Exception:
            limit = 200
        limit = max(10, min(limit, 5000))

        q = {
            "limit": str(limit),
            "kind": _q("kind", ""),
            "event_type": _q("event_type", ""),
            "status": _q("status", ""),
            "user_id": _q("user_id", ""),
            "duration_min": _q("duration_min", ""),
            "hide_static": _q("hide_static", "1"),  # デフォルトは static を隠す
        }

        # フィルタ条件を構築

        filters = {
            "kind": q["kind"],
            "event_type": q["event_type"],
            "status": q["status"],
            "user_id": q["user_id"],
            "duration_min": q["duration_min"],
            "hide_static": q["hide_static"],
        }

        rows = _read_last_logs(limit=limit, filters=filters)

        # 表示用に整形 + サマリ統計を計算
        view_rows = []
        total_ms = 0
        max_ms = 0
        slow = 0
        errors = 0
        ms_count = 0

        for r in rows:
            # 処理時間の統計
            ms = r.get("duration_ms")
            if ms is not None:
                try:
                    ms_i = int(ms)
                    total_ms += ms_i
                    ms_count += 1
                    if ms_i > max_ms:
                        max_ms = ms_i
                    if ms_i >= 1000:
                        slow += 1
                except Exception:
                    pass

            # エラーカウント
            if r.get("kind") in ("error", "http_error") or (r.get("status") is not None and str(r.get("status")).startswith("5")):
                errors += 1

            # detail を JSON 整形
            detail = r.get("detail")
            r["detail_pretty"] = json.dumps(detail, ensure_ascii=False, indent=2) if isinstance(detail, (dict, list)) else (str(detail) if detail is not None else "")
            r["stack"] = r.get("stack") or ""
            r["error_type"] = r.get("error_type") or ""
            r["message"] = r.get("message") or ""
            view_rows.append(r)

        avg = int(total_ms / max(1, ms_count)) if rows else 0

        # サマリ統計を構築
        summary = {
            "rows": len(rows),
            "errors": errors,
            "slow": slow,
            "avg": avg,
            "max": max_ms,
        }

        kinds = ["access", "error", "http_error"]
        return render_template_string(TEMPLATE, rows=view_rows, q=q, kinds=kinds, summary=summary)
