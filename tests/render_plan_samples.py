"""Manual QA helper: produce multilingual samples from the actual exporter."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.content_loader import load_city_data
from src.utils.pdf_export import export_plan_pdf
from src.utils.travel_plan import build_travel_plan


def main():
    for lang in ("zh", "en", "ja", "fr", "ko"):
        output = Path("output/pdf") if lang == "zh" else Path("tmp/pdfs")
        output.mkdir(parents=True, exist_ok=True)
        city_data = load_city_data("beijing", lang)
        plan = build_travel_plan(
            "beijing", city_data, city_data["attractions"], date(2026, 10, 16),
            3, {"reporttime": "2026-10-15 12:00", "casts": [
                {"date": "2026-10-16", "dayweather": "小雨", "nightweather": "多云",
                 "daytemp": "18", "nighttemp": "8"},
            ]}, {"language": lang, "travelers": 2, "rooms": 1, "pace": "balanced",
                 "budget_cny": 2000, "interests": ["culture"]},
            {"hotel_rate": 300, "food_rate": 100, "transport_rate": 40,
             "nights": 2, "cash": 300},
            ai_text="한국 여행 | 北京 | あいう" if lang == "ko" else "",
        )
        path = output / f"travel-plan-preview-{lang}.pdf"
        path.write_bytes(export_plan_pdf(plan))
        print(path.resolve())


if __name__ == "__main__":
    main()
