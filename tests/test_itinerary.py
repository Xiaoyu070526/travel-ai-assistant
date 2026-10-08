"""Calendar, buffers, balanced days, and the reported Beijing regression."""

from datetime import date, timedelta
from unittest import mock

import pytest

from src.utils.content_loader import load_city_data
from src.utils.itinerary import (
    PACE_HOURS, allocate_days, closed_weekdays, day_workload, planning_visit,
)
from src.utils.travel_plan import build_travel_plan


@pytest.mark.parametrize("lang", ["zh", "en", "ja", "fr", "ko"])
def test_reported_beijing_three_days_great_wall_alone_and_closed_monday_avoided(lang):
    data = load_city_data("beijing", lang)
    groups, remaining = allocate_days(data["attractions"][:3], date(2026, 10, 10), 3)
    assert not remaining
    assert [[a["id"] for a in group] for group in groups] == [["gugong"], ["tiantan"], ["badaling"]]
    assert all(day_workload(g, date(2026, 10, 10) + timedelta(days=i))["total_hours"]
               <= PACE_HOURS["balanced"] for i, g in enumerate(groups))


def test_closed_every_available_day_stays_unassigned_not_forced():
    attraction = load_city_data("beijing")["attractions"][0]
    groups, remaining = allocate_days([attraction], date(2026, 10, 12), 1)
    assert groups == [[]]
    assert remaining == [attraction]


def test_scarce_opening_day_reserved_for_restricted_attraction():
    # Only Monday works for restricted; the flexible stop must use Tuesday.
    selected = [
        {"id": "flexible"},
        {"id": "restricted", "planning": {"closed_weekdays": [1, 2, 3, 4, 5, 6]}},
    ]
    groups, remaining = allocate_days(selected, date(2026, 10, 12), 2)
    assert not remaining
    assert groups == [[selected[1]], [selected[0]]]


@pytest.mark.parametrize("city,dedicated", [("beijing", "badaling"), ("shanghai", "disney"), ("xian", "bingmayong")])
def test_excursion_or_theme_park_never_combined_with_other_stops(city, dedicated):
    selected = load_city_data(city)["attractions"]
    groups, remaining = allocate_days(selected, date(2026, 10, 13), 5, pace="busy")
    assert not remaining
    assert all(len(g) == 1 for g in groups if any(a["id"] == dedicated for a in g))


def test_two_days_nearby_gardens_grouped_remote_separate():
    selected = [a for a in load_city_data("beijing")["attractions"]
                if a["id"] in ("badaling", "yiheyuan", "yuanmingyuan")]
    groups, remaining = allocate_days(selected, date(2026, 10, 13), 2)
    assert not remaining
    ids = [{a["id"] for a in g} for g in groups]
    assert {"badaling"} in ids
    assert {"yiheyuan", "yuanmingyuan"} in ids


def test_quiet_day_queue_included_once_and_busy_queue_not_added_twice():
    for crowd, original in ((3, 2.0), (4, 2.5)):
        with mock.patch("src.utils.itinerary.estimate_visit", return_value={
            "duration_hours": original, "queue_minutes": 30, "crowd_index": crowd,
        }):
            assert planning_visit({"id": "unknown"}, date(2026, 10, 13))["visit_hours"] == 2.5


@pytest.mark.parametrize("hours", ["周一闭馆", "closed Mondays", "Closed on Monday", "月曜休館"])
def test_closure_text_different_languages(hours):
    assert closed_weekdays({"entry": {"hours": hours}}) == {0}


def test_unknown_calendar_not_invented_and_partial_park_closure_conservative():
    assert closed_weekdays({}) == set()
    tiantan = next(a for a in load_city_data("beijing")["attractions"] if a["id"] == "tiantan")
    assert closed_weekdays(tiantan) == {0}


def test_budget_cap_counts_buffers_and_no_dropping_or_duplicate_stops():
    selected = [{"id": str(i)} for i in range(5)]
    groups, remaining = allocate_days(selected, date(2026, 10, 13), 2, max_hours=7)
    placed = [a for group in groups for a in group]
    assert sorted(a["id"] for a in placed + remaining) == [str(i) for i in range(5)]
    assert all(day_workload(group, date(2026, 10, 13) + timedelta(days=i))["total_hours"] <= 7
               for i, group in enumerate(groups))


def test_plan_snapshot_same_allocation_and_visible_workload_note():
    data = load_city_data("beijing", "en")
    plan = build_travel_plan("beijing", data, data["attractions"][:3],
                             date(2026, 10, 10), 3, None,
                             {"language": "en", "pace": "balanced"}, {})
    assert [d["attraction_ids"] for d in plan["daily_plan"]] == [["gugong"], ["tiantan"], ["badaling"]]
    schedule = "\n".join(plan["sections"][1]["lines"])
    assert "travel allowance" in schedule
    assert "not live routes" in schedule
    assert "Dedicated excursion" in schedule


def test_large_selection_returns_explicit_extra_stops_and_is_deterministic():
    selected = [{"id": str(i)} for i in range(9)]
    result = allocate_days(selected, date(2026, 10, 13), 3)
    assert selected[-1] in result[1]
    assert result == allocate_days(selected, date(2026, 10, 13), 3)
