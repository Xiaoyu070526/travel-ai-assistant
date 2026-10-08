"""PDF tests use fitz only when available; runtime needs ReportLab alone."""

from datetime import date
from unittest import mock

import pytest

from src.utils.content_loader import load_city_data
from src.utils.pdf_export import _clean, export_plan_pdf
from src.utils.travel_plan import build_travel_plan


@pytest.mark.parametrize("lang", ["zh", "en", "ja", "fr", "ko"])
def test_pdf_valid_bytes_multilingual_and_safe_markup(lang):
    data = load_city_data("beijing", lang)
    plan = build_travel_plan("beijing", data, data["attractions"][:3],
                             date(2026, 10, 16), 3, None, {"language": lang}, {},
                             "## Example\nLiteral <tag> & text\n한국 여행 北京 あいう\n" + "Long line " * 250)
    result = export_plan_pdf(plan)
    assert result.startswith(b"%PDF-")
    assert len(result) > 10000
    fitz = pytest.importorskip("fitz")
    with fitz.open(stream=result, filetype="pdf") as document:
        assert len(document) >= 2
        text = "\n".join(page.get_text() for page in document)
        assert "2026-10-16" in text
        assert "Literal <tag> & text" in text
        assert "Reference only" in text
        assert "한국" in text
        assert "北京" in text


def test_pdf_export_has_no_network_calls():
    data = load_city_data("shanghai", "zh")
    plan = build_travel_plan("shanghai", data, data["attractions"][:1],
                             date(2026, 10, 16), 1, None, {"language": "zh"}, {})
    with mock.patch("requests.get", side_effect=AssertionError("network forbidden")), \
            mock.patch("requests.post", side_effect=AssertionError("network forbidden")):
        assert export_plan_pdf(plan).startswith(b"%PDF-")


def test_pdf_clean_removes_emoji_but_keeps_multilingual_content():
    assert _clean("## 🧳 北京 **旅行** — あいう 한국 é") == "北京 旅行 - あいう 한국 é"
