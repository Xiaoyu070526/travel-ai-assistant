"""Deterministic, calendar-aware allocation with conservative planning buffers.

Travel buffers below are planning assumptions, NOT live routes or train times.
Weekly closures use explicit knowledge-base text; holiday exceptions, tickets
and actual opening calendars still need official confirmation.
"""

from __future__ import annotations

import itertools
import re
from datetime import date, timedelta
from functools import lru_cache

from src.utils.crowd import estimate_visit

PLANNER_VERSION = 2
PACE_HOURS = {"relaxed": 8.0, "balanced": 10.0, "busy": 12.0}
MEAL_REST_HOURS = 1.0
URBAN_RETURN_BUFFER = 1.0
UNKNOWN_TRANSFER_BUFFER = 1.0

# Profiles identify places already present in the knowledge base. Durations are
# minimum planning allowances; district labels only group locations, not routes.
PROFILES = {
    "gugong": {"zone": "beijing-central", "visit_min": 3.5},
    "badaling": {"zone": "beijing-yanqing", "visit_min": 3.0,
                 "dedicated": True, "return_buffer": 2.5},
    "tiantan": {"zone": "beijing-central", "visit_min": 2.5},
    "yiheyuan": {"zone": "beijing-haidian", "visit_min": 3.0},
    "yuanmingyuan": {"zone": "beijing-haidian", "visit_min": 2.5},
    "waitan": {"zone": "shanghai-huangpu", "visit_min": 1.5},
    "dongfangmingzhu": {"zone": "shanghai-lujiazui", "visit_min": 2.0},
    "chenghuangmiao": {"zone": "shanghai-huangpu", "visit_min": 2.5},
    "disney": {"zone": "shanghai-chuansha", "visit_min": 6.0,
               "dedicated": True, "return_buffer": 1.5},
    "shibohui": {"zone": "shanghai-expo", "visit_min": 2.0},
    "bingmayong": {"zone": "xian-lintong", "visit_min": 3.0,
                   "dedicated": True, "return_buffer": 2.5},
    "guchengqiang": {"zone": "xian-central", "visit_min": 2.5},
    "dayanta": {"zone": "xian-yanta", "visit_min": 2.0},
    "huiminjie": {"zone": "xian-central", "visit_min": 1.5},
    "shanxi": {"zone": "xian-yanta", "visit_min": 3.0},
}


def planning_profile(attr: dict) -> dict:
    """Optional explicit planning fields override defaults for future cities."""
    profile = dict(PROFILES.get(attr.get("id"), {}))
    for key, value in (attr.get("planning") or {}).items():
        if key in ("zone", "visit_min", "dedicated", "return_buffer"):
            profile[key] = value
    return profile


def closed_weekdays(attr: dict) -> set[int]:
    explicit = (attr.get("planning") or {}).get("closed_weekdays")
    if explicit is not None:
        return {d for d in explicit if isinstance(d, int) and 0 <= d <= 6}
    parts = []
    for key in ("entry", "entry_en", "entry_ja"):
        entry = attr.get(key) or {}
        parts.append(str(entry.get("hours", "")))
    text = " ".join(parts).lower()
    weekdays = (
        ("一", "monday", "月"), ("二", "tuesday", "火"),
        ("三", "wednesday", "水"), ("四", "thursday", "木"),
        ("五", "friday", "金"), ("六", "saturday", "土"),
        ("日天", "sunday", "日"),
    )
    result = set()
    for index, (cn, en, ja) in enumerate(weekdays):
        patterns = (
            rf"(?:周|星期)[{cn}][^，。;；)]{{0,10}}(?:闭馆|休馆|关闭|休息)",
            rf"closed\s+(?:on\s+)?{en}s?\b",
            rf"{en}s?\s+(?:closed|closure)\b",
            rf"{ja}曜[^、。)]{{0,8}}(?:休館|休園|閉館)",
        )
        if any(re.search(pattern, text) for pattern in patterns):
            result.add(index)
    return result


def planning_visit(attr: dict, visit_date: date) -> dict:
    """Include queue once, even when crowd.py omitted it on quieter days."""
    estimate = estimate_visit(attr, visit_date)
    queue = max(0, estimate.get("queue_minutes", 0)) / 60.0
    # crowd.estimate_visit includes queues only when crowd_index >= 4.
    core = estimate["duration_hours"]
    if estimate.get("crowd_index", 0) >= 4:
        core = max(0, core - queue)
    core = max(core, planning_profile(attr).get("visit_min", 0))
    return {"estimate": estimate, "visit_hours": round(core + queue, 2),
            "core_hours": round(core, 2), "queue_hours": queue}


def _transfer(left: dict, right: dict) -> float:
    lzone = planning_profile(left).get("zone")
    rzone = planning_profile(right).get("zone")
    return 0.5 if lzone and lzone == rzone else UNKNOWN_TRANSFER_BUFFER


def ordered_stops(group: list[dict]) -> list[dict]:
    """Keep known nearby areas together, preserving selection order on ties."""
    if len(group) < 3 or len(group) > 7:
        return list(group)
    order = min(itertools.permutations(range(len(group))), key=lambda seq: (
        sum(_transfer(group[a], group[b]) for a, b in zip(seq, seq[1:])), seq,
    ))
    return [group[i] for i in order]


def day_workload(group: list[dict], visit_date: date) -> dict:
    visits = [planning_visit(attr, visit_date) for attr in group]
    if not group:
        return {"visit_hours": 0.0, "travel_hours": 0.0, "rest_hours": 0.0,
                "total_hours": 0.0, "dedicated": False}
    ordered = ordered_stops(group)
    outbound = max(planning_profile(attr).get("return_buffer", URBAN_RETURN_BUFFER)
                   for attr in group)
    travel = outbound + sum(_transfer(left, right) for left, right in zip(ordered, ordered[1:]))
    visit = sum(v["visit_hours"] for v in visits)
    return {
        "visit_hours": round(visit, 2), "travel_hours": round(travel, 2),
        "rest_hours": MEAL_REST_HOURS,
        "total_hours": round(visit + travel + MEAL_REST_HOURS, 2),
        "dedicated": any(planning_profile(attr).get("dedicated", False) for attr in group),
    }


def allocate_days(selected: list[dict], start: date, days: int,
                  pace: str = "balanced", max_hours: float | None = None) -> tuple:
    """Maximize placed stops, then spread active days and balance total loads.

    Exact subset DP is bounded to 8 stops (current cities have 5 each). Extra
    stops are returned explicitly as unscheduled instead of causing a UI hang.
    Restrictive calendars are solved globally, not by greedily taking day one.
    """
    if days < 1:
        raise ValueError("days must be positive")
    limit = max_hours if max_hours is not None else PACE_HOURS.get(pace, 10.0)
    if limit <= 0:
        raise ValueError("max_hours must be positive")
    stops = selected[:8]
    n = len(stops)
    closed = [closed_weekdays(attr) for attr in stops]

    @lru_cache(maxsize=None)
    def evaluate(day_index, mask):
        indexes = [i for i in range(n) if mask & (1 << i)]
        d = start + timedelta(days=day_index)
        if any(d.weekday() in closed[i] for i in indexes):
            return None
        group = [stops[i] for i in indexes]
        if len(group) > 1 and any(planning_profile(a).get("dedicated") for a in group):
            return None
        load = day_workload(group, d)
        if load["total_hours"] > limit:
            return None
        return load

    # State: (placed mask, active days) -> (squared load, travel, day index sum, masks).
    states = {(0, 0): (0.0, 0.0, 0, ())}
    full = (1 << n) - 1
    for day_index in range(days):
        next_states = {}
        for (placed, active), score in states.items():
            available = full ^ placed
            subset = available
            while True:
                load = evaluate(day_index, subset)
                if load is not None:
                    new_state = (placed | subset, active + bool(subset))
                    candidate = (
                        round(score[0] + load["total_hours"] ** 2, 4),
                        score[1] + load["travel_hours"],
                        score[2] + day_index * bin(subset).count("1"),
                        score[3] + (subset,),
                    )
                    if new_state not in next_states or candidate < next_states[new_state]:
                        next_states[new_state] = candidate
                if not subset:
                    break
                subset = (subset - 1) & available
        states = next_states
    (placed, _), best = min(states.items(), key=lambda item: (
        -bin(item[0][0]).count("1"), -item[0][1], *item[1],
    ))
    groups = [ordered_stops([stops[i] for i in range(n) if mask & (1 << i)])
              for mask in best[3]]
    remaining = [attr for i, attr in enumerate(stops) if not placed & (1 << i)] + selected[8:]
    return groups, remaining
