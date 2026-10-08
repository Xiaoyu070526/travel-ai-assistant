"""Offline checks for allocation, pricing assumptions and snapshot invalidation."""

from datetime import date
from unittest import mock

import pytest

from src.utils.content_loader import load_city_data
from src.utils.plan_i18n import TEXT, pt
from src.utils.travel_plan import (
    allocate_days, build_travel_plan, calculate_budget, input_signature,
    rank_attractions,
)


def fixture_plan(lang="zh", ai_text=""):
    data = load_city_data("beijing", lang=lang)
    identity = {"language": lang, "nationality": "France", "travelers": 2,
                "rooms": 1, "pace": "balanced", "budget_cny": 1000,
                "interests": ["culture"], "special_needs": "", "accommodation": ""}
    costs = {"hotel_rate": 300, "food_rate": 100, "transport_rate": 40,
             "nights": 2, "cash": 300}
    plan = build_travel_plan("beijing", data, data["attractions"][:3],
                             date(2026, 10, 16), 3, None, identity, costs, ai_text)
    return plan, data, identity, costs


def test_daily_allocation_uses_each_actual_date_and_explicit_overflow():
    selected = [{"id": str(i)} for i in range(5)]
    visited_dates = []

    def estimate(attr, day):
        visited_dates.append(day)
        return {"duration_hours": 3.0}

    with mock.patch("src.utils.itinerary.estimate_visit", side_effect=estimate):
        groups, overflow = allocate_days(selected, date(2026, 10, 16), 2, max_hours=9.0)
    assert list(map(len, groups)) == [2, 2]
    assert len(overflow) == 1
    assert date(2026, 10, 17) in visited_dates
    assert {a["id"] for group in groups for a in group} | {a["id"] for a in overflow} == {a["id"] for a in selected}


def test_oversized_stop_does_not_block_smaller_stops():
    def estimate(attr, day):
        return {"duration_hours": 10 if attr["id"] == "large" else 2}
    with mock.patch("src.utils.itinerary.estimate_visit", side_effect=estimate):
        groups, overflow = allocate_days([{"id": "large"}, {"id": "small"}],
                                         date(2026, 10, 16), 1)
    assert groups == [[{"id": "small"}]]
    assert overflow == [{"id": "large"}]


def test_allocate_empty_days_and_invalid_days():
    assert allocate_days([], date(2026, 10, 16), 3) == ([[], [], []], [])
    with pytest.raises(ValueError):
        allocate_days([], date.today(), 0)


def test_budget_group_rooms_nights_unknown_tickets_and_cash_not_double_counted():
    selected = [{"id": "paid", "passport": {"price_cny": 60}},
                {"id": "unknown", "passport": {}},
                {"id": "free", "passport": {"price_cny": 0}}]
    budget = calculate_budget(selected, 3, 2, 1,
                              {"hotel_rate": 300, "food_rate": 100,
                               "transport_rate": 40, "nights": 2, "cash": 300})
    assert budget["items"] == {"ticket_cost": 120, "hotel_cost": 600,
                               "food_cost": 600, "transport_cost": 240}
    assert budget["total"] == 1560
    assert budget["unknown_ticket_ids"] == ["unknown"]
    assert budget["cash"] == 300


def test_signature_changes_with_city_preferences_costs_weather_and_order():
    args = ["beijing", [{"id": "a"}, {"id": "b"}], date(2026, 10, 16),
            3, None, {"language": "zh"}, {"cash": 300}]
    original = input_signature(*args)
    for index, replacement in ((0, "shanghai"), (1, list(reversed(args[1]))),
                                (4, {"casts": []}), (5, {"language": "ja"}),
                                (6, {"cash": 500})):
        changed = args.copy()
        changed[index] = replacement
        assert input_signature(*changed) != original


@pytest.mark.parametrize("lang", ["zh", "en", "ja", "fr", "ko"])
def test_plan_contains_shared_sections_and_copies_preferences(lang):
    plan, data, identity, costs = fixture_plan(lang)
    titles = {section["title"] for section in plan["sections"]}
    for key in ("schedule", "budget_title", "entry_tax", "preparation", "sources", "disclaimer"):
        assert pt(key, lang) in titles
    assert plan["signature"] == input_signature("beijing", data["attractions"][:3],
                                                date(2026, 10, 16), 3, None, identity, costs)
    identity["interests"].append("nature")
    assert plan["identity"]["interests"] == ["culture"]


def test_missing_weather_not_replaced_by_invented_forecast():
    plan, _, _, _ = fixture_plan()
    weather = next(s for s in plan["sections"] if s["title"] == pt("weather", "zh"))
    assert len([line for line in weather["lines"] if "暂无" in line]) == 3


def test_ai_text_kept_verbatim_and_not_required_for_basic_export():
    plan, _, _, _ = fixture_plan(ai_text="## Day 1\n08:30-11:30 <test> & safety")
    assert plan["ai_text"] == "## Day 1\n08:30-11:30 <test> & safety"
    assert next(s for s in plan["sections"] if s["title"] == pt("ai", "zh"))["lines"][-1].endswith("& safety")


def test_interest_ranking_and_all_labels_have_three_languages():
    ranked = rank_attractions([{"name": "商业街"}, {"name": "历史博物馆"}], ["culture"])
    assert ranked[0]["name"] == "历史博物馆"
    assert all(len(values) == 3 and all(values) for values in TEXT.values())
