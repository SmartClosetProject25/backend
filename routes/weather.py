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
# https://api.openweathermap.org/data/2.5/weather?lat=35.6895&lon=139.692&appid=ffbb7ab838bd456572c0e6388f83c7c6


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
    現在の天気＋今日の3時間ごとの予報を返すエンドポイント。

    例:
      /api/weather/today?lon=139.6917&lat=35.6895
    """
    if not OPENWEATHER_API_KEY:
        return jsonify({"error": "OPENWEATHER_API_KEY is not set"}), 500

    lon = request.args.get("lon")
    lat = request.args.get("lat")

    if lon is None or lat is None:
        return jsonify({"error": "lon and lat are required"}), 400

    try:
        lon_f = float(lon)
        lat_f = float(lat)
    except ValueError:
        return jsonify({"error": "lon and lat must be numbers"}), 400

    # -------------------------
    # 1. 現在の天気 (/weather)
    # -------------------------
    try:
        current_res = requests.get(
            f"{OPENWEATHER_BASE_URL}/weather",
            params={
                "lon": lon_f,
                "lat": lat_f,
                "appid": OPENWEATHER_API_KEY,
            },
            timeout=10,
        )
    except requests.RequestException:
        return jsonify({"error": "failed to request current weather"}), 502

    if current_res.status_code != 200:
        return jsonify({"error": "failed to fetch current weather from API"}), 502

    current_json = current_res.json()

    temp_c = kelvin_to_celsius(current_json["main"]["temp"])
    humidity = current_json["main"]["humidity"]

    country = current_json.get("sys", {}).get("country", "")
    city_name = current_json.get("name", "")
    location_str = f"{country} - {city_name}" if city_name else country

    # 現在の降水確率は /weather では直接出ないので、とりあえず 0 で初期化。
    # 後で forecast 側から「今日の最初のデータ」を拾って上書きしてもOK。
    precip_percent_current = 0

    # -------------------------
    # 2. 3時間ごとの予報 (/forecast)
    # -------------------------
    try:
        forecast_res = requests.get(
            f"{OPENWEATHER_BASE_URL}/forecast",
            params={
                "lon": lon_f,
                "lat": lat_f,
                "appid": OPENWEATHER_API_KEY,
            },
            timeout=10,
        )
    except requests.RequestException:
        return jsonify({"error": "failed to request forecast"}), 502

    if forecast_res.status_code != 200:
        return jsonify({"error": "failed to fetch forecast from API"}), 502

    forecast_json = forecast_res.json()

    jst = ZoneInfo("Asia/Tokyo")
    today_jst = datetime.now(jst).date()

    today_3h_list = []

    for item in forecast_json.get("list", []):
        # item["dt"] は UTC の Unix 時刻
        dt_utc = datetime.utcfromtimestamp(item["dt"])
        dt_jst = dt_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(jst)

        # 今日（JST）の分だけ抽出
        if dt_jst.date() != today_jst:
            continue

        time_label = f"{dt_jst.hour}時"
        temp_c_3h = kelvin_to_celsius(item["main"]["temp"])

        # pop: 0.0〜1.0 → %
        pop = item.get("pop", 0.0)
        precip_percent = int(round(pop * 100))

        weather_main = item["weather"][0]["main"]
        weather_type = classify_weather_type(weather_main)

        today_3h_list.append(
            {
                "timeLabel": time_label,
                "timestamp": item["dt"],  # 必要ならフロントで使えるように生のUnix時刻も
                "temperatureC": temp_c_3h,
                "precipitationPercent": precip_percent,
                "weatherType": weather_type,
            }
        )

    # 今日の3時間予報が1件以上あれば、先頭を「現在の降水確率」として流用
    if today_3h_list:
        precip_percent_current = today_3h_list[0]["precipitationPercent"]

    # -------------------------
    # 3. フロントに返す JSON を組み立て
    # -------------------------
    response_json = {
        "date": today_jst.isoformat(),  # "2025-12-12" 形式
        "location": location_str,
        "current": {
            "temperatureC": temp_c,
            "precipitationPercent": precip_percent_current,
            "humidityPercent": humidity,
        },
        "today3h": today_3h_list,
    }
    
    print("返す天気データ:")
    print(response_json)

    return jsonify(response_json)
