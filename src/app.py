"""旅游AI助手 - Streamlit 主应用入口（Day 1-5 多页面 + Day 6-7 DeepSeek 攻略）

Demo 场景：
1. 身份采集（国籍/到达日期/中文水平）
2. 城市推荐（城市简介 + 5景点带护照可行性标签）
3. 选景点 → 生成结构化攻略卡片（Day 6-7 DeepSeek / 队友 Qwen 双通道）
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
from src.api.qwen import chat
from src.api.llm_client import generate_guide
from src.utils.passport_check import check_passport_bookability
from src.utils.faq_kb import match_faq
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


# =============================================================================
# 页面 1：身份采集
# =============================================================================

def page_identity():
    st.header("👋 欢迎！让我们了解你的旅行计划")
    st.write("为了给你定制专属的来华旅行方案，请回答以下几个问题：")

    with st.form("identity_form"):
        nationality = st.text_input("1. 你的国籍是？", placeholder="例如：美国、英国、日本")
        arrival_date = st.text_input("2. 预计到达日期？", placeholder="例如：下周一、2026-10-01")
        chinese_level = st.selectbox(
            "3. 你的中文水平？",
            ["完全不会", "基础（能听懂简单词汇）", "会话级（日常交流）", "流利"],
        )
        purpose = st.selectbox(
            "4. 旅行目的？",
            ["旅游", "商务", "探亲访友", "留学/学习", "其他"],
        )
        submitted = st.form_submit_button("✅ 确认，开始规划行程")

    if submitted and nationality and arrival_date:
        st.session_state.identity = {
            "nationality": nationality,
            "arrival_date": arrival_date,
            "chinese_level": chinese_level,
            "purpose": purpose,
        }
        # 身份采集完成后，展示行前准备 Checklist（新增大模型能力）
        st.session_state.page = "city"
        st.rerun()
    elif submitted:
        st.warning("请填写完整信息后再提交。")


# =============================================================================
# 页面 2：城市推荐
# =============================================================================

def page_city():
    identity = st.session_state.identity
    st.header(f"🗺️ {identity.get('nationality', '游客')}朋友，想去哪里玩？")
    st.caption(f"到达日期：{identity.get('arrival_date', '未定')} | 中文水平：{identity.get('chinese_level', '未定')}")

    # 城市选择
    cities = list_cities()
    if not cities:
        st.error("暂无城市数据，请联系管理员添加知识库。")
        return

    city_choice = st.selectbox(
        "选择一个城市",
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
    render_city_overview(city_data)

    # 落地必备指南（调研痛点驱动）
    render_essentials(city_data)

    # 行前准备 Checklist（调研 Q15：行前准备清单价值 3.73）
    st.divider()
    if st.button("🧳 生成我的行前准备 Checklist", type="secondary"):
        with st.spinner("正在生成行前清单..."):
            _generate_checklist(city_data, identity)

    # 景点推荐
    st.subheader("🏛️ 推荐景点")
    st.info("每个景点显示护照可行性标签：✅可订 / ⚠️需人工 / ❌不可")

    for attr in city_data["attractions"]:
        render_attraction_card(attr, show_guide_button=True)

    # 兜底问答入口
    st.divider()
    with st.expander("💬 有问题？随时问我"):
        question = st.text_input("输入你的问题", placeholder="例如：支付宝绑卡失败了怎么办？")
        if question:
            _handle_faq(question, identity)


# =============================================================================
# 页面 3：攻略生成
# =============================================================================

def page_guide():
    identity = st.session_state.identity
    attr = st.session_state.selected_attraction

    if not attr:
        st.session_state.page = "city"
        st.rerun()
        return

    st.header(f"📍 {attr['name']} 详细攻略")

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
    st.subheader("🔍 预订可行性诊断")
    has_phone = identity.get("has_chinese_phone", False)
    if st.checkbox("我有中国手机号（可用于接收验证码）", value=has_phone, key="has_phone"):
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
        st.write(f"**判断依据：** {check_result['reason']}")
        st.info(f"**建议操作：** {check_result['action']}")
        st.caption(f"{check_result['details']}")

    # 护照预订信息
    st.subheader("🛂 护照预订信息")
    p = attr["passport"]
    info_cols = st.columns(4)
    info_cols[0].metric("在线预订", "✅ 是" if p["bookable_online"] else "❌ 否")
    info_cols[1].metric("接受护照", "✅ 是" if p["passport_accepted"] else "❌ 否")
    info_cols[2].metric("需中国手机号", "是" if p["requires_chinese_phone"] else "否")
    info_cols[3].metric("门票", f"¥{p['price_cny']}")

    st.write(f"**预订平台：** {p['platform']}")
    st.write(f"**建议提前：** {p['advance_booking_days']} 天预订")
    st.write(f"**价格说明：** {p['price_notes']}")

    # 入园信息
    st.subheader("📍 入园信息")
    e = attr["entry"]
    st.write(f"**地址：** {e['location']}")
    st.write(f"**最近地铁：** {e['nearest_metro']}")
    st.write(f"**开放时间：** {e['hours']}")
    st.write(f"**入园方式：** {e['entry_method']}")

    st.info("**实用提示：**")
    for tip in e["tips"]:
        st.write(f"- {tip}")

    # 备选景点
    if attr.get("alternatives"):
        st.subheader("🔄 备选景点")
        for alt in attr["alternatives"]:
            st.write(f"**{alt['name']}：** {alt['reason']}")

    # 数据来源标注（原型要求：每条知识库含 source + updated_at，不编造）
    if attr.get("sources"):
        st.divider()
        st.caption("📚 **信息来源：** " + "；".join(attr["sources"]))
        if attr.get("updated_at"):
            st.caption(f"🕒 数据更新时间：{attr['updated_at']}（信息仅供参考，以官方最新为准）")

    # AI 生成攻略（Day 6-7：DeepSeek 结构化攻略，失败自动 fallback）
    st.divider()
    if st.button("🤖 让 AI 生成完整攻略", type="primary"):
        with st.spinner("正在生成攻略..."):
            _generate_deepseek_guide(attr, identity)

    # 备用：通义千问文字版攻略（队友 Day 1-5 原能力，保留）
    if st.button("🈯 用通义千问生成文字版攻略"):
        with st.spinner("正在生成攻略..."):
            guide = _generate_guide(attr, identity)
            if guide:
                st.success("攻略生成完成！")
                st.markdown(guide)
            else:
                st.error("攻略生成失败，请检查 API 配置。")

    # 返回按钮
    if st.button("← 返回景点列表"):
        st.session_state.selected_attraction = None
        st.session_state.page = "city"
        st.rerun()


# =============================================================================
# 页面 4：途中求助（动态对话）
# =============================================================================

def page_chat():
    identity = st.session_state.identity
    st.header("🆘 途中求助")
    st.caption("任何途中问题（支付失败 / 酒店拒外宾 / 找不到路 / 网络异常）都可随时提问 —— 不是静态攻略，是动态对话。")

    # 快捷提问按钮（本地 FAQ 知识库）
    render_quick_questions(on_click=lambda q: _ask_faq(q, identity))

    st.divider()

    # 对话历史
    for msg in st.session_state.chat_history:
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(msg["content"])

    # 输入框
    user_input = st.chat_input("输入你的问题，例如：支付宝绑卡失败了怎么办？")
    if user_input:
        _ask_faq(user_input, identity)


def _ask_faq(question: str, identity: dict) -> None:
    """处理途中提问：优先本地 FAQ 知识库，未命中走 LLM"""
    # 记录用户问题
    st.session_state.chat_history.append({"role": "user", "content": question})

    # 本地知识库优先（稳定、无 API 依赖）
    hit = match_faq(question)
    if hit:
        answer = f"🤖 **{hit['question']}**\n\n{hit['answer']}"
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        return

    # 本地未命中 → LLM 兜底
    try:
        prompt = FALLBACK_PROMPT.format(
            nationality=identity.get("nationality", "外国游客"),
            chinese_level=identity.get("chinese_level", "完全不会"),
            city=st.session_state.selected_city or "北京",
            question=question,
            faq_reference="（暂无本地知识库命中，请基于常识给出稳妥建议，不编造具体政策）",
        )
        answer = chat(prompt, model="qwen-turbo")
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
    except Exception as e:
        st.session_state.chat_history.append(
            {"role": "assistant", "content": f"⚠️ 调用 AI 失败：{e}。请稍后重试，或直接提问酒店/平台客服。"}
        )


# =============================================================================
# 辅助函数
# =============================================================================

def _generate_checklist(city_data: dict, identity: dict) -> None:
    """调用 LLM 生成行前准备清单（原型 Day 新增能力：行前 Checklist）"""
    try:
        city_name = city_data["city"]["name"]
        prompt = ARRIVAL_CHECKLIST_PROMPT.format(
            nationality=identity.get("nationality", "外国游客"),
            arrival_date=identity.get("arrival_date", "未定"),
            chinese_level=identity.get("chinese_level", "完全不会"),
            city=city_name,
            city_data=format_city_data(city_data),
        )
        checklist = chat(prompt, model="qwen-turbo")
        st.success("你的行前准备清单已生成：")
        st.markdown(checklist)
    except Exception as e:
        st.error(f"生成清单失败: {e}")


def _generate_guide(attr: dict, identity: dict) -> str | None:
    """调用通义千问生成文字版攻略（队友 Day 1-5 原能力，保留）"""
    try:
        prompt = GUIDE_GENERATION_PROMPT.format(
            nationality=identity.get("nationality", "外国游客"),
            chinese_level=identity.get("chinese_level", "完全不会"),
            attraction_name=attr["name"],
            attraction_name_en=attr["name_en"],
            attraction_data=format_attraction_data(attr),
        )
        return chat(prompt, model="qwen-turbo")
    except Exception as e:
        st.error(f"调用 LLM 失败: {e}")
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

    return {
        "nationality": identity.get("nationality") or "unknown",
        "arrival_date": identity.get("arrival_date") or "unknown",
        "chinese_level": _map_chinese_level(identity.get("chinese_level")),
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
    render_guide_result(result)


def _handle_faq(question: str, identity: dict) -> None:
    """处理兜底问答：本地 FAQ 知识库优先，未命中走 LLM"""
    # 本地知识库优先（稳定、无 API 依赖）
    hit = match_faq(question)
    if hit:
        st.write("**AI：**")
        st.markdown(f"**{hit['question']}**\n\n{hit['answer']}")
        return
    try:
        prompt = FALLBACK_PROMPT.format(
            nationality=identity.get("nationality", "外国游客"),
            chinese_level=identity.get("chinese_level", "完全不会"),
            city=st.session_state.selected_city or "北京",
            question=question,
            faq_reference="（暂无本地知识库命中，请基于常识给出稳妥建议，不编造具体政策）",
        )
        answer = chat(prompt, model="qwen-turbo")
        st.write("**AI：**")
        st.write(answer)
    except Exception as e:
        st.error(f"调用 LLM 失败: {e}")


# =============================================================================
# 主入口
# =============================================================================

def main():
    st.set_page_config(
        page_title="🧳 AI入境旅游搭子",
        page_icon="🧳",
        layout="wide",
    )

    init_session()
    config = load_config()

    # 顶部导航
    st.sidebar.title("🧳 AI入境旅游搭子")
    st.sidebar.caption("智能旅行规划助手")

    # API 状态
    status = "✅ 已配置" if config.api_keys_ready() else "⚠️ 未配置 .env"
    st.sidebar.info(f"API 配置状态：{status}")

    # 导航按钮
    if st.sidebar.button("🏠 身份采集"):
        st.session_state.page = "identity"
        st.rerun()
    if st.sidebar.button("🗺️ 城市推荐"):
        st.session_state.page = "city"
        st.rerun()
    if st.sidebar.button("🆘 途中求助"):
        st.session_state.page = "chat"
        st.rerun()

    # 当前身份展示
    if st.session_state.identity:
        st.sidebar.divider()
        st.sidebar.write("**当前游客信息：**")
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


if __name__ == "__main__":
    main()
