"""Produce a basic PDF for the user's October 10-12 Beijing regression."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.content_loader import load_city_data
from src.utils.pdf_export import export_plan_pdf
from src.utils.travel_plan import build_travel_plan


def main():
    data = load_city_data("beijing", "zh")
    plan = build_travel_plan(
        "beijing", data, data["attractions"][:3], date(2026, 10, 10), 3, None,
        {"language": "zh", "travelers": 1, "rooms": 1, "pace": "balanced",
         "budget_cny": 5000, "interests": ["culture"]},
        {"hotel_rate": 300, "food_rate": 100, "transport_rate": 40, "nights": 2, "cash": 300},
    )
    expected = [["gugong"], ["tiantan"], ["badaling"]]
    assert [day["attraction_ids"] for day in plan["daily_plan"]] == expected
    output = Path("output/pdf/travel-plan-beijing-balanced-2026-10-10.pdf")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(export_plan_pdf(plan))
    print(output.resolve())


if __name__ == "__main__":
    main()
