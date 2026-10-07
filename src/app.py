"""旅游AI助手 - Streamlit 主应用入口（Day 1-5 多页面 + Day 6-7 DeepSeek 攻略）

Demo 场景：
1. 身份采集（国籍/到达日期/中文水平）
2. 城市推荐（城市简介 + 5景点带护照可行性标签）
3. 选景点 → 生成结构化攻略卡片（Day 6-7 DeepSeek）
4. 途中兜底（FAQ对话）
"""

import sys
from pathlib import Path

# 把项目根目录加入 sys.path，保证顶层包 ``src`` 始终可导入。
# Streamlit / 直接运行脚本时只会把脚本所在目录（src/）加入 sys.path，
# 因此 ``from src.* import ...`` 需要项目根目录在 sys.path 中。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import os

from dotenv import load_dotenv
import streamlit as st
from src.utils.config import load_config
from src.utils.content_loader import load_city_data, list_cities
from src.components.cards import (
    render_attraction_card,
    render_city_overview,
    render_essentials,
    render_guide_result,
    render_quick_questions,
)
from src.api.llm_client import LLMClient, generate_guide
from src.utils.passport_check import check_passport_bookability
from src.utils.faq_kb import match_faq
from src.utils.errors import APIResponseError
from src.utils.i18n import (
    SUPPORTED_LANGUAGES,
    language_display_name,
    output_language,
    faq_answer,
    t,
)
from src.prompts.templates import (
    ARRIVAL_CHECKLIST_PROMPT,
    GUIDE_GENERATION_PROMPT,
    FALLBACK_PROMPT,
    format_attraction_data,
    format_city_data,
)

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


# =============================================================================
# Session State 初始化
# =============================================================================

def init_session():
    defaults = {
        "page": "identity",  # identity / city / guide / chat
        "identity": {},
        "selected_city": None,
        "selected_attraction": None,
        "chat_history": [],
        "faq_answered": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _get_lang() -> str:
    """获取当前界面的语言偏好（identity.language，未设置默认 en）。"""
    return (st.session_state.identity or {}).get("language", "en")


def _deepseek_text(prompt: str) -> str:
    """调用 DeepSeek 生成自由文本（FAQ 兜底 / 行前 Checklist / 文字攻略）。

    替代原通义千问 ``chat``。失败时抛出底层异常，由调用方 try/except 统一兜底。
    """
    system = "你是一名专业、谨慎的中国入境旅游助手，请用简洁、清晰、可执行的语言回答。"
    return LLMClient().complete(system=system, user=prompt)


# =============================================================================
# 页面 1：身份采集
# =============================================================================

def page_identity():
    st.header(t("identity_greeting", _get_lang()))
    st.write(t("identity_sub", _get_lang()))

    with st.form("identity_form"):
        language = st.selectbox(
            t("identity_lang_label", _get_lang()),
            list(SUPPORTED_LANGUAGES),
            format_func=language_display_name,
        )
        nationality = st.text_input(
            t("identity_q_nationality", language),
            placeholder=t("identity_q_nationality_ph", language),
        )
        arrival_date = st.text_input(
            t("identity_q_arrival", language),
            placeholder=t("identity_q_arrival_ph", language),
        )
        chinese_level = st.selectbox(
            t("identity_q_chinese", language),
            ["完全不会", "基础（能听懂简单词汇）", "会话级（日常交流）", "流利"],
            format_func=lambda x: t(
                {
                    "完全不会": "cl_none",
                    "基础（能听懂简单词汇）": "cl_basic",
                    "会话级（日常交流）": "cl_conversational",
                    "流利": "cl_fluent",
                }.get(x, "cl_none"),
                language,
            ),
        )
        purpose = st.selectbox(
            t("identity_q_purpose", language),
            ["旅游", "商务", "探亲访友", "留学/学习", "其他"],
            format_func=lambda x: t(
                {
                    "旅游": "purpose_tourism",
                    "商务": "purpose_business",
                    "探亲访友": "purpose_visit",
                    "留学/学习": "purpose_study",
                    "其他": "purpose_other",
                }.get(x, "purpose_other"),
                language,
            ),
        )
        submitted = st.form_submit_button(t("identity_submit", language))

    if submitted and nationality and arrival_date:
        st.session_state.identity = {
            "nationality": nationality,
            "arrival_date": arrival_date,
            "chinese_level": chinese_level,
            "purpose": purpose,
            "language": language,
        }
        # 身份采集完成后，展示行前准备 Checklist（新增大模型能力）
        st.session_state.page = "city"
        st.rerun()
    elif submitted:
        st.warning(t("identity_warning", _get_lang()))


# =============================================================================
# 页面 2：城市推荐
# =============================================================================

def page_city():
    identity = st.session_state.identity
    lang = _get_lang()
    st.header(t("city_header_fmt", lang, nationality=identity.get("nationality", "Friend")))
    st.caption(
        t("city_caption_fmt", lang, arrival=identity.get("arrival_date", "-"),
          level=identity.get("chinese_level", "-"))
    )

    # 城市选择
    cities = list_cities()
    if not cities:
        st.error(t("city_no_data", lang))
        return

    city_choice = st.selectbox(
        t("city_select", lang),
        cities,
        format_func=lambda x: x.capitalize(),
    )

    if not city_choice:
        return

    st.session_state.selected_city = city_choice

    city_data = load_city_data(city_choice)
    if not city_data:
        st.error(f"无法加载 {city_choice} 的数据。")
        return

    # 城市概览
    render_city_overview(city_data, lang=lang)

    # 落地必备指南（调研痛点驱动）
    render_essentials(city_data, lang=lang)

    # 行前准备 Checklist（调研 Q15：行前准备清单价值 3.73）
    st.divider()
    if st.button(t("city_checklist_btn", lang), type="secondary"):
        with st.spinner(t("city_checklist_spinner", lang)):
            _generate_checklist(city_data, identity)

    # 景点推荐
    st.subheader(t("city_attractions_title", lang))
    st.info(t("city_attractions_info", lang))

    for attr in city_data["attractions"]:
        render_attraction_card(attr, show_guide_button=True, lang=lang)

    # 兜底问答入口
    st.divider()
    with st.expander(t("city_faq_title", lang)):
        question = st.text_input(t("city_faq_ph", lang), placeholder=t("city_faq_ph", lang))
        if question:
            _handle_faq(question, identity)


# =============================================================================
# 页面 3：攻略生成
# =============================================================================

def page_guide():
    identity = st.session_state.identity
    attr = st.session_state.selected_attraction
    lang = _get_lang()

    if not attr:
        st.session_state.page = "city"
        st.rerun()
        return

    st.header(t("guide_header_fmt", lang, name=attr["name"]))

    # 基础信息卡片
    cols = st.columns([2, 1])
    with cols[0]:
        st.subheader(f"{attr['name']} ({attr['name_en']})")
        st.write(attr["description"])
    with cols[1]:
        status = attr.get("status", "未知")
        status_color = {"✅ 可订": "green", "⚠️ 需人工": "orange", "❌ 不可": "red"}.get(status, "gray")
        st.markdown(f"<h2 style='color:{status_color};text-align:center;'>{status}</h2>", unsafe_allow_html=True)

    # 护照校验动态判断
    st.subheader(t("guide_bookability", lang))
    has_phone = identity.get("has_chinese_phone", False)
    if st.checkbox(t("guide_phone_checkbox", lang), value=has_phone, key="has_phone"):
        identity["has_chinese_phone"] = True
    else:
        identity["has_chinese_phone"] = False

    # 动态校验
    city_choice = st.session_state.selected_city
    check_result = check_passport_bookability(
        city_choice, attr["id"],
        has_chinese_phone=identity.get("has_chinese_phone", False)
    )

    # 显示动态校验结果
    check_cols = st.columns([1, 3])
    with check_cols[0]:
        check_status = check_result["status"]
        check_color = {"✅ 可订": "green", "⚠️ 需人工": "orange", "❌ 不可": "red"}.get(check_status, "gray")
        st.markdown(f"<h1 style='color:{check_color};text-align:center;'>{check_status}</h1>", unsafe_allow_html=True)
    with check_cols[1]:
        st.write(t("guide_basis", lang, reason=check_result['reason']))
        st.info(t("guide_action", lang, action=check_result['action']))
        st.caption(f"{check_result['details']}")

    # 护照预订信息
    st.subheader(t("guide_passport_info", lang))
    p = attr["passport"]
    info_cols = st.columns(4)
    info_cols[0].metric(t("guide_online", lang), "✅ 是" if p["bookable_online"] else "❌ 否")
    info_cols[1].metric(t("guide_passport_ok", lang), "✅ 是" if p["passport_accepted"] else "❌ 否")
    info_cols[2].metric(t("guide_cn_phone", lang), "是" if p["requires_chinese_phone"] else "否")
    info_cols[3].metric(t("guide_ticket_price", lang), f"¥{p['price_cny']}")

    st.write(t("guide_platform_fmt", lang, platform=p['platform']))
    st.write(t("guide_advance_fmt", lang, days=p['advance_booking_days']))
    st.write(t("guide_price_notes_fmt", lang, notes=p['price_notes']))

    # 入园信息
    st.subheader(t("guide_entry_info", lang))
    e = attr["entry"]
    st.write(t("guide_address_fmt", lang, addr=e['location']))
    st.write(t("guide_metro_fmt", lang, metro=e['nearest_metro']))
    st.write(t("guide_hours_fmt", lang, hours=e['hours']))
    st.write(t("guide_entry_fmt", lang, entry=e['entry_method']))

    st.info(t("guide_tips", lang))
    for tip in e["tips"]:
        st.write(f"- {tip}")

    # 备选景点
    if attr.get("alternatives"):
        st.subheader(t("guide_alternatives", lang))
        for alt in attr["alternatives"]:
            st.write(f"**{alt['name']}：** {alt['reason']}")

    # 数据来源标注（原型要求：每条知识库含 source + updated_at，不编造）
    if attr.get("sources"):
        st.divider()
        st.caption(t("guide_sources", lang) + "；".join(attr["sources"]))
        if attr.get("updated_at"):
            st.caption(t("guide_updated_fmt", lang, time=attr["updated_at"]))

    # AI 生成攻略（Day 6-7：DeepSeek 结构化攻略，失败自动 fallback）
    st.divider()
    st.subheader(t("guide_ai_section", lang))
    if st.button(t("guide_deepseek_btn", lang), type="primary"):
        with st.spinner("Generating..."):
            _generate_deepseek_guide(attr, identity)

    # 结构化攻略卡片（DeepSeek 文字版第二通道）
    if st.button(t("guide_deepseek_card_btn", lang)):
        with st.spinner("Generating..."):
            guide = _generate_guide(attr, identity)
            if guide:
                st.success("Guide ready!")
                st.markdown(guide)
            else:
                st.error("Guide generation failed. Check API config.")

    # 返回按钮
    if st.button(t("guide_back_btn", lang)):
        st.session_state.selected_attraction = None
        st.session_state.page = "city"
        st.rerun()


# =============================================================================
# 页面 4：途中求助（动态对话）
# =============================================================================

def page_chat():
    identity = st.session_state.identity
    lang = _get_lang()
    st.header(t("chat_title", lang))
    st.caption(t("chat_caption", lang))

    # 快捷提问按钮（本地 FAQ 知识库）
    render_quick_questions(on_click=lambda q: _ask_faq(q, identity), lang=lang)

    st.divider()

    # 对话历史
    for msg in st.session_state.chat_history:
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(msg["content"])

    # 输入框
    user_input = st.chat_input(t("chat_input", lang))
    if user_input:
        _ask_faq(user_input, identity)


def _ask_faq(question: str, identity: dict) -> None:
    """处理途中提问：优先本地 FAQ 知识库，未命中走 LLM"""
    lang = _get_lang()
    # 记录用户问题
    st.session_state.chat_history.append({"role": "user", "content": question})

    # 本地知识库优先（稳定、无 API 依赖）
    hit = match_faq(question)
    if hit:
        en_answer = faq_answer(hit["id"], lang)
        if en_answer:
            answer = f"🤖 **{hit['question']}**\n\n{en_answer}"
        else:
            answer = f"🤖 **{hit['question']}**\n\n{hit['answer']}"
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        return

    # 本地未命中 → LLM 兜底
    try:
        prompt = FALLBACK_PROMPT.format(
            nationality=identity.get("nationality", "Foreign traveler"),
            chinese_level=identity.get("chinese_level", "None"),
            city=st.session_state.selected_city or "Beijing",
            output_language=output_language(lang),
            question=question,
            faq_reference="（暂无本地知识库命中，请基于常识给出稳妥建议，不编造具体政策）",
        )
        answer = _deepseek_text(prompt)
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
    except Exception as e:
        st.session_state.chat_history.append(
            {"role": "assistant", "content": t("chat_llm_fail", lang, error=e)}
        )


# =============================================================================
# 辅助函数
# =============================================================================

def _generate_checklist(city_data: dict, identity: dict) -> None:
    """调用 DeepSeek 生成行前准备清单；空结果重试一次后友好提示，不伪造内容。"""
    lang = _get_lang()
    city_name = city_data["city"]["name"]
    prompt = ARRIVAL_CHECKLIST_PROMPT.format(
        nationality=identity.get("nationality", "Foreign traveler"),
        arrival_date=identity.get("arrival_date", "unknown"),
        chinese_level=identity.get("chinese_level", "None"),
        output_language=output_language(lang),
        city=city_name,
        city_data=format_city_data(city_data),
    )

    checklist = ""
    for _ in range(2):  # API 返回空内容时重试一次
        try:
            checklist = _deepseek_text(prompt)
            if checklist.strip():
                break
        except APIResponseError:
            checklist = ""  # 空响应 / 无法解析，重试
        except Exception as e:
            st.error(t("chat_llm_fail", lang, error=e))
            return

    if not checklist.strip():
        st.warning(t("city_checklist_empty", lang))
        return

    st.success(t("city_checklist_done", lang))
    st.markdown(checklist)


def _generate_guide(attr: dict, identity: dict) -> str | None:
    """调用 DeepSeek 生成文字版结构化攻略卡片（原通义千问通道已切换）。"""
    lang = _get_lang()
    try:
        prompt = GUIDE_GENERATION_PROMPT.format(
            nationality=identity.get("nationality", "Foreign traveler"),
            chinese_level=identity.get("chinese_level", "None"),
            output_language=output_language(lang),
            attraction_name=attr["name"],
            attraction_name_en=attr["name_en"],
            attraction_data=format_attraction_data(attr),
        )
        return _deepseek_text(prompt)
    except Exception as e:
        st.error(t("chat_llm_fail", lang, error=e))
        return None


def _map_chinese_level(level: str | None) -> str:
    """把队友中文水平标签映射为 Day 6-7 的英文枚举。

    Day 6-7 prompts 期望 none / basic / conversational / fluent；
    未知值原样透传，不凭空改写。
    """
    mapping = {
        "完全不会": "none",
        "基础（能听懂简单词汇）": "basic",
        "会话级（日常交流）": "conversational",
        "流利": "fluent",
    }
    return mapping.get(level or "", level or "none")


def _build_guide_context(attr: dict, identity: dict, city_choice: str) -> dict:
    """把队友 data/content 的景点字段安全映射为 Day 6-7 generate_guide 的 context。

    不修改 llm_client.py / prompts.py；不编造知识库中不存在的真实信息，
    缺失字段一律用 None / unknown / [] 等安全值。
    """
    passport = attr.get("passport") or {}
    entry = attr.get("entry") or {}

    # 队友 emoji 状态标签 -> Day 6-7 passport_booking_status 枚举
    status_map = {
        "✅ 可订": "supported",
        "⚠️ 需人工": "unknown",
        "❌ 不可": "not_supported",
    }
    passport_booking_status = status_map.get(attr.get("status"), "unknown")

    # 在线可订且需提前 N 天 -> 需要预约；不可在线订 -> 需人工（unknown，不编造）
    advance_days = passport.get("advance_booking_days")
    if passport.get("bookable_online") is True and isinstance(advance_days, (int, float)):
        reservation_required = advance_days > 0
    else:
        reservation_required = None

    # 备选景点：队友是 [{name, reason}]，用 name 作为标识（无独立 id）
    alternatives = attr.get("alternatives") or []
    alternative_attraction_ids = [
        alt.get("name") for alt in alternatives if isinstance(alt, dict) and alt.get("name")
    ]

    # 来源：队友是 sources 列表，取第一条；无则 None
    sources = attr.get("sources") or []
    source_url = sources[0] if sources else None

    # 城市中文名（load_city_data 里是 city.name）
    city_name = city_choice
    city_data = load_city_data(city_choice)
    if city_data and city_data.get("city", {}).get("name"):
        city_name = city_data["city"]["name"]

    lang = identity.get("language") or "en"
    return {
        "nationality": identity.get("nationality") or "unknown",
        "arrival_date": identity.get("arrival_date") or "unknown",
        "chinese_level": _map_chinese_level(identity.get("chinese_level")),
        "language": lang,
        "output_language": output_language(lang),
        "city": city_name,
        "attraction": attr,
        "passport_booking_status": passport_booking_status,
        "reservation_required": reservation_required,
        "entry_method": entry.get("entry_method"),
        "alternative_attraction_ids": alternative_attraction_ids,
        "source_url": source_url,
        "updated_at": attr.get("updated_at"),
    }


def _generate_deepseek_guide(attr: dict, identity: dict) -> None:
    """调用 Day 6-7 DeepSeek 生成结构化攻略并渲染。

    失败时 ``generate_guide`` 会返回 fallback 结构（不抛异常），
    由 ``render_guide_result`` 展示友好提示，绝不显示 traceback。
    """
    city_choice = st.session_state.selected_city or "beijing"
    context = _build_guide_context(attr, identity, city_choice)
    result = generate_guide(context)
    id_lang = _get_lang()
    render_guide_result(result, lang=id_lang)


def _handle_faq(question: str, identity: dict) -> None:
    """处理兜底问答：本地 FAQ 知识库优先，未命中走 LLM"""
    lang = _get_lang()

    # 本地知识库优先（稳定、无 API 依赖）
    hit = match_faq(question)
    if hit:
        en_answer = faq_answer(hit["id"], lang)
        if en_answer:
            st.write("**AI：**")
            st.markdown(f"**{hit['question']}**\n\n{en_answer}")
        else:
            st.write("**AI：**")
            st.markdown(f"**{hit['question']}**\n\n{hit['answer']}")
        return
    try:
        prompt = FALLBACK_PROMPT.format(
            nationality=identity.get("nationality", "Foreign traveler"),
            chinese_level=identity.get("chinese_level", "None"),
            city=st.session_state.selected_city or "Beijing",
            output_language=output_language(lang),
            question=question,
            faq_reference="（暂无本地知识库命中，请基于常识给出稳妥建议，不编造具体政策）",
        )
        answer = _deepseek_text(prompt)
        st.write("**AI：**")
        st.write(answer)
    except Exception as e:
        st.error(t("chat_llm_fail", lang, error=e))


# =============================================================================
# 主入口
# =============================================================================

def render_footer(lang: str) -> None:
    """页面底部合规与免责声明（Day 8-9：合规/来源标注/隐私说明）。"""
    st.divider()
    with st.container():
        st.markdown(f"#### {t('footer_disclaimer_title', lang)}")
        st.caption(t("footer_disclaimer_body", lang))
        st.caption(t("footer_source_note", lang))
        st.caption(t("footer_privacy", lang))


def main():
    st.set_page_config(
        page_title="AI China Travel Buddy",
        page_icon="🧳",
        layout="wide",
    )

    init_session()
    config = load_config()
    lang = _get_lang()

    # 顶部导航
    st.sidebar.title(t("app_title", lang))
    st.sidebar.caption(t("app_slogan", lang))

    # API 状态
    status = t("sidebar_api_ready", lang) if config.api_keys_ready() else t("sidebar_api_missing", lang)
    st.sidebar.info(f"API: {status}")

    # 导航按钮
    if st.sidebar.button(t("sidebar_nav_identity", lang)):
        st.session_state.page = "identity"
        st.rerun()
    if st.sidebar.button(t("sidebar_nav_city", lang)):
        st.session_state.page = "city"
        st.rerun()
    if st.sidebar.button(t("sidebar_nav_chat", lang)):
        st.session_state.page = "chat"
        st.rerun()

    # 当前身份展示
    if st.session_state.identity:
        st.sidebar.divider()
        st.sidebar.write(t("sidebar_identity", lang))
        for k, v in st.session_state.identity.items():
            st.sidebar.write(f"- {k}: {v}")

    # 页面路由
    page = st.session_state.page
    if page == "identity":
        page_identity()
    elif page == "city":
        page_city()
    elif page == "guide":
        page_guide()
    elif page == "chat":
        page_chat()
    else:
        page_identity()

    # 页面底部合规与免责声明（Day 8-9）
    render_footer(lang)


if __name__ == "__main__":
    main()
