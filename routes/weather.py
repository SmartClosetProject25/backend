# routes/weather.py
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from flask import Blueprint, jsonify, request

# ===== env =====
load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"

# JST
JST = ZoneInfo("Asia/Tokyo")

weather_api = Blueprint("weather_api", __name__)


def _to_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _weather_type_from_id(ow_id: int) -> str:
    """
    OpenWeather weather condition id をざっくりUI用タイプに変換
    """
    # Thunderstorm: 200-232
    if 200 <= ow_id <= 232:
        return "thunder"
    # Drizzle: 300-321
    if 300 <= ow_id <= 321:
        return "rain"
    # Rain: 500-531
    if 500 <= ow_id <= 531:
        return "rain"
    # Snow: 600-622
    if 600 <= ow_id <= 622:
        return "snow"
    # Atmosphere: 701-781 (mist, fog, etc.)
    if 701 <= ow_id <= 781:
        return "fog"
    # Clear: 800
    if ow_id == 800:
        return "sun"
    # Clouds: 801-804
    if 801 <= ow_id <= 804:
        return "cloud"
    return "cloud"


def _safe_get(d: Dict[str, Any], path: List[str], default=None):
    cur: Any = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


@weather_api.route("/get_weather", methods=["POST"])
def get_weather():
    """
    受け取りJSON例:
    { "lon": 139.6917, "lat": 35.6895 }

    返すJSON:
    {
      "location": "Tokyo",
      "tempC": 9.1,
      "precipitationPercent": 0,
      "humidityPercent": 45,
      "today3h": [
        { "timeLabel": "06:00", "tempC": 9.0, "precipitationPercent": 0, "weatherType": "cloud" }
      ]
    }
    """
    data = request.get_json(silent=True) or {}

    lon = _to_float(data.get("lon"))
    lat = _to_float(data.get("lat"))

    print(f"[get_weather] received lon={lon}, lat={lat}")

    if lon is None or lat is None:
        return jsonify({"error": "lon/lat required", "received": data}), 400

    if not OPENWEATHER_API_KEY:
        # ここが空だと常に失敗します（IDE起動でenvが読めてない等）
        return jsonify({"error": "OPENWEATHER_API_KEY is missing"}), 500

    # ---- OpenWeather current ----
    try:
        current_res = requests.get(
            f"{OPENWEATHER_BASE_URL}/weather",
            params={
                "lat": lat,
                "lon": lon,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric",
            },
            timeout=(3, 10),  # (connect, read)
        )
    except requests.Timeout:
        return jsonify({"error": "OpenWeather /weather timeout"}), 504
    except Exception as e:
        return jsonify({"error": "OpenWeather /weather request failed", "detail": str(e)}), 502

    if current_res.status_code != 200:
        # ここで「本当の原因(401/429/400等)」を返す
        print("[get_weather] /weather failed:", current_res.status_code, current_res.text)
        return (
            jsonify(
                {
                    "error": "OpenWeather /weather error",
                    "status": current_res.status_code,
                    "body": current_res.text,
                }
            ),
            current_res.status_code,
        )

    current_json = current_res.json()

    # ---- OpenWeather forecast (3h) ----
    try:
        forecast_res = requests.get(
            f"{OPENWEATHER_BASE_URL}/forecast",
            params={
                "lat": lat,
                "lon": lon,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric",
            },
            timeout=(3, 10),
        )
    except requests.Timeout:
        return jsonify({"error": "OpenWeather /forecast timeout"}), 504
    except Exception as e:
        return jsonify({"error": "OpenWeather /forecast request failed", "detail": str(e)}), 502

    if forecast_res.status_code != 200:
        print("[get_weather] /forecast failed:", forecast_res.status_code, forecast_res.text)
        return (
            jsonify(
                {
                    "error": "OpenWeather /forecast error",
                    "status": forecast_res.status_code,
                    "body": forecast_res.text,
                }
            ),
            forecast_res.status_code,
        )

    forecast_json = forecast_res.json()

    # ---- location ----
    # OpenWeather /weather の name を優先して表示（取れない場合は空）
    location_str = current_json.get("name") or "Unknown"

    # ---- current values ----
    temp_c = _safe_get(current_json, ["main", "temp"])
    humidity = _safe_get(current_json, ["main", "humidity"])

    # fallback
    if temp_c is None:
        temp_c = 0.0
    if humidity is None:
        humidity = 0

    # ---- build today 3h list in JST ----
    today = datetime.now(JST).date()

    today_3h_list: List[Dict[str, Any]] = []
    items = forecast_json.get("list") or []
    for it in items:
        # dt is unix seconds (UTC)
        dt_utc = it.get("dt")
        if not isinstance(dt_utc, int):
            continue
        dt_jst = datetime.fromtimestamp(dt_utc, tz=ZoneInfo("UTC")).astimezone(JST)

        if dt_jst.date() != today:
            continue

        t = _safe_get(it, ["main", "temp"], 0.0)
        pop = it.get("pop", 0.0)  # 0.0-1.0
        try:
            pop_percent = int(round(float(pop) * 100))
        except Exception:
            pop_percent = 0

        wid = 800
        wlist = it.get("weather") or []
        if isinstance(wlist, list) and len(wlist) > 0 and isinstance(wlist[0], dict):
            wid = int(wlist[0].get("id", 800))

        today_3h_list.append(
            {
                "timeLabel": dt_jst.strftime("%H:%M"),
                "tempC": float(t) if t is not None else 0.0,
                "precipitationPercent": pop_percent,
                "weatherType": _weather_type_from_id(wid),
            }
        )

    # today3h が空の場合でも落とさない
    precip_percent_current = today_3h_list[0]["precipitationPercent"] if today_3h_list else 0

    response_json = {
        "location": location_str,
        "tempC": float(temp_c),
        "precipitationPercent": int(precip_percent_current),
        "humidityPercent": int(humidity),
        "today3h": today_3h_list,
    }

    print("[get_weather] response:", response_json)
    return jsonify(response_json), 200
