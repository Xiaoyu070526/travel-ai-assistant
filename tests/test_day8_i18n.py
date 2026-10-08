"""Day 8-9：多语言模块（i18n）单元测试。

覆盖：
1. ``t()`` 取词：zh/en 全量、fr/ja/ko 回退英文、缺失 key 原样返回；
2. ``output_language()`` 语言映射（zh -> 中文，其余 -> 对应语言名）；
3. ``normalize_lang()`` 未知语言回退 en；
4. ``faq_answer()`` 中英分支；
5. prompt 模板已注入 ``{output_language}`` 占位符；
6. FAQ 知识库英文快捷问题能唯一命中对应条目。
"""

from pathlib import Path

from src.utils import i18n
from src.utils.i18n import faq_answer, normalize_lang, output_language, t
from src.utils.faq_kb import match_faq, quick_questions

ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- #
# t() 取词
# --------------------------------------------------------------------------- #

def test_t_zh_and_en_full():
    assert t("app_title", "zh") == "🧳 AI入境旅游搭子"
    assert t("app_title", "en") == "🧳 AI China Travel Buddy"


def test_t_fallback_to_en_for_fr_ko():
    # fr/ko 未单独维护 UI 文案，必须回退英文，不能抛 KeyError
    for lang in ("fr", "ko"):
        assert t("app_title", lang).startswith("🧳 AI China")


def test_t_ja_has_own_text():
    # ja 已提供真实日文词条，不再回退英文
    assert t("app_title", "ja").startswith("🧳 AI中国")


def test_t_format_kwargs():
    text = t("card_advance_days_fmt", "en", days=3)
    assert text == "3 days"


def test_t_missing_key_returns_key():
    assert t("no_such_key_xyz", "en") == "no_such_key_xyz"


def test_t_missing_lang_falls_back_en():
    # 默认 lang 是 en（演示场景：美国游客不会中文）
    assert t("app_title") == "🧳 AI China Travel Buddy"


# --------------------------------------------------------------------------- #
# 语言规范化 / 输出语言
# --------------------------------------------------------------------------- #

def test_normalize_lang_unknown_falls_back_en():
    assert normalize_lang("xx") == "en"
    assert normalize_lang(None) == "en"
    assert normalize_lang("ja") == "ja"


def test_output_language_zh_is_chinese():
    assert output_language("zh") == "中文"


def test_output_language_others_are_named():
    assert "English" in output_language("en")
    assert "French" in output_language("fr")
    assert "Japanese" in output_language("ja")
    assert "Korean" in output_language("ko")


# --------------------------------------------------------------------------- #
# FAQ 答案语言分支
# --------------------------------------------------------------------------- #

def test_faq_answer_zh_empty_en_filled():
    assert faq_answer("hotel_refuse", "zh") == ""
    en = faq_answer("hotel_refuse", "en")
    assert en and "passport" in en.lower()


def test_faq_answer_missing_id_returns_empty():
    assert faq_answer("no_such_id", "en") == ""


# --------------------------------------------------------------------------- #
# prompt 模板中 output_language 占位符
# --------------------------------------------------------------------------- #

def test_prompt_templates_have_output_language_placeholder():
    from src.prompts import templates

    for name in [
        "CITY_RECOMMENDATION_PROMPT",
        "GUIDE_GENERATION_PROMPT",
        "FALLBACK_PROMPT",
        "ARRIVAL_CHECKLIST_PROMPT",
    ]:
        template = getattr(templates, name)
        assert "{output_language}" in template, f"{name} 缺少 {{output_language}}"


# --------------------------------------------------------------------------- #
# 英文快捷问题知识库命中（Day 8 核心：不会中文的游客点按钮也能获得答案）
# --------------------------------------------------------------------------- #

def test_english_quick_questions_hit_unique_faq():
    en_qs = quick_questions(lang="en")
    assert len(en_qs) == 6
    for q in en_qs:
        hit = match_faq(q)
        assert hit is not None, f"英文问题未命中知识库: {q}"


def test_english_quick_questions_no_ambiguity():
    """每个英文快捷问题应命中不同 FAQ 条目（防止歧义误命中）。"""
    en_qs = quick_questions(lang="en")
    hit_ids = {match_faq(q)["id"] for q in en_qs}
    assert len(hit_ids) == len(en_qs), f"英文问题存在歧义命中: {hit_ids}"


def test_ui_text_keys_referenced_in_cards_exist():
    """cards.py / app.py 引用的 i18n 词条必须存在，防止运行时静默返回 key 本身。"""
    required = [
        "card_city_hdr", "card_highlights", "card_transport", "card_airport",
        "card_airport_to_city", "card_city_transport", "card_tips_fmt",
        "card_notes", "card_apps", "card_required", "card_optional",
        "card_essentials_title", "card_essentials_expander", "card_quick_questions",
        "card_sim", "card_payment", "card_hotel", "card_ride",
        "card_registration", "card_public_transport",
        "guide_section_booking", "guide_section_transport",
        "guide_section_alternatives", "guide_section_emergency",
        "guide_source_official", "guide_eta_fmt", "guide_no_alternatives",
        "card_guide_fallback_title", "card_guide_fallback_msg", "card_destination",
        "guide_basis", "guide_action", "guide_online", "guide_passport_ok",
        "guide_cn_phone", "guide_ticket_price", "guide_platform_fmt",
        "guide_advance_fmt", "guide_price_notes_fmt", "guide_address_fmt",
        "guide_metro_fmt", "guide_hours_fmt", "guide_entry_fmt",
        "footer_disclaimer_title", "footer_disclaimer_body",
        "footer_source_note", "footer_privacy",
    ]
    for key in required:
        assert key in i18n.UI_TEXT, f"缺少 i18n 词条: {key}"
        assert i18n.UI_TEXT[key].get("en"), f"词条缺少英文: {key}"

