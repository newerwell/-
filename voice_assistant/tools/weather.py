"""天气查询工具：Open-Meteo（免费、无需 API key、支持 HTTP）。

能力：
- 城市 → 经纬度（geocoding API，支持中文）
- 当前天气 + 今日预报 + 未来 3 天
"""
import json
import urllib.parse
import urllib.request

GEO_URL = "http://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "http://api.open-meteo.com/v1/forecast"

# 天气代码 → 中文描述
WMO_CODES = {
    0: "晴",
    1: "大致晴朗",
    2: "多云",
    3: "阴",
    45: "雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "大毛毛雨",
    56: "冻毛毛雨",
    57: "强冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "强冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "中阵雨",
    82: "强阵雨",
    85: "小阵雪",
    86: "大阵雪",
    95: "雷暴",
    96: "雷暴伴冰雹",
    99: "强雷暴伴冰雹",
}


def _http_get_json(url: str, timeout: int = 15) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "voice-assistant/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def geocode(city: str) -> dict | None:
    """城市名 → 经纬度。返回 {name, latitude, longitude, country} 或 None。"""
    q = urllib.parse.quote(city)
    data = _http_get_json(f"{GEO_URL}?name={q}&count=1&language=zh")
    results = data.get("results") or []
    if not results:
        return None
    r = results[0]
    return {
        "name": r.get("name", city),
        "latitude": r["latitude"],
        "longitude": r["longitude"],
        "country": r.get("country", ""),
        "admin1": r.get("admin1", ""),
    }


def get_weather(city: str) -> str:
    """查询城市天气，返回人类可读的中文描述。"""
    loc = geocode(city)
    if loc is None:
        return f"抱歉，没找到城市「{city}」的天气信息。"

    params = {
        "latitude": loc["latitude"],
        "longitude": loc["longitude"],
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min",
        "forecast_days": 3,
        "timezone": "Asia/Shanghai",
    }
    url = FORECAST_URL + "?" + urllib.parse.urlencode(params)
    data = _http_get_json(url)

    cur = data.get("current", {})
    daily = data.get("daily", {})
    place = f"{loc['name']}（{loc['country']}）"
    if not cur:
        return f"{place}：天气数据获取失败。"

    desc = WMO_CODES.get(cur.get("weather_code", 0), "未知")
    temp = cur.get("temperature_2m", "?")
    hum = cur.get("relative_humidity_2m", "?")
    wind = cur.get("wind_speed_10m", "?")

    lines = [
        f"{place}当前天气：{desc}，{temp}°C，湿度{hum}%，风速{wind}km/h。",
    ]
    if daily:
        days = daily.get("time", [])
        codes = daily.get("weather_code", [])
        tmax = daily.get("temperature_2m_max", [])
        tmin = daily.get("temperature_2m_min", [])
        for i in range(min(3, len(days))):
            label = "今天" if i == 0 else ("明天" if i == 1 else "后天")
            d = WMO_CODES.get(codes[i], "未知")
            lines.append(f"{label}：{d}，{tmin[i]}~{tmax[i]}°C。")
    return " ".join(lines)


def get_weather_tool_schema() -> dict:
    """LLM 工具调用 schema。"""
    return {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气和未来三天预报。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称，如：北京、上海、广州"}
                },
                "required": ["city"],
            },
        },
    }
