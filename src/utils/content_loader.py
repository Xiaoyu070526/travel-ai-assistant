"""知识库数据加载：读取城市/景点知识库 JSON"""

import json
import os
from typing import Any

DATA_CONTENT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "content"
)


def load_city_data(city: str) -> dict[str, Any] | None:
    """加载指定城市的知识库数据

    Args:
        city: 城市名拼音或英文名，如 'beijing', 'shanghai', 'xian'

    Returns:
        城市数据字典，文件不存在返回 None
    """
    path = os.path.join(DATA_CONTENT_DIR, f"{city.lower()}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_attraction(city: str, attraction_id: str) -> dict[str, Any] | None:
    """加载指定景点数据"""
    data = load_city_data(city)
    if not data or "attractions" not in data:
        return None
    for attr in data["attractions"]:
        if attr.get("id") == attraction_id:
            return attr
    return None


def list_cities() -> list[str]:
    """列出所有可用的城市知识库"""
    if not os.path.exists(DATA_CONTENT_DIR):
        return []
    files = [f for f in os.listdir(DATA_CONTENT_DIR) if f.endswith(".json")]
    return [f.replace(".json", "") for f in files]


def get_passport_status_label(status: str) -> str:
    """将状态字符串转换为带emoji的标签"""
    mapping = {
        "✅ 可订": "✅ 可订",
        "⚠️ 需人工": "⚠️ 需人工",
        "❌ 不可": "❌ 不可",
    }
    return mapping.get(status, status)


if __name__ == "__main__":
    # 自测
    data = load_city_data("beijing")
    if data:
        print(f"Loaded Beijing: {len(data['attractions'])} attractions")
        for attr in data["attractions"]:
            print(f"  - {attr['name']} ({attr['status']})")
    else:
        print("Beijing data not found")
