"""高德地图 Web 服务 API 调用模块"""

import os

from dotenv import load_dotenv
import requests

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

AMAP_GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"
AMAP_PLACE_URL = "https://restapi.amap.com/v3/place/text"


def _amap_key() -> str:
    key = os.getenv("AMAP_MAP_KEY", "").strip()
    if not key:
        raise ValueError("未配置 AMAP_MAP_KEY，请在 .env 中填写")
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


if __name__ == "__main__":
    for poi in search_places("西湖"):
        print(poi.get("name"), poi.get("location"))
