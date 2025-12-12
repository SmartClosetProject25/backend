import os
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9 以降
from typing import Literal

from dotenv import load_dotenv
import requests
from flask import Blueprint, Flask, jsonify, request

# -------------------------
# 初期設定
# -------------------------

load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"

weather_api = Blueprint('weather_api', __name__)


def kelvin_to_celsius(k: float) -> int:
    """ケルビン → 摂氏（整数）"""
    return round(k - 273.15)


def classify_weather_type(main: str) -> Literal["rain", "snow", "cloud", "clear", "other"]:
    """OpenWeatherMap の weather.main を簡易分類"""
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


@weather_api.route("/api/weather/today", methods=["GET"])
def get_today_weather():
    """
    フロントから lon / lat を受け取り、
    現在の天気 + 現在以降の3時間ごとの予報を返す。

    返すJSON:
    {
        "location": "JP - Tokyo",
        "tempC": 9,
        "precipitationPercent": 0,
        "humidityPercent": 33,
        "today3h": [
            {
                "timeLabel": "12時",
                "tempC": 9,
                "precipitationPercent": 0,
                "weatherType": "cloud"
            },
            ...
        ]
    }
    """

    if not OPENWEATHER_API_KEY:
        return jsonify({"error": "OPENWEATHER_API_KEY is not set"}), 500

    # ---- クエリから lon / lat を取得 ----
    lon = request.args.get("lon")
    lat = request.args.get("lat")

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
            params={"lon": lon_f, "lat": lat_f, "appid": OPENWEATHER_API_KEY},
            timeout=10,
        )
    except requests.RequestException:
        return jsonify({"error": "failed to request current weather"}), 502

    if current_res.status_code != 200:
        return jsonify({"error": "failed to fetch current weather from API"}), 502

    current_json = current_res.json()

    # 現在気温・湿度
    temp_c = kelvin_to_celsius(current_json["main"]["temp"])
    humidity = current_json["main"]["humidity"]

    # 都市名・国コードから location 表示用文字列
    country = current_json.get("sys", {}).get("country", "")
    city_name = current_json.get("name", "")
    location_str = city_name or country or ""

    # 現在の降水確率は forecast から拾うので、とりあえず 0 で初期化
    precip_percent_current = 0

    # ---- 2. 3時間ごとの予報 (/forecast) ----
    try:
        forecast_res = requests.get(
            f"{OPENWEATHER_BASE_URL}/forecast",
            params={"lon": lon_f, "lat": lat_f, "appid": OPENWEATHER_API_KEY},
            timeout=10,
        )
    except requests.RequestException:
        return jsonify({"error": "failed to request forecast"}), 502

    if forecast_res.status_code != 200:
        return jsonify({"error": "failed to fetch forecast from API"}), 502

    forecast_json = forecast_res.json()

    # JST の現在時刻・今日の日付
    jst = ZoneInfo("Asia/Tokyo")
    now_jst = datetime.now(jst)
    today_jst = now_jst.date()

    today_3h_list = []

    for item in forecast_json.get("list", []):
        # item["dt"] は UTC の Unix 時刻
        dt_utc = datetime.utcfromtimestamp(item["dt"])
        dt_jst = dt_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(jst)

        # ---- 現在より過去のデータは除外 ----
        if dt_jst <= now_jst:
            continue

        # ---- 今日だけに限定したい場合 ----
        if dt_jst.date() != today_jst:
            continue

        time_label = f"{dt_jst.hour}時"
        temp_c_3h = kelvin_to_celsius(item["main"]["temp"])

        # pop: 0.0〜1.0 → 降水確率 %
        pop = item.get("pop", 0.0)
        precip_percent = int(round(pop * 100))

        weather_main = item["weather"][0]["main"]
        weather_type = classify_weather_type(weather_main)

        # ★ ここでフロントに渡す形に合わせて key 名を揃える
        today_3h_list.append(
            {
                "timeLabel": time_label,
                "tempC": temp_c_3h,
                "precipitationPercent": precip_percent,
                "weatherType": weather_type,
            }
        )

    # 3時間予報があれば、その最初のものから「現在の降水確率」を拾う（簡易）
    if today_3h_list:
        precip_percent_current = today_3h_list[0]["precipitationPercent"]

    # ---- 3. フロントに返す JSON（指定の形） ----
    response_json = {
        "location": location_str,              # 都市名
        "tempC": temp_c,                       # 現在気温
        "precipitationPercent": precip_percent_current,  # 現在の降水確率（簡易）
        "humidityPercent": humidity,           # 現在の湿度
        "today3h": today_3h_list,              # 3時間ごとの予報
    }
    print("返す天気データ:")
    print(response_json)

    return jsonify(response_json)
