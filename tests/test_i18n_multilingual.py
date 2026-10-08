"""多语言（zh/en/ja）整改的单元测试（Day 9 多语言）。

覆盖：
1. load_city_data / load_attraction 的三语言切换；
2. display_name / status_label / weather_term 展示层；
3. i18n 日文词条完整性；
4. FAQ / passport / crowd 三语言；
5. Day 8 Checklist 与 Day 9 trip planner 模板不回归。

所有测试不调用真实 DeepSeek / 高德 API。
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.content_loader import (  # noqa: E402
    display_name,
    load_attraction,
    load_city_data,
)
from src.utils.crowd import (  # noqa: E402
    best_window_for,
    crowd_label_for,
    date_tag_for,
    estimate_visit,
)
from src.utils.faq_kb import match_faq, question_label, quick_questions  # noqa: E402
from src.utils.i18n import (  # noqa: E402
    UI_TEXT,
    UI_TEXT_JA,
    faq_answer,
    output_language,
    status_label,
    t,
    weather_term,
)
from src.utils.passport_check import check_passport_bookability  # noqa: E402


# --------------------------------------------------------------------------- #
# 1. 数据层三语言
# --------------------------------------------------------------------------- #

def test_load_city_data_default_is_zh():
    d = load_city_data("beijing")
    assert d["city"]["name"] == "北京"
    assert "中国" in d["city"]["description"]


def test_load_city_data_en_switches_fields():
    d = load_city_data("beijing", lang="en")
    assert "Capital of China" in d["city"]["description"]
    assert "Both Alipay and WeChat" in d["city"]["essentials"]["payment"]
    assert "Capital International Airport" in d["city"]["transport"]["airport"]


def test_load_city_data_ja_switches_fields():
    d = load_city_data("beijing", lang="ja")
    assert "中国の首都" in d["city"]["description"]
    assert "Alipay / WeChat" in d["city"]["essentials"]["payment"]


def test_load_attraction_en_switches_fields():
    a = load_attraction("beijing", "gugong", lang="en")
    assert a["category"] == "Palace / Museum"
    assert "Imperial palace" in a["description"]
    assert "Meridian Gate" in a["entry"]["entry_method"]
    assert "Forbidden City official" in a["passport"]["platform"]


def test_load_attraction_ja_switches_fields():
    a = load_attraction("beijing", "gugong", lang="ja")
    assert a["category"] == "宮殿/博物館"
    assert "明清時代" in a["description"]
    assert "午門" in a["entry"]["entry_method"]


def test_load_attraction_factual_fields_preserved():
    # 事实数据（布尔/数值/URL）不因语言切换被篡改
    en = load_attraction("shanghai", "disney", lang="en")
    zh = load_attraction("shanghai", "disney", lang="zh")
    assert en["passport"]["price_cny"] == zh["passport"]["price_cny"] == 475
    assert en["passport"]["bookable_online"] is True
    assert en["sources"] == zh["sources"]


def test_display_name():
    d = load_city_data("beijing", lang="zh")
    a = d["attractions"][0]
    assert display_name(a, "zh") == "故宫 (Forbidden City)"
    assert display_name(a, "en") == "Forbidden City (故宫)"
    assert display_name(a, "ja") == "故宮 (Forbidden City)"


# --------------------------------------------------------------------------- #
# 2. 展示层辅助
# --------------------------------------------------------------------------- #

def test_status_label_three_languages():
    assert status_label("✅ 可订", "zh") == "✅ 可订"
    assert status_label("✅ 可订", "en") == "✅ Bookable online"
    assert status_label("✅ 可订", "ja") == "✅ 予約可"
    assert status_label("⚠️ 需人工", "ja") == "⚠️ 要確認"


def test_weather_term_three_languages():
    assert weather_term("晴", "zh") == "晴"
    assert weather_term("晴", "en") == "Clear"
    assert weather_term("晴", "ja") == "晴れ"
    assert weather_term("北风", "en") == "North wind"
    # 未收录词原样返回，不丢失真实数据
    assert weather_term("某未知天气", "en") == "某未知天气"


# --------------------------------------------------------------------------- #
# 3. i18n 日文词条完整性
# --------------------------------------------------------------------------- #

def test_ja_ui_text_covers_all_keys():
    missing = [k for k in UI_TEXT if k not in UI_TEXT_JA]
    assert not missing, f"缺少日文词条: {missing}"


def test_t_ja_returns_japanese_not_chinese_or_english():
    for key in ("app_title", "planner_gen_btn", "city_checklist_btn", "guide_deepseek_btn"):
        ja = t(key, "ja")
        assert ja, key
        # 日文不该等于中文或英文文案
        assert ja != t(key, "zh"), f"{key} 日文 == 中文"
        assert ja != t(key, "en"), f"{key} 日文 == 英文"


# --------------------------------------------------------------------------- #
# 4. FAQ 三语言
# --------------------------------------------------------------------------- #

def test_quick_questions_three_languages():
    assert "酒店" in quick_questions("zh")[0]
    assert "Hotel refuses" in quick_questions("en")[0]
    assert "ホテル" in quick_questions("ja")[0]


def test_faq_answer_three_languages():
    assert faq_answer("hotel_refuse", "zh") == ""
    assert "passport" in faq_answer("hotel_refuse", "en").lower()
    assert "ホテル" in faq_answer("hotel_refuse", "ja")


def test_japanese_quick_questions_hit_unique_faq():
    ja_qs = quick_questions("ja")
    hit_ids = {match_faq(q)["id"] for q in ja_qs}
    assert len(hit_ids) == len(ja_qs), f"日文问题存在歧义命中: {hit_ids}"


def test_question_label_three_languages():
    hit = match_faq("酒店说不能接外籍护照怎么办")
    assert question_label(hit, "zh").startswith("酒店")
    assert "Hotel refuses" in question_label(hit, "en")
    assert "ホテル" in question_label(hit, "ja")


# --------------------------------------------------------------------------- #
# 5. passport 三语言
# --------------------------------------------------------------------------- #

def test_passport_check_three_languages():
    for lang, expected in (("zh", "护照可直接在线预订"), ("en", "Passport can be used"), ("ja", "パスポートで直接オンライン予約")):
        r = check_passport_bookability("beijing", "gugong", has_chinese_phone=True, lang=lang)
        assert expected in r["reason"], f"{lang}: {r['reason']}"
        assert r["status"] == "✅ 可订"  # 规范枚举保持不变（供配色）
        assert r["status_label"]


def test_passport_check_status_label_follows_lang():
    r = check_passport_bookability("shanghai", "disney", has_chinese_phone=False, lang="ja")
    assert r["status_label"] == "⚠️ 要確認"


# --------------------------------------------------------------------------- #
# 6. crowd 三语言
# --------------------------------------------------------------------------- #

def test_crowd_three_languages():
    est = estimate_visit({"id": "gugong"}, "2026.10.01")  # 国庆 -> 拥挤
    assert crowd_label_for(est, "zh") == "拥挤"
    assert crowd_label_for(est, "en") == "Very crowded"
    assert crowd_label_for(est, "ja") == "大混雑"
    assert "early" == est["best_window"]
    assert best_window_for(est, "zh") != best_window_for(est, "en")
    assert best_window_for(est, "ja")
    assert date_tag_for(est, "zh") == "节假日"
    assert date_tag_for(est, "en") == "Holiday"
    assert date_tag_for(est, "ja") == "祝日"


# --------------------------------------------------------------------------- #
# 7. Day 8 / Day 9 回归（模板与占位符不受影响）
# --------------------------------------------------------------------------- #

def test_checklist_prompt_still_has_placeholders():
    from src.prompts.templates import ARRIVAL_CHECKLIST_PROMPT

    assert "{output_language}" in ARRIVAL_CHECKLIST_PROMPT
    assert "{city}" in ARRIVAL_CHECKLIST_PROMPT


def test_trip_planner_prompt_still_has_output_language():
    from src.prompts.templates import TRIP_PLANNER_PROMPT

    assert "{output_language}" in TRIP_PLANNER_PROMPT
    assert "{days}" in TRIP_PLANNER_PROMPT


def test_output_language_zh_en_ja():
    assert output_language("zh") == "中文"
    assert "English" in output_language("en")
    assert "Japanese" in output_language("ja")
