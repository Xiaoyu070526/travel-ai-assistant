"""多语言支持模块（Day 8-9：多语言打磨）。

依据《外国游客来华旅行痛点调研》：28.13% 受调查者完全不会中文，
因此「身份采集 → 城市推荐 → 攻略」全链路必须让不会中文的游客也能看懂。

支持语言（5 种）：
    en: English（完整 UI 文案）
    zh: 中文（完整 UI 文案）
    fr: Français（界面文案回退英文，AI 输出按偏好语言）
    ja: 日本語（界面文案回退英文，AI 输出按偏好语言）
    ko: 한국어（界面文案回退英文，AI 输出按偏好语言）

设计约定：
- 界面静态文案用 :func:`t` 取词：``t("identity_greeting", lang)``，
  缺失时自动回退英文，绝不抛 KeyError。
- LLM 动态输出语言通过 :func:`output_language` 注入 prompt：
  ``language == "zh"`` → "中文"；其余 → 对应语言名。
- 语言偏好存于 ``st.session_state.identity["language"]``，
  未设置时默认 ``en``（演示场景：美国游客，不会中文）。
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# 语言常量
# --------------------------------------------------------------------------- #

LANG_EN = "en"
LANG_ZH = "zh"
LANG_FR = "fr"
LANG_JA = "ja"
LANG_KO = "ko"

SUPPORTED_LANGUAGES: tuple[str, ...] = (LANG_EN, LANG_FR, LANG_JA, LANG_KO, LANG_ZH)

# 界面文案完整支持的语言；其余语言回退英文
_UI_FULL_LANGS = (LANG_EN, LANG_ZH)

#: 语言代码 -> 界面显示名称（各语言下均显示自身名称）
LANGUAGE_NAMES: dict[str, str] = {
    LANG_EN: "English",
    LANG_FR: "Français",
    LANG_JA: "日本語",
    LANG_KO: "한국어",
    LANG_ZH: "中文",
}

#: 语言代码 -> LLM 可理解的输出语言指令
_OUTPUT_LANGUAGE_NAMES: dict[str, str] = {
    LANG_EN: "English（英语）",
    LANG_FR: "French（法语）",
    LANG_JA: "Japanese（日语）",
    LANG_KO: "Korean（韩语）",
    LANG_ZH: "中文",
}

# --------------------------------------------------------------------------- #
# 界面文案字典：key -> {zh, en}
# fr/ja/ko 未单独维护，回退 en（见 t() 实现）
# --------------------------------------------------------------------------- #

UI_TEXT: dict[str, dict[str, str]] = {
    # ---- 顶部与应用 ----
    "app_title": {"zh": "🧳 AI入境旅游搭子", "en": "🧳 AI China Travel Buddy"},
    "app_slogan": {"zh": "智能旅行规划助手", "en": "Smart Trip Planner"},

    # ---- 身份采集页 ----
    "identity_greeting": {
        "zh": "👋 欢迎！让我们了解你的旅行计划",
        "en": "👋 Welcome! Let's get to know your trip",
    },
    "identity_sub": {
        "zh": "为了给你定制专属的来华旅行方案，请回答以下几个问题：",
        "en": "To build your personalized China trip plan, please answer a few questions:",
    },
    "identity_lang_label": {
        "zh": "🌐 界面与回答语言（Interface & answer language）",
        "en": "🌐 Interface & answer language",
    },
    "identity_q_nationality": {
        "zh": "1. 你的国籍是？",
        "en": "1. What is your nationality?",
    },
    "identity_q_nationality_ph": {
        "zh": "例如：美国、英国、日本",
        "en": "e.g., United States, United Kingdom, Japan",
    },
    "identity_q_arrival": {
        "zh": "2. 预计到达日期？",
        "en": "2. When do you plan to arrive?",
    },
    "identity_q_arrival_ph": {
        "zh": "例如：下周一、2026-10-01",
        "en": "e.g., next Monday, 2026-10-01",
    },
    "identity_q_chinese": {
        "zh": "3. 你的中文水平？",
        "en": "3. How well do you speak Chinese?",
    },
    "identity_q_purpose": {
        "zh": "4. 旅行目的？",
        "en": "4. What is the purpose of your visit?",
    },
    "identity_submit": {
        "zh": "✅ 确认，开始规划行程",
        "en": "✅ Confirm & Start Planning",
    },
    "identity_warning": {
        "zh": "请填写完整信息后再提交。",
        "en": "Please fill in all required fields to continue.",
    },

    # ---- 中文水平选项 ----
    "cl_none": {"zh": "完全不会", "en": "None"},
    "cl_basic": {"zh": "基础（能听懂简单词汇）", "en": "Basic (simple words)"},
    "cl_conversational": {"zh": "会话级（日常交流）", "en": "Conversational"},
    "cl_fluent": {"zh": "流利", "en": "Fluent"},

    # ---- 旅行目的选项 ----
    "purpose_tourism": {"zh": "旅游", "en": "Tourism"},
    "purpose_business": {"zh": "商务", "en": "Business"},
    "purpose_visit": {"zh": "探亲访友", "en": "Visiting friends/family"},
    "purpose_study": {"zh": "留学/学习", "en": "Study"},
    "purpose_other": {"zh": "其他", "en": "Other"},

    # ---- 城市推荐页 ----
    "city_header_fmt": {
        "zh": "🗺️ {nationality}朋友，想去哪里玩？",
        "en": "🗺️ Hi {nationality}! Where would you like to go?",
    },
    "city_caption_fmt": {
        "zh": "到达日期：{arrival} | 中文水平：{level}",
        "en": "Arrival: {arrival} | Chinese level: {level}",
    },
    "city_select": {
        "zh": "选择一个城市",
        "en": "Choose a city",
    },
    "city_no_data": {
        "zh": "暂无城市数据，请联系管理员添加知识库。",
        "en": "No city data available yet. Please contact the administrator.",
    },
    "city_checklist_btn": {
        "zh": "🧳 生成我的行前准备 Checklist",
        "en": "🧳 Generate my Before-Arrival Checklist",
    },
    "city_checklist_spinner": {
        "zh": "正在生成行前清单...",
        "en": "Generating your checklist...",
    },
    "city_checklist_done": {
        "zh": "你的行前准备清单已生成：",
        "en": "Here is your Before-Arrival Checklist:",
    },
    "city_attractions_title": {
        "zh": "🏛️ 推荐景点",
        "en": "🏛️ Recommended Attractions",
    },
    "city_attractions_info": {
        "zh": "每个景点显示护照可行性标签：✅可订 / ⚠️需人工 / ❌不可",
        "en": "Each attraction shows a passport availability tag: ✅ Bookable / ⚠️ Manual / ❌ Not available",
    },
    "city_faq_title": {
        "zh": "💬 有问题？随时问我",
        "en": "💬 Questions? Ask me anytime",
    },
    "city_faq_ph": {
        "zh": "输入你的问题",
        "en": "Type your question",
    },

    # ---- 攻略页 ----
    "guide_header_fmt": {
        "zh": "📍 {name} 详细攻略",
        "en": "📍 {name} - Detailed Guide",
    },
    "guide_bookability": {
        "zh": "🔍 预订可行性诊断",
        "en": "🔍 Booking Availability Check",
    },
    "guide_phone_checkbox": {
        "zh": "我有中国手机号（可用于接收验证码）",
        "en": "I have a Chinese phone number (for SMS verification)",
    },
    "guide_passport_info": {
        "zh": "🛂 护照预订信息",
        "en": "🛂 Passport Booking Info",
    },
    "guide_entry_info": {
        "zh": "📍 入园信息",
        "en": "📍 Entry Information",
    },
    "guide_tips": {
        "zh": "**实用提示：**",
        "en": "**Useful tips:**",
    },
    "guide_alternatives": {
        "zh": "🔄 备选景点",
        "en": "🔄 Alternative Attractions",
    },
    "guide_sources": {
        "zh": "📚 **信息来源：** ",
        "en": "📚 **Sources:** ",
    },
    "guide_updated_fmt": {
        "zh": "🕒 数据更新时间：{time}（信息仅供参考，以官方最新为准）",
        "en": "🕒 Last updated: {time} (For reference only, always check official info)",
    },
    "guide_ai_section": {
        "zh": "🤖 AI 攻略生成",
        "en": "🤖 AI Guide Generation",
    },
    "guide_deepseek_btn": {
        "zh": "🧠 用 DeepSeek 生成结构化攻略",
        "en": "🧠 Generate structured guide (DeepSeek)",
    },
    "guide_deepseek_card_btn": {
        "zh": "🈯 用 DeepSeek 生成结构化攻略卡片",
        "en": "🈯 Generate guide card (DeepSeek)",
    },
    "guide_back_btn": {
        "zh": "← 返回景点列表",
        "en": "← Back to attractions",
    },
    # 攻略卡片小节标题
    "guide_section_booking": {
        "zh": "### 🎫 购票/预约",
        "en": "### 🎫 Booking / Tickets",
    },
    "guide_section_transport": {
        "zh": "### 🚇 交通",
        "en": "### 🚇 Transportation",
    },
    "guide_section_alternatives": {
        "zh": "### 🔄 备选景点",
        "en": "### 🔄 Alternative Attractions",
    },
    "guide_section_emergency": {
        "zh": "### 🆘 应急帮助",
        "en": "### 🆘 Emergency Help",
    },
    "guide_source_official": {
        "zh": "官方来源：",
        "en": "Official source: ",
    },
    "guide_eta_fmt": {
        "zh": "预计耗时：{time}",
        "en": "Estimated time: {time}",
    },
    "guide_no_alternatives": {
        "zh": "暂无备选景点。",
        "en": "No alternative attractions.",
    },
    "guide_basis": {"zh": "判断依据：{reason}", "en": "Based on: {reason}"},
    "guide_action": {"zh": "建议操作：{action}", "en": "Recommended: {action}"},
    "guide_online": {"zh": "在线预订", "en": "Online booking"},
    "guide_passport_ok": {"zh": "接受护照", "en": "Passport accepted"},
    "guide_cn_phone": {"zh": "需中国手机号", "en": "CN phone required"},
    "guide_ticket_price": {"zh": "门票", "en": "Ticket"},
    "guide_platform_fmt": {"zh": "**预订平台：** {platform}", "en": "**Booking platform:** {platform}"},
    "guide_advance_fmt": {"zh": "**建议提前：** {days} 天预订", "en": "**Book ahead:** {days} days"},
    "guide_price_notes_fmt": {"zh": "**价格说明：** {notes}", "en": "**Price: ** {notes}"},
    "guide_address_fmt": {"zh": "**地址：** {addr}", "en": "**Address:** {addr}"},
    "guide_metro_fmt": {"zh": "**最近地铁：** {metro}", "en": "**Nearest metro:** {metro}"},
    "guide_hours_fmt": {"zh": "**开放时间：** {hours}", "en": "**Opening hours:** {hours}"},
    "guide_entry_fmt": {"zh": "**入园方式：** {entry}", "en": "**Entry:** {entry}"},

    # ---- 景点卡片（cards.py）----
    "card_ticket": {"zh": "门票", "en": "Ticket"},
    "card_passport_ok": {"zh": "接受护照", "en": "Passport OK"},
    "card_phone_req": {"zh": "需中国手机号", "en": "CN phone needed"},
    "card_advance_days_fmt": {"zh": "{days}天", "en": "{days} days"},
    "card_advance_booking": {"zh": "提前预订", "en": "Book ahead"},
    "card_guide_btn": {"zh": "📋 生成攻略", "en": "📋 Guide"},
    "card_yes": {"zh": "是", "en": "Yes"},
    "card_no": {"zh": "否", "en": "No"},
    "card_city_hdr": {"zh": "🏙️ {name} ({name_en})", "en": "🏙️ {name} ({name_en})"},
    "card_highlights": {"zh": "✨ 亮点", "en": "✨ Highlights"},
    "card_transport": {"zh": "🚆 交通", "en": "🚆 Transport"},
    "card_airport": {"zh": "机场", "en": "Airport"},
    "card_airport_to_city": {"zh": "机场→市区", "en": "Airport to city"},
    "card_city_transport": {"zh": "市内交通", "en": "City transport"},
    "card_tips_fmt": {"zh": "💡 **提示：** {tips}", "en": "💡 **Tips:** {tips}"},
    "card_notes": {"zh": "⚠️ 注意事项", "en": "⚠️ Notes"},
    "card_apps": {"zh": "📱 推荐 App", "en": "📱 Recommended Apps"},
    "card_required": {"zh": "🔴 必需", "en": "🔴 Required"},
    "card_optional": {"zh": "⚪ 可选", "en": "⚪ Optional"},
    "card_essentials_title": {
        "zh": "📶 落地必备指南",
        "en": "📶 Essential On-Arrival Guide",
    },
    "card_essentials_expander": {
        "zh": "点击展开全部落地指南",
        "en": "Expand all on-arrival guides",
    },
    "card_quick_questions": {
        "zh": "💬 途中高频问题（点一下直接问）",
        "en": "💬 Frequent questions (tap to ask)",
    },
    "card_sim": {"zh": "📶 SIM 卡 / 网络", "en": "📶 SIM / Network"},
    "card_payment": {"zh": "💰 支付方式", "en": "💰 Payment"},
    "card_hotel": {"zh": "🏨 酒店预订", "en": "🏨 Hotel booking"},
    "card_ride": {"zh": "🚕 打车 / 网约车", "en": "🚕 Ride-hailing"},
    "card_registration": {"zh": "🛂 公安住宿登记", "en": "🛂 Police registration"},
    "card_public_transport": {"zh": "🚇 公共交通购票", "en": "🚇 Public transit tickets"},
    "card_guide_fallback_title": {
        "zh": "暂时无法生成完整攻略",
        "en": "Full guide temporarily unavailable",
    },
    "card_guide_fallback_msg": {
        "zh": "AI服务暂时不可用，请稍后重试。",
        "en": "AI service is temporarily unavailable. Please retry later.",
    },
    "card_destination": {"zh": "**目的地**：{text}", "en": "**Destination**: {text}"},
    # ---- 快捷问题英文文案（faq_kb id -> en）----
    "quickq_hotel_refuse": {
        "zh": "酒店说不能接外籍护照怎么办",
        "en": "Hotel refuses foreign passport",
    },
    "quickq_metro_ticket": {
        "zh": "地铁怎么用护照买票",
        "en": "Metro ticket with passport",
    },
    "quickq_network_down": {
        "zh": "网络断了怎么办",
        "en": "No network / SIM issues",
    },
    "quickq_payment_fail": {
        "zh": "支付宝绑卡失败了怎么办",
        "en": "Alipay card binding failed",
    },
    "quickq_police_registration": {
        "zh": "公安住宿登记怎么办",
        "en": "Police registration",
    },
    "quickq_train_ticket": {
        "zh": "高铁票怎么用护照买",
        "en": "Train ticket with passport",
    },

    # ---- 途中求助页 ----
    "chat_title": {
        "zh": "🆘 途中求助",
        "en": "🆘 On-the-Go Help",
    },
    "chat_caption": {
        "zh": "任何途中问题（支付失败 / 酒店拒外宾 / 找不到路 / 网络异常）都可随时提问 —— 不是静态攻略，是动态对话。",
        "en": (
            "Ask about any on-the-go issue (payment failure / hotel refusal / "
            "getting lost / no network) — this is a live conversation, not a static guide."
        ),
    },
    "chat_quick_title": {
        "zh": "💬 途中高频问题（点一下直接问）",
        "en": "💬 Frequent on-the-go questions (tap to ask)",
    },
    "chat_input": {
        "zh": "输入你的问题，例如：支付宝绑卡失败了怎么办？",
        "en": "Type your question, e.g., Alipay card binding failed, what to do?",
    },
    "chat_llm_fail": {
        "zh": "⚠️ 调用 AI 失败：{error}。请稍后重试，或直接提问酒店/平台客服。",
        "en": "⚠️ AI call failed: {error}. Please retry later or ask hotel/platform support directly.",
    },

    # ---- 页面底部合规（Day 8-9: 合规与免责表述）----
    "footer_disclaimer_title": {
        "zh": "🛡️ 合规与免责声明",
        "en": "🛡️ Compliance & Disclaimer",
    },
    "footer_disclaimer_body": {
        "zh": (
            "本工具提供的信息仅供参考，不构成任何承诺或法律建议；购票、预约、入园、支付等"
            "关键信息请以官方最新发布为准。AI 生成内容可能存在偏差，请结合官方渠道核实。"
        ),
        "en": (
            "This tool provides information for reference only and does not constitute "
            "a commitment or legal advice. For tickets, reservations, entry and payment, "
            "always check the latest official information. AI-generated content may "
            "contain inaccuracies — please verify via official channels."
        ),
    },
    "footer_source_note": {
        "zh": "信息来源：知识库已标注各条目的来源链接与更新时间，详见各页「信息来源」标注。",
        "en": "Sources: each knowledge-base item is annotated with its source link and "
        "update time; see the 'Sources' notes on each page.",
    },
    "footer_privacy": {
        "zh": "🔒 隐私说明：您输入的身份信息仅在本会话内用于生成个性化内容，不会被保存或用于其他用途。",
        "en": "🔒 Privacy: the identity info you enter is used only within this session "
        "to personalize content; it is not stored or used for any other purpose.",
    },

    # ---- 侧边栏 ----
    "sidebar_identity": {
        "zh": "**当前游客信息：**",
        "en": "**Current traveler info:**",
    },
    "sidebar_api_ready": {
        "zh": "✅ 已配置",
        "en": "✅ Configured",
    },
    "sidebar_api_missing": {
        "zh": "⚠️ 未配置 .env",
        "en": "⚠️ .env not configured",
    },
    "sidebar_nav_identity": {
        "zh": "🏠 身份采集",
        "en": "🏠 Identity",
    },
    "sidebar_nav_city": {
        "zh": "🗺️ 城市推荐",
        "en": "🗺️ City",
    },
    "sidebar_nav_chat": {
        "zh": "🆘 途中求助",
        "en": "🆘 On-the-Go Help",
    },
    "sidebar_nav_team": {
        "zh": "👥 团队协作",
        "en": "👥 Team",
    },
}


# --------------------------------------------------------------------------- #
# 工具函数
# --------------------------------------------------------------------------- #


def normalize_lang(lang: str | None) -> str:
    """规范化语言代码；未知 / 缺失一律回退 en。"""
    if lang in SUPPORTED_LANGUAGES:
        return lang
    return LANG_EN


def language_display_name(lang: str | None) -> str:
    """语言代码 -> 界面显示名称。"""
    return LANGUAGE_NAMES.get(normalize_lang(lang), LANGUAGE_NAMES[LANG_EN])


def output_language(lang: str | None) -> str:
    """语言代码 -> LLM 输出语言指令（注入 prompt 用）。

    中文游客输出中文，其余一律按偏好语言英文名输出，
    保证「完全不会中文」的游客看到的内容真的看得懂。
    """
    return _OUTPUT_LANGUAGE_NAMES[normalize_lang(lang)]


def t(key: str, lang: str | None = LANG_EN, **kwargs) -> str:
    """按语言取界面文案；fallback 顺序：zh/en -> en。缺失 key 返回 key 本身。"""
    lang = normalize_lang(lang)
    entry = UI_TEXT.get(key)
    if not entry:
        return key
    if lang in _UI_FULL_LANGS and lang in entry and entry[lang]:
        text = entry[lang]
    else:
        text = entry.get(LANG_EN) or entry.get(LANG_ZH) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


def faq_answer(faq_id: str, lang: str | None = LANG_EN) -> str:
    """按语言取 FAQ 静态答案。

    - 中文（zh）：返回空串，由调用方直接使用 faq_kb 的中文 answer。
    - 其他语言：返回 FAQ_ANSWER_EN 中的英文翻译；缺失回退空串（走 LLM 兜底）。
    """
    lang = normalize_lang(lang)
    if lang == LANG_ZH:
        return ""
    return FAQ_ANSWER_EN.get(faq_id, "")


# --------------------------------------------------------------------------- #
# 本地 FAQ 答案英文翻译（用于「完全不会中文」游客的口径校对与静态展示）
# --------------------------------------------------------------------------- #

FAQ_ANSWER_EN: dict[str, str] = {
    "hotel_refuse": (
        "1) First confirm whether the hotel is licensed to host foreigners — some "
        "guesthouses/small hotels have no foreign-guest license.\n"
        "2) Re-book on Ctrip/Booking using the 'accepts foreign guests' filter "
        "(international chains generally accept all passports).\n"
        "3) If your booking is rejected or cannot be honored, contact the booking "
        "platform's support, or call the 12345 civic hotline for help.\n"
        "Source: hotel foreign-guest regulations (verified 2026-09)"
    ),
    "metro_ticket": (
        "1) Most metro station ticket vending machines accept passports (choose "
        "'Passport' as ID type).\n"
        "2) You can also download local apps such as Yitongxing / Beijing Yikatong, "
        "bind an international card, and scan QR codes to enter.\n"
        "3) Major stations have manual windows — ask staff if you cannot find a "
        "machine (show the Chinese prompt on this page).\n"
        "Source: Beijing/Shanghai/Xi'an metro station info (verified 2026-09)"
    ),
    "network_down": (
        "1) Buy a China eSIM before departure (Airalo / Holafly) — internet works "
        "right after landing.\n"
        "2) Or buy a local SIM at the airport arrivals hall (passport required).\n"
        "3) For temporary outages, ask shops for WiFi (some need SMS verification; "
        "a registered passport SIM can receive it).\n"
        "4) Save key offline info (guide cards, emergency phrases) to your photo "
        "album before you go.\n"
        "Source: travel service provider info (verified 2026-09)"
    ),
    "payment_fail": (
        "1) Diagnose: is international online payment enabled on your card? Do the "
        "name on the card and your ID match? Is your network being interfered?\n"
        "2) Retry with a Visa/Mastercard, or enable Alipay Tour Pass (bind foreign "
        "card to a prepaid wallet; passport + face verification; limit ~¥2000).\n"
        "3) Fallback: pay at convenience stores / Starbucks / large supermarkets "
        "that accept foreign cards; airport ATMs dispense cash; cash is still "
        "accepted by most merchants.\n"
        "Source: Alipay/WeChat foreign-card policy (verified 2026-09)"
    ),
    "police_registration": (
        "1) At regular hotels, the front desk registers you with your passport "
        "automatically — no need to visit a police station.\n"
        "2) For guesthouses/short-term rentals, first confirm the host has a "
        "foreign-guest license and can register you.\n"
        "3) If no one can do it, ask the local community police post or hotel desk "
        "— never skip it silently.\n"
        "Source: accommodation registration rules (verified 2026-09)"
    ),
    "attraction_reserve": (
        "1) Prefer the platforms marked ✅ in the knowledge base (official site / "
        "Ctrip) that accept passport booking online.\n"
        "2) Most attractions support passport real-name reservation — choose "
        "'Passport' as the ID type.\n"
        "3) If fully booked, check the 'Alternative Attractions' in the guide card "
        "for options that need no reservation or accept passports.\n"
        "4) As a last resort, go to the on-site manual window (some sites keep "
        "same-day tickets).\n"
        "Source: attraction ticketing policy (verified 2026-09)"
    ),
    "taxi_ride": (
        "1) Didi has an English interface; after binding a foreign card you can "
        "hail a ride. AMap also supports ride-hailing.\n"
        "2) Street taxis accept cash or QR payment (online hailing reduces the "
        "chance of cancellation).\n"
        "3) If you cannot find a ride, the metro is the most reliable fallback — "
        "check the route with an app and transfer.\n"
        "Source: ride-hailing platform info (verified 2026-09)"
    ),
    "train_ticket": (
        "1) 12306 App/website supports passport registration and ticket purchase "
        "(choose 'Passport' as ID type).\n"
        "2) Collect tickets at the station's manual window (bring your passport); "
        "some self-service machines also support it.\n"
        "3) For domestic flights: passport works for booking and boarding; the "
        "international/manual counter is more reliable.\n"
        "Source: 12306 & airline policy (verified 2026-09)"
    ),
    "diet": (
        "1) Search Dianping / Xiaohongshu for 'halal / vegetarian' keywords and "
        "read recent local reviews.\n"
        "2) Western chains (KFC / McDonald's) and international hotel restaurants "
        "are the safest fallbacks.\n"
        "3) Allergies: save 'I am allergic to X, please avoid it' in Chinese on "
        "your phone and show it when ordering.\n"
        "Source: review platform info (verified 2026-09)"
    ),
    "translation": (
        "1) Download Baidu Translate / Youdao Translate — photo translation works "
        "for menus and signs.\n"
        "2) Screenshot the 'Emergency Phrases' section of guide cards and show "
        "them to staff directly.\n"
        "3) Major attractions and metro stations have English signage; metro "
        "announcements include English.\n"
        "Source: translation tools & city signage (verified 2026-09)"
    ),
}

