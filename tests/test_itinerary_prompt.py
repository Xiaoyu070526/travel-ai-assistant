"""AI input must use the same balanced allocation as the saved plan."""

from datetime import date
from unittest import mock

from src import app
from src.utils.content_loader import load_city_data


def test_beijing_prompt_matches_saved_days_and_queue_inclusion():
    data = load_city_data("beijing", "en")
    identity = {"language": "en", "pace": "balanced", "has_chinese_phone": False}
    st = mock.MagicMock()
    st.session_state.selected_city = "beijing"
    with mock.patch.object(app, "st", st), \
            mock.patch.object(app, "_deepseek_text", return_value="New itinerary") as generate:
        result = app._generate_trip_plan(data, data["attractions"][:3],
                                         date(2026, 10, 10), 3, None, identity, "en")
    assert result == "New itinerary"
    prompt = generate.call_args.args[0]
    day1 = prompt.split("[Day 1")[1].split("[Day 2")[0]
    day2 = prompt.split("[Day 2")[1].split("[Day 3")[0]
    day3 = prompt.split("[Day 3")[1].split("Requirements:")[0]
    assert "Forbidden City" in day1 and "Great Wall" not in day1
    assert "Temple of Heaven" in day2
    assert "Great Wall" in day3 and "dedicated excursion day: True" in day3
    assert "duration INCLUDING queue" in prompt
    assert "do not invent weather" in prompt
    assert "Do not add queue a second time" in prompt
    assert "Manual required" in day1


def test_infeasible_days_do_not_call_ai_or_force_closed_sights():
    data = load_city_data("beijing", "en")
    st = mock.MagicMock()
    with mock.patch.object(app, "st", st), mock.patch.object(app, "_deepseek_text") as generate:
        result = app._generate_trip_plan(data, [data["attractions"][0]],
                                         date(2026, 10, 12), 1, None,
                                         {"language": "en"}, "en")
    assert result is None
    generate.assert_not_called()
    st.warning.assert_called_once()
