"""Run real Streamlit pages offline; no external requests or credentials needed."""

from datetime import date, timedelta
from unittest import mock

from streamlit.testing.v1 import AppTest

from src.utils.plan_i18n import pt
from src.utils.i18n import t


def test_save_download_rerun_stale_inputs_and_city_weather_reset():
    app = AppTest.from_file("src/app.py", default_timeout=20)
    with mock.patch("requests.get", side_effect=AssertionError("no network")), \
            mock.patch("requests.post", side_effect=AssertionError("no network")):
        app.run()
        assert not app.exception
        app.session_state["identity"] = {
            "language": "zh", "nationality": "France", "trip_days": 3,
            "arrival_date": (date.today() + timedelta(days=7)).isoformat(),
            "interests": ["culture"], "pace": "balanced", "travelers": 2,
            "rooms": 1, "budget_cny": 3000,
        }
        app.session_state["selected_city"] = "beijing"
        app.session_state["page"] = "planner"
        app.run()
        assert not app.exception
        next(button for button in app.button if button.label == pt("base", "zh")).click().run()
        assert not app.exception
        assert app.session_state["plan_pdf"].startswith(b"%PDF-")
        saved = app.session_state["travel_plan"]["signature"]
        assert len(app.get("download_button")) == 1
        app.run()
        assert app.session_state["travel_plan"]["signature"] == saved
        assert len(app.get("download_button")) == 1
        app.slider(key="planner_days_input").set_value(4).run()
        assert not app.exception
        assert any(w.value == pt("stale", "zh") for w in app.warning)
        assert len(app.get("download_button")) == 0

        app.session_state["page"] = "city"
        app.session_state["planner_weather_city"] = "beijing"
        app.session_state["planner_weather"] = {"city": "北京", "casts": []}
        app.run()
        next(s for s in app.selectbox if "城市" in s.label).set_value("shanghai").run()
        assert not app.exception
        assert app.session_state["selected_city"] == "shanghai"
        assert app.session_state["planner_weather"] is None


def test_identity_validation_and_new_preferences():
    app = AppTest.from_file("src/app.py", default_timeout=20).run()
    app.text_input[0].set_value("France")
    app.text_input[1].set_value("invalid-date")
    next(button for button in app.button if button.label == t("identity_submit", "en")).click().run()
    assert not app.exception
    assert app.session_state["identity"] == {}
    assert any(w.value == pt("date_error", "en") for w in app.warning)
    app.text_input[1].set_value((date.today() + timedelta(days=7)).isoformat())
    next(button for button in app.button if button.label == t("identity_submit", "en")).click().run()
    assert not app.exception
    assert app.session_state["identity"]["travelers"] == 1
    assert app.session_state["identity"]["pace"] == "balanced"
    assert app.session_state["page"] == "city"


def test_ai_plan_saved_once_and_download_does_not_regenerate():
    app = AppTest.from_file("src/app.py", default_timeout=20).run()
    app.session_state["identity"] = {"language": "en", "trip_days": 3, "pace": "balanced"}
    app.session_state["selected_city"] = "beijing"
    app.session_state["page"] = "planner"
    app.run()
    with mock.patch("src.api.llm_client.LLMClient.complete", return_value="## Day 1\n09:00 Museum visit") as complete:
        next(b for b in app.button if b.label == t("planner_gen_btn", "en")).click().run()
        assert not app.exception
        assert app.session_state["travel_plan"]["ai_text"] == "## Day 1\n09:00 Museum visit"
        assert app.session_state["plan_pdf"].startswith(b"%PDF-")
        app.run()
        assert complete.call_count == 1
        assert len(app.get("download_button")) == 1


def test_weather_failure_still_allows_basic_pdf():
    app = AppTest.from_file("src/app.py", default_timeout=20).run()
    app.session_state["identity"] = {"language": "zh", "trip_days": 3}
    app.session_state["selected_city"] = "shanghai"
    app.session_state["page"] = "planner"
    app.run()
    with mock.patch("src.api.amap._amap_key", side_effect=RuntimeError("missing key")):
        next(b for b in app.button if b.label == t("planner_weather_btn", "zh")).click().run()
    assert not app.exception
    next(b for b in app.button if b.label == pt("base", "zh")).click().run()
    assert not app.exception
    assert app.session_state["plan_pdf"].startswith(b"%PDF-")
