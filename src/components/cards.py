"""Streamlit 组件：攻略卡片渲染（Day 1-5 + Day 6-7 合并）。

- 队友 Day 1-5：render_attraction_card / render_guide_card /
  render_city_overview / render_essentials / render_quick_questions
- Day 6-7：render_guide_result（渲染 DeepSeek 结构化攻略 JSON）
"""

from typing import Any

import streamlit as st


def render_attraction_card(attr: dict, show_guide_button: bool = True) -> None:
    """渲染单个景点卡片"""
    status_color = {
        "✅ 可订": "green",
        "⚠️ 需人工": "orange",
        "❌ 不可": "red",
    }.get(attr.get("status", ""), "gray")

    with st.container():
        cols = st.columns([3, 1])
        with cols[0]:
            st.subheader(f"{attr['name']} ({attr['name_en']})")
            st.caption(f"{attr['category']} · {attr['description'][:60]}...")
        with cols[1]:
            st.markdown(
                f"<span style='color:{status_color};font-size:20px;font-weight:bold;'>{attr['status']}</span>",
                unsafe_allow_html=True,
            )

        # 关键信息行
        info_cols = st.columns(4)
        with info_cols[0]:
            st.metric("门票", f"¥{attr['passport']['price_cny']}")
        with info_cols[1]:
            passport_ok = "✅" if attr['passport']['passport_accepted'] else "❌"
            st.metric("接受护照", passport_ok)
        with info_cols[2]:
            phone_req = "是" if attr['passport']['requires_chinese_phone'] else "否"
            st.metric("需中国手机号", phone_req)
        with info_cols[3]:
            st.metric("提前预订", f"{attr['passport']['advance_booking_days']}天")

        # 操作按钮
        if show_guide_button:
            if st.button("📋 生成攻略", key=f"guide_{attr['id']}"):
                st.session_state.selected_attraction = attr
                st.session_state.page = "guide"
                st.rerun()

        st.divider()


def render_guide_card(guide_data: dict) -> None:
    """渲染结构化攻略卡片（队友 Day 1-5 旧 schema，保留）"""
    st.header(f"📍 {guide_data['attraction_name']} 攻略")

    # 护照预订指南
    with st.expander("🛂 护照预订指南", expanded=True):
        passport = guide_data["passport_guide"]
        st.write(f"**在线预订：** {passport['bookable']}")
        st.write(f"**预订平台：** {passport['platform']}")
        st.write(f"**接受护照：** {passport['passport_accepted']}")
        st.write(f"**需中国手机号：** {passport['requires_phone']}")
        st.write(f"**建议提前：** {passport['advance_days']}天")
        st.write(f"**门票价格：** {passport['price']}")

    # 分步购票指引
    with st.expander("🎫 分步购票指引"):
        for i, step in enumerate(guide_data["booking_steps"], 1):
            st.write(f"**Step {i}：** {step}")

    # 出行路线
    with st.expander("🚇 出行路线"):
        route = guide_data["route"]
        st.write(f"**交通方式：** {route['transport']}")
        st.write(f"**地铁线路：** {route['metro']}")
        st.write(f"**预计用时：** {route['duration']}")
        st.write(f"**最佳出发：** {route['best_time']}")

    # 备选方案
    with st.expander("🔄 备选方案"):
        for alt in guide_data["alternatives"]:
            st.write(f"**{alt['name']}：** {alt['reason']}")

    # 应急话术
    with st.expander("🆘 应急话术"):
        for phrase in guide_data["emergency_phrases"]:
            st.write(f"{phrase['cn']} / *{phrase['en']}*")


def render_city_overview(city_data: dict) -> None:
    """渲染城市概览卡片"""
    city = city_data["city"]

    st.header(f"🏙️ {city['name']} ({city['name_en']})")
    st.write(city["description"])

    # 亮点
    st.subheader("✨ 亮点")
    for highlight in city["highlights"]:
        st.write(f"- {highlight}")

    # 交通
    st.subheader("🚆 交通")
    transport = city["transport"]
    st.write(f"**机场：** {transport['airport']}")
    st.write(f"**机场→市区：** {transport['airport_to_city']}")
    st.write(f"**市内交通：** {transport['city_transport']}")
    st.info("💡 **提示：** " + "；".join(transport["tips"]))

    # 注意事项
    st.subheader("⚠️ 注意事项")
    for note in city["notes"]:
        st.write(f"- {note}")

    # 推荐 App
    st.subheader("📱 推荐 App")
    app_cols = st.columns(len(city["apps"]))
    for i, app in enumerate(city["apps"]):
        with app_cols[i]:
            req_badge = "🔴 必需" if app["required"] else "⚪ 可选"
            st.write(f"**{app['name']}**")
            st.caption(f"{app['purpose']}")
            st.caption(req_badge)


def render_essentials(city_data: dict) -> None:
    """渲染落地必备信息卡片（调研驱动：对应问卷 Q11 高频痛点）

    覆盖：SIM/网络、支付、酒店、打车、公安登记、公共交通购票
    """
    ess = city_data.get("city", {}).get("essentials")
    if not ess:
        return

    st.subheader("📶 落地必备指南")
    st.caption("基于《外国游客来华旅行痛点调研》高频痛点整理（SIM卡4.27/支付被拒4.20/酒店拒外宾4.17/护照购票4.17/打车4.17/公安登记3.93）")

    sections = [
        ("📶 SIM 卡 / 网络", ess.get("sim_data", "")),
        ("💰 支付方式", ess.get("payment", "")),
        ("🏨 酒店预订", ess.get("hotel_booking", "")),
        ("🚕 打车 / 网约车", ess.get("ride_hailing", "")),
        ("🛂 公安住宿登记", ess.get("police_registration", "")),
        ("🚇 公共交通购票", ess.get("public_transport", "")),
    ]
    with st.expander("点击展开全部落地指南", expanded=False):
        for title, content in sections:
            if content:
                st.markdown(f"**{title}**")
                st.write(content)


def render_quick_questions(on_click) -> None:
    """渲染快捷提问按钮行（对应原型场景4：动态对话入口）

    Args:
        on_click: 点击后回调，接收问题字符串
    """
    from src.utils.faq_kb import quick_questions

    st.subheader("💬 途中高频问题（点一下直接问）")
    qs = quick_questions()
    cols = st.columns(len(qs))
    for i, q in enumerate(qs):
        with cols[i]:
            if st.button(q, key=f"quickq_{i}", use_container_width=True):
                on_click(q)


def render_guide_result(result: dict[str, Any] | None) -> None:
    """渲染 DeepSeek 结构化攻略结果（Day 6-7）。

    :param result: ``generate_guide`` 的返回值，``status`` 为 ``success`` 或
        ``fallback``。非字典 / 状态未知时按 fallback 兜底展示，不抛异常。
    """
    if not isinstance(result, dict):
        st.warning("暂时无法生成完整攻略")
        st.write("AI服务暂时不可用，请稍后重试。")
        return

    status = result.get("status")

    if status != "success":
        # fallback 或未知状态：只展示友好提示，绝不展示 traceback。
        st.warning(result.get("title") or "暂时无法生成完整攻略")
        st.write(result.get("message") or "AI服务暂时不可用，请稍后重试。")
        notice = result.get("notice")
        if notice:
            st.caption(notice)
        return

    st.subheader(result.get("title") or "游玩攻略")

    destination = result.get("destination") or {}
    city = destination.get("city") or ""
    attraction = destination.get("attraction") or ""
    if city or attraction:
        st.markdown(f"**目的地**：{city} · {attraction}".strip())

    # ------------------------------------------------------------------ #
    # 🎫 购票/预约
    # ------------------------------------------------------------------ #
    booking = result.get("booking") or {}
    st.markdown("### 🎫 购票/预约")
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
        st.write(f"官方来源：{source_url}")

    # ------------------------------------------------------------------ #
    # 🚇 交通
    # ------------------------------------------------------------------ #
    transport = result.get("transport") or {}
    st.markdown("### 🚇 交通")
    route = transport.get("recommended_route")
    if route:
        st.write(route)
    for step in transport.get("steps") or []:
        st.write(f"- {step}")
    estimated_time = transport.get("estimated_time")
    if estimated_time:
        st.caption(f"预计耗时：{estimated_time}")

    # ------------------------------------------------------------------ #
    # 🔄 备选景点
    # ------------------------------------------------------------------ #
    alternatives = result.get("alternatives") or []
    st.markdown("### 🔄 备选景点")
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
        st.write("暂无备选景点。")

    # ------------------------------------------------------------------ #
    # 🆘 应急帮助
    # ------------------------------------------------------------------ #
    emergency = result.get("emergency") or {}
    st.markdown("### 🆘 应急帮助")
    problem = emergency.get("problem")
    if problem:
        st.write(problem)
    for step in emergency.get("steps") or []:
        st.write(f"- {step}")

    notice = result.get("notice")
    if notice:
        st.caption(notice)
