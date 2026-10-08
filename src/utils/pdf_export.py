"""In-memory A4 travel-plan PDF with safe text rendering and multilingual fonts."""

from __future__ import annotations

import os
import re
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def _clean(text: str) -> str:
    text = str(text)
    text = re.sub(r"[\U0001F000-\U0001FFFF\u2600-\u27BF\uFE0F\u200D]", "", text)
    text = re.sub(r"[\u2010-\u2015\u2212]", "-", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    text = re.sub(r"^\s*#{1,6}\s*", "", text)
    return text.replace("**", "").replace("`", "").strip()


@lru_cache(maxsize=5)
def _font(lang: str) -> str:
    """Prefer embedded TrueType; portable CJK CID fallback when unavailable."""
    configured = os.getenv("TRAVEL_PDF_FONT_PATH")
    candidates = [configured] if configured else []
    windows = Path(os.getenv("WINDIR", "C:/Windows")) / "Fonts"
    if lang == "ko":
        candidates.append(str(windows / "malgun.ttf"))
    elif lang == "ja":
        candidates.append(str(windows / "msgothic.ttc"))
    if lang in ("en", "fr", "zh", "ja"):
        candidates.extend([
            str(windows / "NotoSansSC-Regular.ttf"), str(windows / "simhei.ttf"),
            "/usr/share/fonts/truetype/noto/NotoSansSC-Regular.ttf",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        ])
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            name = "TravelFont-" + lang
            try:
                pdfmetrics.registerFont(TTFont(name, candidate))
                return name
            except Exception:
                if configured and candidate == configured:
                    raise ValueError("TRAVEL_PDF_FONT_PATH is not a supported TrueType font")
    if configured:
        raise ValueError("TRAVEL_PDF_FONT_PATH does not exist")
    name = {"ja": "HeiseiKakuGo-W5", "ko": "HYSMyeongJo-Medium"}.get(lang, "STSong-Light")
    pdfmetrics.registerFont(UnicodeCIDFont(name))
    return name


def _markup(text: str, primary: str) -> str:
    """Escape all input and select fallback fonts for unsupported glyphs.

    Korean TrueType fonts often lack Chinese place-name glyphs; conversely,
    Chinese fonts often lack Hangul entered in traveler preferences.
    """
    text = _clean(text)
    runs = []
    current_font, current_text = primary, ""

    def supported(font_name, char):
        face = pdfmetrics.getFont(font_name).face
        mapping = getattr(face, "charToGlyph", None)
        if mapping is not None:
            return ord(char) in mapping
        # Portable CJK CID fonts have no cmap, but their script is known.
        if "\uac00" <= char <= "\ud7af" or "\u1100" <= char <= "\u11ff":
            return font_name == "HYSMyeongJo-Medium"
        return True

    for char in text:
        chosen = primary
        if not supported(primary, char):
            hangul = "\uac00" <= char <= "\ud7af" or "\u1100" <= char <= "\u11ff"
            candidate = _font("ko" if hangul else "zh")
            if supported(candidate, char):
                chosen = candidate
        if chosen != current_font and current_text:
            runs.append((current_font, current_text))
            current_text = ""
        current_font = chosen
        current_text += char
    if current_text:
        runs.append((current_font, current_text))
    return "".join(f'<font name="{name}">{escape(value)}</font>' for name, value in runs)


def export_plan_pdf(plan: dict) -> bytes:
    """Use only saved snapshot sections, never regenerate content during export."""
    font = _font(plan.get("language", "en"))
    buffer = BytesIO()
    body = ParagraphStyle("TravelBody", fontName=font, fontSize=10, leading=16,
                          textColor=colors.HexColor("#263449"), wordWrap="CJK",
                          spaceAfter=6, alignment=TA_LEFT)
    heading = ParagraphStyle("TravelHeading", parent=body, fontSize=14, leading=21,
                             spaceBefore=15, spaceAfter=8, keepWithNext=True,
                             textColor=colors.HexColor("#156575"))
    title = ParagraphStyle("TravelTitle", parent=heading, fontSize=20, leading=29,
                           spaceBefore=0, spaceAfter=14)

    def para(text, style=body):
        return Paragraph(_markup(text, font), style)

    story = [para(plan["title"], title),
             para(f"{plan['date']} | {plan['days']} days | AI China Travel Buddy"), Spacer(1, 10)]
    for section in plan["sections"]:
        lines = [line for line in section["lines"] if _clean(line)]
        if not lines:
            continue
        story.append(para(section["title"], heading))
        # One paragraph per line allows tables/long AI text to paginate safely.
        story.extend(para(line) for line in lines)

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#CCDDE1"))
        canvas.line(42, 37, A4[0] - 42, 37)
        canvas.setFont(font, 8)
        canvas.setFillColor(colors.HexColor("#687887"))
        canvas.drawString(42, 24, "AI China Travel Buddy | Reference only")
        canvas.drawRightString(A4[0] - 42, 24, str(document.page))
        canvas.restoreState()

    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=42, leftMargin=42,
                           topMargin=42, bottomMargin=54,
                           title=_clean(plan["title"]), author="AI China Travel Buddy")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
