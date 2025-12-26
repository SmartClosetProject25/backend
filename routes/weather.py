import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Literal

from dotenv import load_dotenv
import requests
from flask import Blueprint, jsonify, request

load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"

weather_api = Blueprint('weather_api', __name__)


def kelvin_to_celsius(k: float) -> int:
    return round(k - 273.15)


def classify_weather_type(main: str) -> Literal["rain", "snow", "cloud", "clear", "other"]:
    main_lower = main.lower()
    if "rain" in main_lower:
        return "rain"
    if "snow" in main_lower:
        return "snow"
    if "cloud" in main_lower:
        return "cloud"
    if "clear" in main_lower:
        return "clear"
    return "other"


@weather_api.route("/get_weather", methods=["POST"])
def get_weather():
    """
    Android(POST + JSON) で受け取る:
      { "lon": 139.6917, "lat": 35.6895 }

    返すJSON:
    {
      "location": "...",
      "tempC": 9,
      "precipitationPercent": 0,
      "humidityPercent": 33,
      "today3h": [ { "timeLabel": "...", "tempC": 9, "precipitationPercent": 0, "weatherType": "cloud" } ]
    }
    """

    if not OPENWEATHER_API_KEY:
        return jsonify({"error": "OPENWEATHER_API_KEY is not set"}), 500

    # ---- Body(JSON) から lon/lat を取得 ----
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body is required"}), 400

    lon = data.get("lon")
    lat = data.get("lat")
    if lon is None or lat is None:
        return jsonify({"error": "lon and lat are required"}), 400

    try:
        lon_f = float(lon)
        lat_f = float(lat)
    except ValueError:
        return jsonify({"error": "lon and lat must be numbers"}), 400

    # ---- 1. 現在の天気 (/weather) ----
    try:
        current_res = requests.get(
            f"{OPENWEATHER_BASE_URL}/weather",
            params={"lon": lon_f, "lat": lat_f, "appid": OPENWEATHER_API_KEY, "lang": "ja"},
            timeout=10,
        )
    except requests.RequestException:
        return jsonify({"error": "failed to request current weather"}), 502

    if current_res.status_code != 200:
        return jsonify({"error": "failed to fetch current weather from API"}), 502

    current_json = current_res.json()

    temp_c = kelvin_to_celsius(current_json["main"]["temp"])
    humidity = current_json["main"]["humidity"]

    # 都市名（必要なら lang=ja を追加して日本語化できる）
    city_name = current_json.get("name", "")
    country = current_json.get("sys", {}).get("country", "")
    location_str = city_name or country or ""

    precip_percent_current = 0

    # ---- 2. 3時間ごとの予報 (/forecast) ----
    try:
        forecast_res = requests.get(
            f"{OPENWEATHER_BASE_URL}/forecast",
            params={"lon": lon_f, "lat": lat_f, "appid": OPENWEATHER_API_KEY, "lang": "ja"},
            timeout=10,
        )
    except requests.RequestException:
        return jsonify({"error": "failed to request forecast"}), 502

    if forecast_res.status_code != 200:
        return jsonify({"error": "failed to fetch forecast from API"}), 502

    forecast_json = forecast_res.json()

    jst = ZoneInfo("Asia/Tokyo")
    now_jst = datetime.now(jst)
    today_jst = now_jst.date()

    today_3h_list = []

    for item in forecast_json.get("list", []):
        dt_utc = datetime.utcfromtimestamp(item["dt"])
        dt_jst = dt_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(jst)

        # 現在より未来のみ
        if dt_jst <= now_jst:
            continue
        # 今日だけ
        if dt_jst.date() != today_jst:
            continue

        time_label = f"{dt_jst.hour}時"
        temp_c_3h = kelvin_to_celsius(item["main"]["temp"])

        pop = item.get("pop", 0.0)
        precip_percent = int(round(pop * 100))

        weather_main = item["weather"][0]["main"]
        weather_type = classify_weather_type(weather_main)

        today_3h_list.append(
            {
                "timeLabel": time_label,
                "tempC": temp_c_3h,
                "precipitationPercent": precip_percent,
                "weatherType": weather_type,
            }
        )

    if today_3h_list:
        precip_percent_current = today_3h_list[0]["precipitationPercent"]

    response_json = {
        "location": location_str,
        "tempC": temp_c,
        "precipitationPercent": precip_percent_current,
        "humidityPercent": humidity,
        "today3h": today_3h_list,
    }

    print("返す天気データ:")
    print(response_json)

    return jsonify(response_json)
