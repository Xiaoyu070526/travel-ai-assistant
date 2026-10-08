"""知识库数据加载：读取城市/景点知识库 JSON，并按界面语言切换多语言字段。

语言优先级（对所有可翻译字段一致）：``_{lang}``（如 ``_ja``）> ``_en`` > 中文原字段。
默认 ``lang="zh"`` 直接返回原始中文，保证原有中文界面完全兼容。
"""

import json
import os
from typing import Any

DATA_CONTENT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "content"
)

#: 城市层需要按语言切换的「整字段替换」字段
_CITY_TEXT_FIELDS = ("description", "highlights", "notes", "transport", "apps", "essentials")

#: 景点层需要按语言切换的「整字段替换」字段。
#: 注意：``status`` 不在此处替换——它是规范枚举（用于配色映射），展示层用
#: :func:`src.utils.i18n.status_label` 按语言取标签。
_ATTR_TEXT_FIELDS = ("description", "category", "entry", "alternatives")


def _get_field(node: dict, field: str, lang: str) -> Any:
    """按语言优先级获取字段值：``_{lang}`` > ``_en`` > 原字段（中文）。

    例如 ``_get_field(city_node, "description", "ja")`` 优先找 ``description_ja``，
    无则回退 ``description_en``，仍无则返回原 ``description``（中文）。
    """
    localized = node.get(f"{field}_{lang}")
    if localized is not None:
        return localized
    fallback_en = node.get(f"{field}_en")
    if fallback_en is not None:
        return fallback_en
    return node.get(field)


def _apply_language(raw: dict, lang: str) -> dict:
    """将 raw 城市数据按语言替换可翻译字段（city 层 + attraction 层）。

    - ``name`` 不在此处替换：它是专有名词，保留 ``name``（中文）+ ``name_en``（英文），
      并额外提供 ``name_ja``；展示层用 :func:`display_name` 选取。
    - 非文本字段（布尔 / 数字 / URL / id）保持原值，绝不因语言切换被篡改。
    """
    lang = (lang or "zh").lower()
    if lang == "zh":
        return raw

    # 城市层
    city = raw.get("city") or {}
    if city:
        for field in _CITY_TEXT_FIELDS:
            val = _get_field(city, field, lang)
            if val is not None:
                city[field] = val

    # 景点层
    for attr in raw.get("attractions", []):
        for field in _ATTR_TEXT_FIELDS:
            val = _get_field(attr, field, lang)
            if val is not None:
                attr[field] = val

        # passport 是「文本 + 事实数值」混合，只替换其中的文本字段，
        # 避免重复/篡改 bookable_online、price_cny 等事实数据。
        passport = attr.get("passport")
        if isinstance(passport, dict):
            for field in ("platform", "price_notes"):
                val = _get_field(passport, field, lang)
                if val is not None:
                    passport[field] = val

    return raw


def display_name(node: dict, lang: str) -> str:
    """返回景点/城市的展示名（本地名 + 可选另一种语言注释）。

    - zh → ``故宫 (Forbidden City)``
    - en → ``Forbidden City (故宫)``
    - ja → ``故宮 (Forbidden City)``
    """
    lang = (lang or "zh").lower()
    name = node.get("name", "") or ""
    name_en = node.get("name_en", "") or ""
    if lang == "zh":
        primary, secondary = name, name_en
    elif lang == "ja":
        primary = node.get("name_ja") or name
        secondary = name_en
    else:  # en 及其它语言
        primary = name_en or name
        secondary = name
    primary = primary or ""
    secondary = secondary or ""
    if secondary and secondary != primary:
        return f"{primary} ({secondary})"
    return primary


def load_city_data(city: str, lang: str = "zh") -> dict[str, Any] | None:
    """加载指定城市的知识库数据，并根据语言切换多语言字段。

    Args:
        city: 城市名拼音或英文名，如 'beijing', 'shanghai', 'xian'
        lang: 界面语言，如 'zh', 'en', 'ja'；默认 'zh'（保持中文兼容）

    Returns:
        城市数据字典（已按语言切换核心字段），文件不存在返回 None
    """
    path = os.path.join(DATA_CONTENT_DIR, f"{city.lower()}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    return _apply_language(raw, lang)


def load_attraction(city: str, attraction_id: str, lang: str = "zh") -> dict[str, Any] | None:
    """加载指定景点数据，支持语言切换。"""
    data = load_city_data(city, lang=lang)
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
    # 自测（中文 / 英文 / 日文）
    for lang in ("zh", "en", "ja"):
        data = load_city_data("beijing", lang=lang)
        if data:
            print(f"[{lang}] {display_name(data['city'], lang)}: "
                  f"{len(data['attractions'])} attractions")
            print(f"    desc: {data['city']['description'][:40]}")
            a = data["attractions"][0]
            print(f"    attr0: {display_name(a, lang)} | {a['status']}")
