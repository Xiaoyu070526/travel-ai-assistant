"""按日期估算景点人流、排队时间与建议游玩时长（启发式预估）。

重要约定：所有输出都是基于「日期类型 + 景点热度」的启发式预估，
不是实时数据；调用方（行程规划页）必须在界面上明确标注"预估"，
绝不冒充真实人流/排队信息（合规要求：不编造）。
"""

from __future__ import annotations

from datetime import date, datetime

# --------------------------------------------------------------------------- #
# 2026 年中国法定节假日（近似范围，用于人流上浮判断）
# --------------------------------------------------------------------------- #
_HOLIDAYS_2026: set[date] = {
    date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3),           # 元旦
    date(2026, 2, 15), date(2026, 2, 16), date(2026, 2, 17),        # 春节
    date(2026, 2, 18), date(2026, 2, 19), date(2026, 2, 20),
    date(2026, 2, 21), date(2026, 2, 22), date(2026, 2, 23),
    date(2026, 4, 4), date(2026, 4, 5), date(2026, 4, 6),           # 清明
    date(2026, 5, 1), date(2026, 5, 2), date(2026, 5, 3),           # 劳动节
    date(2026, 5, 4), date(2026, 5, 5),
    date(2026, 6, 19), date(2026, 6, 20), date(2026, 6, 21),        # 端午
    date(2026, 9, 25), date(2026, 9, 26), date(2026, 9, 27),        # 中秋
    date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3),        # 国庆
    date(2026, 10, 4), date(2026, 10, 5), date(2026, 10, 6),
    date(2026, 10, 7), date(2026, 10, 8),
}

# --------------------------------------------------------------------------- #
# 景点热度（1-5）：知识库暂无该字段，内置已知景点，其余兜底 4
# --------------------------------------------------------------------------- #
_POPULARITY: dict[str, int] = {
    "gugong": 5,        # 故宫
}
DEFAULT_POPULARITY = 4
DEFAULT_DURATION_HOURS = 2.0

_CROWD_ZH = {1: "空旷", 2: "较少", 3: "适中", 4: "较多", 5: "拥挤"}
_CROWD_EN = {1: "Empty", 2: "Light", 3: "Moderate", 4: "Busy", 5: "Very crowded"}
_CROWD_JA = {1: "空いている", 2: "少なめ", 3: "普通", 4: "混雑", 5: "大混雑"}

#: 建议时段 key -> 各语言文案（best_window 字段返回 key，展示用 best_window_for）
_BEST_WINDOW = {
    "early": {
        "zh": "开园后 1-2 小时内（避开人流高峰）",
        "en": "Within 1-2 hours of opening (avoid peak crowds)",
        "ja": "開園後1〜2時間以内（混雑のピークを避ける）",
    },
    "all_day": {
        "zh": "全天均可，建议上午前往",
        "en": "Any time of day; morning recommended",
        "ja": "終日可、午前中の訪問がおすすめ",
    },
}

#: 日期类型 key -> 各语言文案（date_tag 字段返回 key，展示用 date_tag_for）
_DATE_TAG = {
    "holiday": {"zh": "节假日", "en": "Holiday", "ja": "祝日"},
    "weekend": {"zh": "周末", "en": "Weekend", "ja": "週末"},
    "weekday": {"zh": "工作日", "en": "Weekday", "ja": "平日"},
}


def _as_date(value) -> date | None:
    """把 date/datetime/常见字符串（2026.10.16 / 2026-10-16 / 2026/10/16）转 date。"""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        for fmt in ("%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
    return None


def estimate_visit(attr: dict, visit_date) -> dict:
    """估算某景点在某天的游览情况。

    Returns:
        {
            "crowd_index": 1-5,
            "crowd_label_zh": 空旷/较少/适中/较多/拥挤,
            "crowd_label_en": Empty/Light/Moderate/Busy/Very crowded,
            "crowd_label_ja": 空いている/少なめ/普通/混雑/大混雑,
            "queue_minutes": int 预估排队分钟,
            "duration_hours": float 建议游玩时长,
            "best_window": "early" | "all_day"（key，展示用 best_window_for）,
            "date_tag": "holiday" | "weekend" | "weekday"（key，展示用 date_tag_for）,
        }
    """
    d = _as_date(visit_date) or date.today()
    pop = int(_POPULARITY.get(attr.get("id", ""), DEFAULT_POPULARITY))

    if d in _HOLIDAYS_2026:
        factor, date_tag = 1.6, "holiday"
    elif d.weekday() >= 5:
        factor, date_tag = 1.25, "weekend"
    else:
        factor, date_tag = 1.0, "weekday"

    # 连续热度分数（不做整数封顶），用于区分"本来就热门"与"节假日爆热"
    score = pop * factor
    crowd_index = min(5, max(1, int(score // 1.6) + 1))
    queue_minutes = max(0, min(120, int((score - 2) * 12))) if score > 2 else 0

    duration_hours = 3.0 if pop >= 5 else DEFAULT_DURATION_HOURS
    if crowd_index >= 4:
        # 人多时游览体验拉长（排队占用时间）
        duration_hours = round(duration_hours + queue_minutes / 60.0, 1)

    best_window = "early" if crowd_index >= 4 else "all_day"

    return {
        "crowd_index": crowd_index,
        "crowd_label_zh": _CROWD_ZH[crowd_index],
        "crowd_label_en": _CROWD_EN[crowd_index],
        "crowd_label_ja": _CROWD_JA[crowd_index],
        "queue_minutes": queue_minutes,
        "duration_hours": duration_hours,
        "best_window": best_window,
        "date_tag": date_tag,
    }


def crowd_label_for(est: dict, lang: str) -> str:
    """按界面语言返回人流标签。"""
    if lang == "zh":
        return est["crowd_label_zh"]
    if lang == "ja":
        return est["crowd_label_ja"]
    return est["crowd_label_en"]


def best_window_for(est: dict, lang: str) -> str:
    """按界面语言返回建议时段文案。"""
    key = est.get("best_window", "all_day")
    entry = _BEST_WINDOW.get(key) or _BEST_WINDOW["all_day"]
    return entry.get(lang) or entry["en"]


def date_tag_for(est: dict, lang: str) -> str:
    """按界面语言返回日期类型标签。"""
    key = est.get("date_tag", "weekday")
    entry = _DATE_TAG.get(key) or _DATE_TAG["weekday"]
    return entry.get(lang) or entry["en"]


if __name__ == "__main__":
    sample = {"id": "gugong", "name": "故宫"}
    for d in ("2026.10.16", "2026.10.03"):
        est = estimate_visit(sample, d)
        print(d, est["crowd_label_zh"], best_window_for(est, "zh"),
              "|", best_window_for(est, "en"), "|", best_window_for(est, "ja"))
