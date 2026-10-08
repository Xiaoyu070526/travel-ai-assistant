"""高德地图 Web 服务 API 调用模块"""

import os

from dotenv import load_dotenv
import requests

from src.utils import logging_config

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

logger = logging_config.get_logger(__name__)

AMAP_GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"
AMAP_PLACE_URL = "https://restapi.amap.com/v3/place/text"
AMAP_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"

# 城市知识库 key -> 高德 adcode（天气查询必需）
CITY_ADCODES = {
    "beijing": "110000",
    "shanghai": "310000",
    "xian": "610100",
}


class AmapError(RuntimeError):
    """高德 API 调用失败的基类，便于调用方按类别区分失败原因。"""


class AmapConfigError(AmapError):
    """未配置高德 Key。"""


class AmapRequestError(AmapError):
    """HTTP 请求失败（网络错误 / 非 2xx 状态码）。"""


class AmapAPIError(AmapError):
    """高德返回业务错误码（status != "1"）。"""


class AmapParseError(AmapError):
    """响应解析失败（非法 JSON / 缺少 forecasts 字段）。"""


def _amap_key() -> str:
    key = os.getenv("AMAP_MAP_KEY", "").strip()
    if not key:
        logger.error("未配置高德 Key：请设置环境变量 AMAP_MAP_KEY（或写入项目根目录 .env）")
        raise AmapConfigError("未配置 AMAP_MAP_KEY，请在 .env 中填写（或配置到 Streamlit Secrets）")
    # 把 Key 登记到日志过滤器，作为「绝不打印密钥」的防线（与 llm_client 一致）。
    logging_config.register_secret(key)
    return key


def geocode(address: str, city: str = "") -> dict:
    """地理编码：地址 -> 经纬度"""
    params = {"key": _amap_key(), "address": address, "city": city}
    resp = requests.get(AMAP_GEOCODE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") == "1" and data.get("geocodes"):
        return data["geocodes"][0]
    raise RuntimeError(f"高德地理编码失败: {data.get('info')}")


def search_places(keyword: str, city: str = "") -> list:
    """关键字搜地点：返回地点列表"""
    params = {"key": _amap_key(), "keywords": keyword,
              "city": city, "offset": 20}
    resp = requests.get(AMAP_PLACE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") == "1":
        return data.get("pois", [])
    raise RuntimeError(f"高德地点搜索失败: {data.get('info')}")


def get_weather(city_key: str, extensions: str = "all") -> dict:
    """高德天气查询：extensions="base" 实况天气，"all" 未来 4 天预报。

    Args:
        city_key: 城市知识库 key（beijing / shanghai / xian）
        extensions: base=实况，all=预报

    Returns:
        forecasts[0] 字典（含 casts 预报列表）

    Raises:
        AmapConfigError: 未配置高德 Key
        AmapRequestError: HTTP 请求失败（网络错误 / 非 2xx）
        AmapAPIError: 高德返回业务错误码（status != "1"）
        AmapParseError: 响应不是合法 JSON 或缺少 forecasts 字段
        AmapError: 不支持的城市 key
    """
    adcode = CITY_ADCODES.get((city_key or "").lower())
    if not adcode:
        logger.error("高德天气：暂不支持的城市 key=%s", city_key)
        raise AmapError(f"暂不支持该城市的天气查询: {city_key}")

    key = _amap_key()  # 未配置时抛 AmapConfigError

    params = {"key": key, "city": adcode, "extensions": extensions}
    try:
        resp = requests.get(AMAP_WEATHER_URL, params=params, timeout=10)
    except requests.RequestException as exc:
        logger.error("高德天气请求失败（网络错误 %s）：%s", type(exc).__name__, exc)
        raise AmapRequestError(
            f"高德天气请求失败（网络错误 {type(exc).__name__}），请检查网络连接"
        ) from exc

    if resp.status_code != 200:
        logger.error("高德天气请求失败（HTTP %d）", resp.status_code)
        raise AmapRequestError(f"高德天气请求失败（HTTP {resp.status_code}）")

    try:
        data = resp.json()
    except ValueError as exc:
        logger.error("高德天气响应不是合法 JSON")
        raise AmapParseError("高德天气数据解析失败（响应不是合法 JSON）") from exc

    status = data.get("status")
    if status != "1":
        info = data.get("info") or "未知错误"
        logger.error("高德天气返回错误码 status=%s info=%s", status, info)
        raise AmapAPIError(f"高德天气返回错误码（status={status}）：{info}")

    forecasts = data.get("forecasts")
    if not forecasts:
        logger.error("高德天气响应缺少 forecasts 字段")
        raise AmapParseError("高德天气数据解析失败（缺少 forecasts 字段）")

    logger.info("高德天气查询成功 city=%s adcode=%s", city_key, adcode)
    return forecasts[0]


if __name__ == "__main__":
    for poi in search_places("西湖"):
        print(poi.get("name"), poi.get("location"))
