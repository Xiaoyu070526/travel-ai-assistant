"""Pure travel-plan assembly shared by Streamlit preview and PDF export.

No network calls, policy eligibility decisions or live-price claims are made here.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import date, timedelta
from typing import Any

from src.utils.content_loader import display_name
from src.utils.crowd import best_window_for, crowd_label_for
from src.utils.i18n import status_label, t, weather_term
from src.utils.plan_i18n import pt
from src.utils.itinerary import (
    PLANNER_VERSION, PACE_HOURS, allocate_days, day_workload, planning_visit,
)

INTEREST_TERMS = {
    "culture": ("博物", "历史", "文化", "宫", "寺", "古", "遗址", "museum", "palace", "historic", "temple"),
    "nature": ("公园", "山", "湖", "园林", "自然", "park", "nature", "garden", "mountain"),
    "family": ("乐园", "娱乐", "海洋", "亲子", "迪士尼", "theme", "entertainment", "family"),
    "citylife": ("商业", "购物", "都市", "观景", "街", "外滩", "shopping", "urban", "street"),
}


def attraction_score(attr: dict, interests: list[str]) -> int:
    # Read original Chinese names/categories regardless of display language.
    text = " ".join(str(attr.get(k, "")) for k in ("name", "category", "category_en")).lower()
    return sum(
        any(term in text for term in INTEREST_TERMS.get(interest, ()))
        for interest in interests
    )


def rank_attractions(attractions: list[dict], interests: list[str]) -> list[dict]:
    return sorted(attractions, key=lambda a: -attraction_score(a, interests))


def input_signature(city: str, selected: list[dict], start: date, days: int,
                    weather: dict | None, identity: dict, costs: dict) -> str:
    payload = {
        "planner_version": PLANNER_VERSION,
        "city": city, "selected": selected, "date": start.isoformat(),
        "days": days, "weather": weather, "identity": identity, "costs": costs,
    }
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, ensure_ascii=False, default=str,
    ).encode("utf-8")).hexdigest()


def calculate_budget(selected: list[dict], days: int, people: int,
                     rooms: int, costs: dict) -> dict:
    people, rooms = max(1, int(people)), max(1, int(rooms))
    ticket_subtotal, unknown = 0.0, []
    for attr in selected:
        price = (attr.get("passport") or {}).get("price_cny")
        if isinstance(price, (int, float)) and not isinstance(price, bool) and price >= 0:
            ticket_subtotal += price * people
        else:
            unknown.append(attr.get("id") or attr.get("name"))
    values = {
        "ticket_cost": round(ticket_subtotal, 2),
        "hotel_cost": round(max(0, costs.get("hotel_rate", 0)) * rooms
                            * max(0, int(costs.get("nights", days - 1))), 2),
        "food_cost": round(max(0, costs.get("food_rate", 0)) * people * days, 2),
        "transport_cost": round(max(0, costs.get("transport_rate", 0)) * people * days, 2),
    }
    return {"items": values, "total": round(sum(values.values()), 2),
            "unknown_ticket_ids": unknown, "cash": max(0, costs.get("cash", 0))}


def _num(value) -> float | None:
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def build_travel_plan(city_key: str, city_data: dict, selected: list[dict],
                      start: date, days: int, weather: dict | None,
                      identity: dict, costs: dict, ai_text: str = "") -> dict[str, Any]:
    """Freeze a plan snapshot; sections are the single preview/export contract."""
    lang = identity.get("language", "en")
    city = city_data["city"]
    groups, overflow = allocate_days(selected, start, days, identity.get("pace", "balanced"))
    budget = calculate_budget(selected, days, identity.get("travelers", 1),
                              identity.get("rooms", 1), costs)
    sections = []

    def section(key: str, lines: list[str]):
        sections.append({"title": pt(key, lang), "lines": [s for s in lines if s]})

    end = start + timedelta(days=days - 1)
    section("overview", [
        display_name(city, lang), f"{start.isoformat()} - {end.isoformat()}",
        f"{pt('people', lang)}: {identity.get('travelers', 1)}; "
        f"{pt('rooms', lang)}: {identity.get('rooms', 1)}",
        f"{pt('pace', lang)}: {pt(identity.get('pace', 'balanced'), lang)}",
        f"{pt('interests', lang)}: " + ", ".join(pt(i, lang) for i in identity.get("interests", [])),
        f"{pt('budget', lang)}: {identity.get('budget_cny', 0)}",
        f"{pt('special', lang)}: {identity.get('special_needs') or '-'}",
    ])
    schedule = []
    daily_plan = []
    for i, group in enumerate(groups):
        visit_date = start + timedelta(days=i)
        load = day_workload(group, visit_date)
        daily_plan.append({"date": visit_date.isoformat(),
                           "attraction_ids": [a.get("id") for a in group], **load})
        schedule.append(f"{pt('day', lang, number=i + 1)} | {visit_date.isoformat()}")
        if group:
            schedule.append(pt("day_load", lang, visit=load["visit_hours"],
                               travel=load["travel_hours"], rest=load["rest_hours"],
                               total=load["total_hours"]))
            if load["dedicated"]:
                schedule.append(pt("dedicated_day", lang))
        if not group:
            schedule.append(pt("free_day", lang))
        for attr in group:
            visit = planning_visit(attr, visit_date)
            est = visit["estimate"]
            schedule.append(
                f"{display_name(attr, lang)} | ~{visit['visit_hours']} h | "
                f"{crowd_label_for(est, lang)} | ~{est['queue_minutes']} min | "
                f"{best_window_for(est, lang)}"
            )
    schedule.append(t("planner_estimate_note", lang))
    schedule.append(pt("allocation_note", lang, hours=PACE_HOURS.get(identity.get("pace"), 10.0)))
    if overflow:
        schedule.extend([pt("capacity", lang), pt("unassigned", lang) + ": "
                         + ", ".join(display_name(a, lang) for a in overflow)])
    section("schedule", schedule)
    if ai_text.strip():
        section("ai", ai_text.strip().splitlines())

    casts = (weather or {}).get("casts") or []
    weather_lines = []
    relevant = []
    for i in range(days):
        d = (start + timedelta(days=i)).isoformat()
        cast = next((c for c in casts if c.get("date") == d), None)
        if cast:
            relevant.append(cast)
            weather_lines.append(
                f"{d}: {weather_term(cast.get('dayweather', ''), lang)} / "
                f"{weather_term(cast.get('nightweather', ''), lang)}; "
                f"{cast.get('nighttemp', '?')}~{cast.get('daytemp', '?')} C"
            )
        else:
            weather_lines.append(pt("no_forecast", lang, date=d))
    if relevant:
        weather_lines.append(f"Amap | {(weather or {}).get('reporttime', '-')}")
    weather_lines.append(pt("layers", lang))
    if any(any(w in str(c.get(k, "")) for w in ("雨", "雪"))
           for c in relevant for k in ("dayweather", "nightweather")):
        weather_lines.append(pt("rain", lang))
    if any(_num(c.get("nighttemp")) is not None and _num(c["nighttemp"]) < 10 for c in relevant):
        weather_lines.append(pt("cold", lang))
    if any(_num(c.get("daytemp")) is not None and _num(c["daytemp"]) >= 28 for c in relevant):
        weather_lines.append(pt("hot", lang))
    section("weather", weather_lines)

    budget_lines = [f"{pt(k, lang)}: CNY {v:.2f}" for k, v in budget["items"].items()]
    budget_lines.extend([
        f"{pt('hotel_rate', lang)}: {costs.get('hotel_rate', 0)}; "
        f"{pt('nights', lang)}: {costs.get('nights', max(0, days - 1))}",
        f"{pt('food_rate', lang)}: {costs.get('food_rate', 0)}; "
        f"{pt('transport_rate', lang)}: {costs.get('transport_rate', 0)}",
    ])
    budget_lines.append(f"{pt('total', lang)}: CNY {budget['total']:.2f}")
    budget_lines.append(pt("budget_note", lang))
    if budget["unknown_ticket_ids"]:
        names = [display_name(a, lang) for a in selected
                 if (a.get("id") or a.get("name")) in budget["unknown_ticket_ids"]]
        budget_lines.append(pt("unknown_ticket", lang, names=", ".join(names)))
    if 0 < identity.get("budget_cny", 0) < budget["total"]:
        budget_lines.append(pt("over_budget", lang))
    budget_lines.append(pt("cash_note", lang, amount=budget["cash"]))
    section("budget_title", budget_lines)

    transport = city.get("transport") or {}
    section("stay_transport", [
        f"{pt('stay', lang)}: {identity.get('accommodation') or '-'}",
        pt("hotel_note", lang), pt("route_note", lang),
        *[str(transport.get(k, "")) for k in ("airport", "airport_to_city", "city_transport")],
        "Hotel comparison: https://www.trip.com/ | https://www.booking.com/",
        "Amap: https://www.amap.com/",
    ])
    essentials = city.get("essentials") or {}
    section("preparation", [pt("packing", lang), pt("booking_note", lang),
                            *[f"{t(label, lang)}: {essentials[key]}"
                              for key, label in (("sim_data", "card_sim"), ("payment", "card_payment"),
                                                 ("police_registration", "card_registration"))
                              if essentials.get(key)]])
    section("entry_tax", [pt("entry_note", lang), "https://www.nia.gov.cn/",
                          "https://www.mfa.gov.cn/", pt("tax_note", lang),
                          "https://www.chinatax.gov.cn/", "https://www.customs.gov.cn/"])

    details, sources = [], []
    for attr in selected:
        p, entry = attr.get("passport") or {}, attr.get("entry") or {}
        details.extend([
            display_name(attr, lang), str(attr.get("description", "")),
            status_label(attr.get("status", ""), lang),
            t("guide_platform_fmt", lang, platform=p.get("platform", "unknown")),
            t("guide_advance_fmt", lang, days=p.get("advance_booking_days", "unknown")),
            t("guide_price_notes_fmt", lang, notes=p.get("price_notes", "unknown")),
            t("guide_hours_fmt", lang, hours=entry.get("hours", "unknown")),
            t("guide_address_fmt", lang, addr=entry.get("location", "unknown")),
            t("guide_metro_fmt", lang, metro=entry.get("nearest_metro", "unknown")),
            t("guide_entry_fmt", lang, entry=entry.get("entry_method", "unknown")),
            *[f"{t('guide_alternatives', lang)}: {alt.get('name', '')} - {alt.get('reason', '')}"
              for alt in attr.get("alternatives", []) if isinstance(alt, dict)],
            *[str(tip) for tip in entry.get("tips", [])],
        ])
        sources.append(display_name(attr, lang) + " | " + str(attr.get("updated_at", "unknown")))
        sources.extend(str(s) for s in attr.get("sources", []))
    section("attractions", details)
    section("sources", list(dict.fromkeys(sources)))
    section("disclaimer", [t("footer_disclaimer_body", lang), pt("privacy", lang)])
    return {
        "schema_version": 2, "planner_version": PLANNER_VERSION,
        "language": lang, "city_key": city_key, "daily_plan": daily_plan,
        "title": f"{display_name(city, lang)} | {pt('result', lang)}",
        "date": start.isoformat(), "days": days, "sections": sections,
        "identity": copy.deepcopy(identity), "budget": budget,
        "unscheduled_ids": [a.get("id") for a in overflow],
        "signature": input_signature(city_key, selected, start, days, weather, identity, costs),
        "ai_text": ai_text,
    }
