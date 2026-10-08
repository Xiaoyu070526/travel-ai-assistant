"""Streamlit 组件：攻略卡片渲染（Day 1-5 + Day 6-7 合并）。

- 队友 Day 1-5：render_attraction_card / render_city_overview /
  render_essentials / render_quick_questions
- Day 6-7：render_guide_result（渲染 DeepSeek 结构化攻略 JSON）
"""

from typing import Any

import streamlit as st

from src.utils.i18n import status_label, t
from src.utils.content_loader import display_name


def render_attraction_card(attr: dict, show_guide_button: bool = True, lang: str = "en") -> None:
    """渲染单个景点卡片"""
    status_color = {
        "✅ 可订": "green",
        "⚠️ 需人工": "orange",
        "❌ 不可": "red",
    }.get(attr.get("status", ""), "gray")

    with st.container():
        cols = st.columns([3, 1])
        with cols[0]:
            st.subheader(display_name(attr, lang))
            st.caption(f"{attr['category']} · {attr['description'][:60]}...")
        with cols[1]:
            st.markdown(
                f"<span style='color:{status_color};font-size:20px;font-weight:bold;'>{status_label(attr['status'], lang)}</span>",
                unsafe_allow_html=True,
            )

        # 关键信息行
        info_cols = st.columns(4)
        with info_cols[0]:
            st.metric(t("card_ticket", lang), f"¥{attr['passport']['price_cny']}")
        with info_cols[1]:
            passport_ok = "✅" if attr['passport']['passport_accepted'] else "❌"
            st.metric(t("card_passport_ok", lang), passport_ok)
        with info_cols[2]:
            phone_req = t("card_yes", lang) if attr['passport']['requires_chinese_phone'] else t("card_no", lang)
            st.metric(t("card_phone_req", lang), phone_req)
        with info_cols[3]:
            st.metric(
                t("card_advance_booking", lang),
                t("card_advance_days_fmt", lang, days=attr["passport"]["advance_booking_days"]),
            )

        # 操作按钮
        if show_guide_button:
            if st.button(t("card_guide_btn", lang), key=f"guide_{attr['id']}"):
                st.session_state.selected_attraction = attr
                st.session_state.page = "guide"
                st.rerun()

        st.divider()


def render_city_overview(city_data: dict, lang: str = "en") -> None:
    """渲染城市概览卡片"""
    city = city_data["city"]

    st.header(t("card_city_hdr", lang, name=display_name(city, lang)))
    st.write(city["description"])

    # 亮点
    st.subheader(t("card_highlights", lang))
    for highlight in city["highlights"]:
        st.write(f"- {highlight}")

    # 交通
    st.subheader(t("card_transport", lang))
    transport = city["transport"]
    st.write(f"**{t('card_airport', lang)}：** {transport['airport']}")
    st.write(f"**{t('card_airport_to_city', lang)}：** {transport['airport_to_city']}")
    st.write(f"**{t('card_city_transport', lang)}：** {transport['city_transport']}")
    st.info(t("card_tips_fmt", lang, tips="；".join(transport["tips"])))

    # 注意事项
    st.subheader(t("card_notes", lang))
    for note in city["notes"]:
        st.write(f"- {note}")

    # 推荐 App
    st.subheader(t("card_apps", lang))
    app_cols = st.columns(len(city["apps"]))
    for i, app in enumerate(city["apps"]):
        with app_cols[i]:
            req_badge = t("card_required", lang) if app.get("required", False) else t("card_optional", lang)
            st.write(f"**{app['name']}**")
            st.caption(f"{app['purpose']}")
            st.caption(req_badge)


def render_essentials(city_data: dict, lang: str = "en") -> None:
    """渲染落地必备信息卡片（调研驱动：对应问卷 Q11 高频痛点）

    覆盖：SIM/网络、支付、酒店、打车、公安登记、公共交通购票
    """
    ess = city_data.get("city", {}).get("essentials")
    if not ess:
        return

    st.subheader(t("card_essentials_title", lang))
    st.caption(t("card_essentials_caption", lang))

    sections = [
        (t("card_sim", lang), ess.get("sim_data", "")),
        (t("card_payment", lang), ess.get("payment", "")),
        (t("card_hotel", lang), ess.get("hotel_booking", "")),
        (t("card_ride", lang), ess.get("ride_hailing", "")),
        (t("card_registration", lang), ess.get("police_registration", "")),
        (t("card_public_transport", lang), ess.get("public_transport", "")),
    ]
    with st.expander(t("card_essentials_expander", lang), expanded=False):
        for title, content in sections:
            if content:
                st.markdown(f"**{title}**")
                st.write(content)


def render_quick_questions(on_click, lang: str = "en") -> None:
    """渲染快捷提问按钮行（对应原型场景4：动态对话入口）

    Args:
        on_click: 点击后回调，接收问题字符串
        lang: 界面语言（en 时使用英文问题；其余沿用中文问题便于知识库命中）
    """
    from src.utils.faq_kb import quick_questions

    st.subheader(t("card_quick_questions", lang))
    qs = quick_questions(lang=lang)
    cols = st.columns(len(qs))
    for i, q in enumerate(qs):
        with cols[i]:
            if st.button(q, key=f"quickq_{i}", use_container_width=True):
                on_click(q)


def render_guide_result(result: dict[str, Any] | None, lang: str = "en") -> None:
    """渲染 DeepSeek 结构化攻略结果（Day 6-7）。

    :param result: ``generate_guide`` 的返回值，``status`` 为 ``success`` 或
        ``fallback``。非字典 / 状态未知时按 fallback 兜底展示，不抛异常。
    :param lang: 界面语言（用于小节标题等静态文案）。
    """
    if not isinstance(result, dict):
        st.warning(t("card_guide_fallback_title", lang))
        st.write(t("card_guide_fallback_msg", lang))
        return

    status = result.get("status")

    if status != "success":
        # fallback 或未知状态：只展示友好提示，绝不展示 traceback。
        st.warning(result.get("title") or t("card_guide_fallback_title", lang))
        st.write(result.get("message") or t("card_guide_fallback_msg", lang))
        notice = result.get("notice")
        if notice:
            st.caption(notice)
        return

    st.subheader(result.get("title") or t("guide_header_fmt", lang, name=""))

    destination = result.get("destination") or {}
    city = destination.get("city") or ""
    attraction = destination.get("attraction") or ""
    if city or attraction:
        st.markdown(t("card_destination", lang, text=f"{city} · {attraction}".strip()))

    # ------------------------------------------------------------------ #
    # 🎫 购票/预约
    # ------------------------------------------------------------------ #
    booking = result.get("booking") or {}
    st.markdown(t("guide_section_booking", lang))
    status_label = booking.get("status_label")
    if status_label:
        st.write(status_label)
    for step in booking.get("steps") or []:
        if isinstance(step, dict):
            action = step.get("action")
            note = step.get("note")
            if action:
                st.write(f"- {action}")
            if note:
                st.caption(note)
        else:
            st.write(f"- {step}")
    source_url = booking.get("source_url")
    if source_url:
        st.write(t("guide_source_official", lang) + source_url)

    # ------------------------------------------------------------------ #
    # 🚇 交通
    # ------------------------------------------------------------------ #
    transport = result.get("transport") or {}
    st.markdown(t("guide_section_transport", lang))
    route = transport.get("recommended_route")
    if route:
        st.write(route)
    for step in transport.get("steps") or []:
        st.write(f"- {step}")
    estimated_time = transport.get("estimated_time")
    if estimated_time:
        st.caption(t("guide_eta_fmt", lang, time=estimated_time))

    # ------------------------------------------------------------------ #
    # 🔄 备选景点
    # ------------------------------------------------------------------ #
    alternatives = result.get("alternatives") or []
    st.markdown(t("guide_section_alternatives", lang))
    if alternatives:
        for alt in alternatives:
            if isinstance(alt, dict):
                reason = alt.get("reason")
                alt_id = alt.get("attraction_id")
                if reason:
                    st.write(f"- {reason}" + (f"（{alt_id}）" if alt_id else ""))
            else:
                st.write(f"- {alt}")
    else:
        st.write(t("guide_no_alternatives", lang))

    # ------------------------------------------------------------------ #
    # 🆘 应急帮助
    # ------------------------------------------------------------------ #
    emergency = result.get("emergency") or {}
    st.markdown(t("guide_section_emergency", lang))
    problem = emergency.get("problem")
    if problem:
        st.write(problem)
    for step in emergency.get("steps") or []:
        st.write(f"- {step}")

    notice = result.get("notice")
    if notice:
        st.caption(notice)
