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
    "city_checklist_empty": {
        "zh": "AI 暂时没有生成内容，请稍后重试。",
        "en": "AI returned no content. Please try again.",
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
    "card_city_hdr": {"zh": "🏙️ {name}", "en": "🏙️ {name}"},
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


def status_label(status: str, lang: str | None = LANG_EN) -> str:
    """把景点的规范状态枚举（✅ 可订 / ⚠️ 需人工 / ❌ 不可）按语言转为展示标签。

    状态枚举保留原始值用于配色映射，展示时用本函数取词。
    """
    lang = normalize_lang(lang)
    mapping = {
        "✅ 可订": {"zh": "✅ 可订", "en": "✅ Bookable online", "ja": "✅ 予約可"},
        "⚠️ 需人工": {"zh": "⚠️ 需人工", "en": "⚠️ Manual required", "ja": "⚠️ 要確認"},
        "❌ 不可": {"zh": "❌ 不可", "en": "❌ Not available", "ja": "❌ 不可"},
    }
    entry = mapping.get(status)
    if not entry:
        return status
    return entry.get(lang) or entry["en"]


#: 高德天气常见词 -> 各语言文案（仅用于展示层，不改变高德原始返回数据）
_WEATHER_TERMS: dict[str, dict[str, str]] = {
    "晴": {"zh": "晴", "en": "Clear", "ja": "晴れ"},
    "多云": {"zh": "多云", "en": "Cloudy", "ja": "曇り"},
    "阴": {"zh": "阴", "en": "Overcast", "ja": "曇り"},
    "小雨": {"zh": "小雨", "en": "Light rain", "ja": "小雨"},
    "中雨": {"zh": "中雨", "en": "Moderate rain", "ja": "雨"},
    "大雨": {"zh": "大雨", "en": "Heavy rain", "ja": "大雨"},
    "暴雨": {"zh": "暴雨", "en": "Torrential rain", "ja": "豪雨"},
    "雷阵雨": {"zh": "雷阵雨", "en": "Thunderstorms", "ja": "雷雨"},
    "雨夹雪": {"zh": "雨夹雪", "en": "Sleet", "ja": "みぞれ"},
    "小雪": {"zh": "小雪", "en": "Light snow", "ja": "小雪"},
    "中雪": {"zh": "中雪", "en": "Moderate snow", "ja": "雪"},
    "大雪": {"zh": "大雪", "en": "Heavy snow", "ja": "大雪"},
    "雾": {"zh": "雾", "en": "Fog", "ja": "霧"},
    "霾": {"zh": "霾", "en": "Haze", "ja": "スモッグ"},
    "浮尘": {"zh": "浮尘", "en": "Dust", "ja": "砂塵"},
    "北风": {"zh": "北风", "en": "North wind", "ja": "北風"},
    "南风": {"zh": "南风", "en": "South wind", "ja": "南風"},
    "东风": {"zh": "东风", "en": "East wind", "ja": "東風"},
    "西风": {"zh": "西风", "en": "West wind", "ja": "西風"},
    "东北风": {"zh": "东北风", "en": "Northeast wind", "ja": "北東の風"},
    "西北风": {"zh": "西北风", "en": "Northwest wind", "ja": "北西の風"},
    "东南风": {"zh": "东南风", "en": "Southeast wind", "ja": "南東の風"},
    "西南风": {"zh": "西南风", "en": "Southwest wind", "ja": "南西の風"},
}


def weather_term(term: str, lang: str | None = LANG_EN) -> str:
    """把高德天气词（晴/多云/北风等）按语言转为展示文案；未收录的词原样返回。"""
    lang = normalize_lang(lang)
    entry = _WEATHER_TERMS.get(term)
    if not entry:
        return term
    return entry.get(lang) or entry.get("en", term)


def t(key: str, lang: str | None = LANG_EN, **kwargs) -> str:
    """按语言取界面文案；日文走 UI_TEXT_JA，其余 fallback 顺序：zh/en -> en。

    缺失 key 返回 key 本身，绝不抛 KeyError。
    """
    lang = normalize_lang(lang)
    if lang == LANG_JA and key in UI_TEXT_JA:
        text = UI_TEXT_JA[key]
    else:
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
    - 日文（ja）：返回 FAQ_ANSWER_JA 中的日文翻译；缺失回退英文。
    - 其他语言：返回 FAQ_ANSWER_EN 中的英文翻译；缺失回退空串（走 LLM 兜底）。
    """
    lang = normalize_lang(lang)
    if lang == LANG_ZH:
        return ""
    if lang == LANG_JA:
        return FAQ_ANSWER_JA.get(faq_id, FAQ_ANSWER_EN.get(faq_id, ""))
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



# --------------------------------------------------------------------------- #
# Day 9 行程规划页（页面三）文案 —— feat/day9-trip-planner 分支新增
# --------------------------------------------------------------------------- #
UI_TEXT.update({
    "sidebar_nav_planner": {"zh": "行程规划", "en": "Trip Planner"},
    "planner_title": {"zh": "行程规划 · 天气与人流智能攻略", "en": "Trip Planner · Weather & Crowd-smart Itinerary"},
    "planner_caption": {
        "zh": "选日期、勾选景点，查看预估天气/人流/排队时间，一键生成按时间排列的一日或几日游玩攻略。",
        "en": "Pick a date, select attractions, check estimated weather/crowd/queue times, then generate a time-ordered day-by-day plan.",
    },
    "planner_need_city": {"zh": "请先在「城市推荐」里选择一个城市。", "en": "Please choose a city on the City page first."},
    "planner_go_city": {"zh": "去选择城市", "en": "Go to City page"},
    "planner_date": {"zh": "出游日期", "en": "Visit date"},
    "planner_days": {"zh": "行程天数", "en": "Number of days"},
    "planner_select_title": {"zh": "勾选想去的景点", "en": "Select attractions"},
    "planner_select_empty": {"zh": "至少勾选一个景点。", "en": "Select at least one attraction."},
    "planner_weather_btn": {"zh": "查看天气与人流预估", "en": "Check weather & crowd estimates"},
    "planner_weather_hint": {
        "zh": "点击上方按钮加载高德天气预报（未来 4 天，真实数据）。",
        "en": "Click the button above to load the Amap weather forecast (next 4 days, real data).",
    },
    "planner_weather_fail": {"zh": "天气查询失败，仅显示人流预估。", "en": "Weather lookup failed — showing crowd estimates only."},
    "planner_forecast_title": {"zh": "天气预报（高德数据，未来 4 天）", "en": "Weather forecast (Amap, next 4 days)"},
    "planner_weather_covered": {"zh": "✅ 你的出游日期在预报范围内，天气为真实预报。", "en": "✅ Your visit date is covered by the real forecast."},
    "planner_weather_outofrange": {
        "zh": "ℹ️ 部分或全部出游日期暂无实际预报，请在出发前重新查询。",
        "en": "ℹ️ Some or all trip dates have no actual forecast. Check again before departure.",
    },
    "planner_crowd_title": {"zh": "人流 / 排队 / 游玩时长预估", "en": "Estimated crowd / queue / visit duration"},
    "planner_col_attr": {"zh": "景点", "en": "Attraction"},
    "planner_col_duration": {"zh": "建议时长", "en": "Est. duration"},
    "planner_col_crowd": {"zh": "人流", "en": "Crowd"},
    "planner_col_queue": {"zh": "预估排队", "en": "Est. queue"},
    "planner_col_window": {"zh": "建议时段", "en": "Best window"},
    "planner_estimate_note": {
        "zh": "⚠️ 人流/排队为按日期类型（节假日/周末/工作日）与景点热度的启发式预估，非实时数据。",
        "en": "⚠️ Crowd/queue values are heuristic estimates based on date type (holiday/weekend/weekday) and attraction popularity — not real-time data.",
    },
    "planner_gen_btn": {"zh": "生成一日/多日游玩攻略", "en": "Generate day-by-day itinerary"},
    "planner_gen_spinner": {"zh": "正在生成攻略...", "en": "Generating your itinerary..."},
    "planner_gen_done": {"zh": "✅ 攻略生成完成！", "en": "✅ Itinerary ready!"},
    "planner_group_note": {
        "zh": "已按「每天游玩约 6.5 小时」自动把景点分配到各天，顺序可在攻略中微调。",
        "en": "Attractions are grouped into days at ~6.5 hours of visiting per day; the order can be fine-tuned in the itinerary.",
    },
})

# --------------------------------------------------------------------------- #
# 补充词条：修复此前「写死中文/英文」的 UI 文案（Day 9 多语言整改）
# --------------------------------------------------------------------------- #
UI_TEXT.update({
    "city_load_failed": {
        "zh": "无法加载 {city} 的数据。",
        "en": "Failed to load data for {city}.",
    },
    "guide_ready": {"zh": "✅ 攻略已生成！", "en": "✅ Guide ready!"},
    "guide_gen_failed": {
        "zh": "攻略生成失败，请检查 API 配置。",
        "en": "Guide generation failed. Check API config.",
    },
    "ai_label": {"zh": "**AI：**", "en": "**AI:**"},
    "status_unknown": {"zh": "未知", "en": "Unknown"},
    "identity_nationality": {"zh": "国籍", "en": "Nationality"},
    "identity_arrival": {"zh": "到达日期", "en": "Arrival date"},
    "identity_chinese_level": {"zh": "中文水平", "en": "Chinese level"},
    "identity_purpose": {"zh": "旅行目的", "en": "Purpose"},
    "identity_language": {"zh": "界面语言", "en": "Language"},
    "card_essentials_caption": {
        "zh": "基于《外国游客来华旅行痛点调研》：SIM卡 4.27 / 支付 4.20 / 酒店 4.17 / 护照购票 4.17 / 打车 4.17 / 公安登记 3.93",
        "en": "Based on the Foreign Visitors Pain-Point Survey: SIM 4.27 / Payment 4.20 / Hotel 4.17 / Passport ticket 4.17 / Taxi 4.17 / Police registration 3.93",
    },
})


# --------------------------------------------------------------------------- #
# 日文 UI 文案（key -> 日本語）。t() 在 lang=="ja" 时优先取此表。
# fr/ko 仍按项目既有设计回退英文，不在本次改动范围内。
# --------------------------------------------------------------------------- #
UI_TEXT_JA: dict[str, str] = {
    # ---- 顶部与应用 ----
    "app_title": "🧳 AI中国旅行アシスタント",
    "app_slogan": "スマート旅行プランナー",
    # ---- 身份采集页 ----
    "identity_greeting": "👋 ようこそ！あなたの旅行プランについて教えてください",
    "identity_sub": "あなた専用の中国旅行プランを作るために、いくつか質問に答えてください：",
    "identity_lang_label": "🌐 画面・回答の言語",
    "identity_q_nationality": "1. 国籍は？",
    "identity_q_nationality_ph": "例：アメリカ、イギリス、日本",
    "identity_q_arrival": "2. 到着予定日は？",
    "identity_q_arrival_ph": "例：来週の月曜日、2026-10-01",
    "identity_q_chinese": "3. 中国語レベルは？",
    "identity_q_purpose": "4. 旅行の目的は？",
    "identity_submit": "✅ 確認して旅程作成を開始",
    "identity_warning": "続行するにはすべての必須項目を入力してください。",
    "cl_none": "なし",
    "cl_basic": "基礎（簡単な単語）",
    "cl_conversational": "会話レベル",
    "cl_fluent": "流暢",
    "purpose_tourism": "観光",
    "purpose_business": "ビジネス",
    "purpose_visit": "親族・友人訪問",
    "purpose_study": "留学/学習",
    "purpose_other": "その他",
    # ---- 城市推荐页 ----
    "city_header_fmt": "🗺️ {nationality}さん、どこへ行きますか？",
    "city_caption_fmt": "到着：{arrival} | 中国語レベル：{level}",
    "city_select": "都市を選択",
    "city_no_data": "都市データがありません。管理者にナレッジベースの追加を依頼してください。",
    "city_checklist_btn": "🧳 出発前チェックリストを作成",
    "city_checklist_spinner": "チェックリストを作成中...",
    "city_checklist_done": "出発前チェックリストができました：",
    "city_checklist_empty": "AIがコンテンツを返しませんでした。もう一度お試しください。",
    "city_attractions_title": "🏛️ おすすめ観光地",
    "city_attractions_info": "各観光地にパスポート可否タグを表示：✅予約可 / ⚠️要確認 / ❌不可",
    "city_faq_title": "💬 質問はありますか？いつでも聞いてください",
    "city_faq_ph": "質問を入力",
    # ---- 攻略页 ----
    "guide_header_fmt": "📍 {name} 詳細ガイド",
    "guide_bookability": "🔍 予約可否診断",
    "guide_phone_checkbox": "中国の携帯番号を持っている（SMS認証用）",
    "guide_passport_info": "🛂 パスポート予約情報",
    "guide_entry_info": "📍 入場情報",
    "guide_tips": "**お役立ち情報：**",
    "guide_alternatives": "🔄 代替観光地",
    "guide_sources": "📚 **情報源：** ",
    "guide_updated_fmt": "🕒 最終更新：{time}（参考情報です。公式情報を必ずご確認ください）",
    "guide_ai_section": "🤖 AIガイド生成",
    "guide_deepseek_btn": "🧠 DeepSeekで構造化ガイドを生成",
    "guide_deepseek_card_btn": "🈯 DeepSeekでガイドカードを生成",
    "guide_back_btn": "← 観光地一覧に戻る",
    "guide_section_booking": "### 🎫 チケット/予約",
    "guide_section_transport": "### 🚇 交通",
    "guide_section_alternatives": "### 🔄 代替観光地",
    "guide_section_emergency": "### 🆘 緊急時の助け",
    "guide_source_official": "公式情報源：",
    "guide_eta_fmt": "所要時間：{time}",
    "guide_no_alternatives": "代替観光地はありません。",
    "guide_basis": "判断根拠：{reason}",
    "guide_action": "推奨操作：{action}",
    "guide_online": "オンライン予約",
    "guide_passport_ok": "パスポート可",
    "guide_cn_phone": "中国の携帯番号が必要",
    "guide_ticket_price": "チケット",
    "guide_platform_fmt": "**予約プラットフォーム：** {platform}",
    "guide_advance_fmt": "**事前予約：** {days}日前",
    "guide_price_notes_fmt": "**価格：** {notes}",
    "guide_address_fmt": "**住所：** {addr}",
    "guide_metro_fmt": "**最寄り地下鉄：** {metro}",
    "guide_hours_fmt": "**営業時間：** {hours}",
    "guide_entry_fmt": "**入場方法：** {entry}",
    # ---- 景点卡片 ----
    "card_ticket": "チケット",
    "card_passport_ok": "パスポート可",
    "card_phone_req": "中国の携帯番号が必要",
    "card_advance_days_fmt": "{days}日前",
    "card_advance_booking": "事前予約",
    "card_guide_btn": "📋 ガイド",
    "card_yes": "はい",
    "card_no": "いいえ",
    "card_city_hdr": "🏙️ {name}",
    "card_essentials_caption": "『外国人来中旅行の痛点調査』に基づく：SIM 4.27 / 支払い 4.20 / ホテル 4.17 / パスポート購入 4.17 / タクシー 4.17 / 警察登録 3.93",
    "card_highlights": "✨ ハイライト",
    "card_transport": "🚆 交通",
    "card_airport": "空港",
    "card_airport_to_city": "空港→市内",
    "card_city_transport": "市内交通",
    "card_tips_fmt": "💡 **ヒント：** {tips}",
    "card_notes": "⚠️ 注意事項",
    "card_apps": "📱 おすすめアプリ",
    "card_required": "🔴 必須",
    "card_optional": "⚪ 任意",
    "card_essentials_title": "📶 到着後必須ガイド",
    "card_essentials_expander": "クリックして到着後ガイドをすべて表示",
    "card_quick_questions": "💬 よくある質問（タップして質問）",
    "card_sim": "📶 SIM / ネットワーク",
    "card_payment": "💰 支払い",
    "card_hotel": "🏨 ホテル予約",
    "card_ride": "🚕 配車/タクシー",
    "card_registration": "🛂 警察登録",
    "card_public_transport": "🚇 公共交通のチケット",
    "card_guide_fallback_title": "完全なガイドを一時的に生成できません",
    "card_guide_fallback_msg": "AIサービスが一時的に利用できません。後でもう一度お試しください。",
    "card_destination": "**目的地**：{text}",
    # ---- 快捷问题 ----
    "quickq_hotel_refuse": "ホテルが外国パスポートを拒否",
    "quickq_metro_ticket": "パスポートでの地下鉄チケット購入",
    "quickq_network_down": "ネットワークなし / SIM問題",
    "quickq_payment_fail": "Alipayのカード紐付け失敗",
    "quickq_police_registration": "警察登録",
    "quickq_train_ticket": "パスポートでの電車チケット購入",
    # ---- 途中求助页 ----
    "chat_title": "🆘 旅行中のヘルプ",
    "chat_caption": "旅行中のどんな問題（支払い失敗 / ホテルが外国人を拒否 / 道に迷った / ネットワーク不調）でもいつでも質問できます。静的なガイドではなく、リアルタイムの対話です。",
    "chat_quick_title": "💬 旅行中のよくある質問（タップして質問）",
    "chat_input": "質問を入力してください。例：Alipayのカード紐付けに失敗したら？",
    "chat_llm_fail": "⚠️ AI呼び出し失敗：{error}。後でもう一度お試しください。またはホテル/プラットフォームのサポートに直接お問い合わせください。",
    # ---- 页面底部 ----
    "footer_disclaimer_title": "🛡️ コンプライアンスと免責事項",
    "footer_disclaimer_body": "本ツールの情報は参考用であり、いかなる約束や法的助言を構成するものではありません。チケット・予約・入場・支払いなどの重要な情報は、必ず公式の最新情報をご確認ください。AI生成コンテンツには誤りが含まれる場合があります。公式チャネルでご確認ください。",
    "footer_source_note": "情報源：各ナレッジベース項目に出典リンクと更新日が記載されています。各ページの「情報源」をご覧ください。",
    "footer_privacy": "🔒 プライバシー：入力された身元情報は、本セッション内でパーソナライズされたコンテンツ生成にのみ使用され、保存・他用途利用はされません。",
    # ---- 侧边栏 ----
    "sidebar_identity": "**現在の旅行者情報：**",
    "sidebar_api_ready": "✅ 設定済み",
    "sidebar_api_missing": "⚠️ .env未設定",
    "sidebar_nav_identity": "🏠 プロフィール",
    "sidebar_nav_city": "🗺️ 都市",
    "sidebar_nav_chat": "🆘 旅行中のヘルプ",
    "sidebar_nav_team": "👥 チーム",
    "sidebar_nav_planner": "🗓️ 旅程プランナー",
    # ---- 补充词条 ----
    "city_load_failed": "{city} のデータを読み込めませんでした。",
    "guide_ready": "✅ ガイドの準備ができました！",
    "guide_gen_failed": "ガイドの生成に失敗しました。API設定を確認してください。",
    "ai_label": "**AI：**",
    "status_unknown": "不明",
    "identity_nationality": "国籍",
    "identity_arrival": "到着日",
    "identity_chinese_level": "中国語レベル",
    "identity_purpose": "目的",
    "identity_language": "言語",
    # ---- 行程规划页 ----
    "planner_title": "🗓️ 旅程プランナー · 天気と混雑を考慮したスマート旅程",
    "planner_caption": "日付を選び、観光地をチェックして、天気・混雑・待ち時間の予測を確認し、時間順の日別プランをワンクリックで生成します。",
    "planner_need_city": "まず「都市」ページで都市を選択してください。",
    "planner_go_city": "都市ページへ",
    "planner_date": "訪問日",
    "planner_days": "日数",
    "planner_select_title": "行きたい観光地を選択",
    "planner_select_empty": "少なくとも1つの観光地を選択してください。",
    "planner_weather_btn": "天気と混雑予測を見る",
    "planner_weather_hint": "上のボタンをクリックして高徳天気予報（今後4日間、実データ）を読み込みます。",
    "planner_weather_fail": "天気情報の取得に失敗しました。混雑予測のみ表示します。",
    "planner_forecast_title": "天気予報（高徳データ、今後4日間）",
    "planner_weather_covered": "✅ 訪問日は予報範囲内です。実際の予報です。",
    "planner_weather_outofrange": "ℹ️ 一部または全部の日付に実際の予報がありません。出発前に再確認してください。",
    "planner_crowd_title": "混雑 / 待ち時間 / 滞在時間の予測",
    "planner_col_attr": "観光地",
    "planner_col_duration": "所要時間",
    "planner_col_crowd": "混雑",
    "planner_col_queue": "待ち時間",
    "planner_col_window": "おすすめ時間帯",
    "planner_estimate_note": "⚠️ 混雑/待ち時間は日付タイプ（祝日/週末/平日）と観光地の人気度によるヒューリスティックな推定であり、リアルタイムデータではありません。",
    "planner_gen_btn": "日ごとの旅程を生成",
    "planner_gen_spinner": "旅程を生成中...",
    "planner_gen_done": "✅ 旅程の準備ができました！",
    "planner_group_note": "1日約6.5時間の観光に自動で振り分けました。順序は旅程内で調整できます。",
}


# --------------------------------------------------------------------------- #
# 本地 FAQ 答案日文翻译（用于「不会中文」的日文游客）
# --------------------------------------------------------------------------- #
FAQ_ANSWER_JA: dict[str, str] = {
    "hotel_refuse": (
        "1) まず、そのホテルが外国人の宿泊を受け入れる資格を持っているか確認してください"
        "——一部の民宿・小規模ホテルには外国人受入資格がありません。\n"
        "2) 携程/Bookingで「外国人受入可」フィルターを使い、再予約してください"
        "（国際チェーンホテルは一般的に全パスポートを受け入れます）。\n"
        "3) 予約が拒否された、または履行できない場合は、予約プラットフォームのサポートに"
        "連絡するか、12345市民ホットラインに電話して助けを求めてください。\n"
        "出典：ホテルの外国人宿泊規制（2026-09確認）"
    ),
    "metro_ticket": (
        "1) 多くの地下鉄駅の自動券売機はパスポートでの購入に対応しています"
        "（身分証タイプで「パスポート」を選択）。\n"
        "2) 「億通行 / 北京一卡通」などの現地アプリをダウンロードし、国際カードを"
        "紐付けてQRコードで入場することもできます。\n"
        "3) 主要駅には有人窓口があります。機械が見つからない場合は駅員に尋ねてください"
        "（このページの中国語の表示を見せるとスムーズです）。\n"
        "出典：北京/上海/西安の地下鉄駅情報（2026-09確認）"
    ),
    "network_down": (
        "1) 出発前に中国のeSIM（Airalo / Holafly）を購入しておけば、到着後すぐに"
        "インターネットに接続できます。\n"
        "2) または到着ロビーで現地SIMを購入します（パスポートが必要）。\n"
        "3) 一時的な通信障害の場合は、店舗のWiFiを利用してください（SMS認証が"
        "必要な場合もあり、パスポート登録済みのSIMなら受信できます）。\n"
        "4) 重要なオフライン情報（ガイドカード、緊急フレーズ）を出発前に"
        "写真アルバムに保存しておきましょう。\n"
        "出典：旅行サービスプロバイダー情報（2026-09確認）"
    ),
    "payment_fail": (
        "1) 原因の切り分け：カードの「海外オンライン決済」が有効か、カード名義と"
        "身分証が一致しているか、ネットワークが干渉されていないかを確認。\n"
        "2) Visa/Mastercardで再試行するか、Alipay Tour Pass（海外カードを"
        "プリペイドウォレットに紐付け。パスポート＋顔認証、上限約¥2000）を有効化。\n"
        "3) 回避策：海外カード対応のコンビニ / スターバックス / 大型スーパーで決済、"
        "空港ATMで現金を引き出す。現金は今も多くの店舗で使えます。\n"
        "出典：Alipay/WeChatの海外カードポリシー（2026-09確認）"
    ),
    "police_registration": (
        "1) 通常のホテルでは、フロントがパスポートで自動的に登録してくれるため、"
        "派出所に行く必要はありません。\n"
        "2) 民宿・短期賃貸の場合は、まず宿泊先が外国人受入ライセンスと"
        "登録能力を持っているか確認してください。\n"
        "3) 誰も代行できない場合は、地域の社区派出所またはホテルのフロントに相談し、"
        "黙って登録を省くことは絶対にやめてください。\n"
        "出典：宿泊登記の規定（2026-09確認）"
    ),
    "attraction_reserve": (
        "1) ナレッジベースで✅とマークされたプラットフォーム（公式サイト / 携程）で"
        "パスポートによるオンライン予約を優先してください。\n"
        "2) 多くの観光地はパスポートでの実名予約に対応しています。身分証タイプで"
        "「パスポート」を選択してください。\n"
        "3) 満席の場合は、ガイドカードの「代替観光地」から、予約不要または"
        "パスポート対応の場所を選んでください。\n"
        "4) 最終手段として、現地の有人窓口に行ってください（当日券を残している"
        "観光地もあります）。\n"
        "出典：各観光地のチケットポリシー（2026-09確認）"
    ),
    "taxi_ride": (
        "1) 滴滴には英語インターフェースがあり、海外カードを紐付ければ配車できます。"
        "高徳地図も配車に対応しています。\n"
        "2) 流しのタクシーは現金またはQR決済が可能です（オンライン配車のほうが"
        "キャンセルの心配が少ない）。\n"
        "3) 配車できない場合は、地下鉄が最も確実な代替手段です。アプリでルートを"
        "確認して乗り換えてください。\n"
        "出典：配車プラットフォーム情報（2026-09確認）"
    ),
    "train_ticket": (
        "1) 12306アプリ/サイトはパスポートでの登録・購入に対応しています"
        "（身分証タイプで「パスポート」を選択）。\n"
        "2) チケットは駅の有人窓口で受け取ってください（パスポート原本が必要）。"
        "一部の自動券売機も対応しています。\n"
        "3) 国内線はパスポートで予約・搭乗が可能です。国際/有人カウンターのほうが"
        "確実です。\n"
        "出典：12306および航空会社のポリシー（2026-09確認）"
    ),
    "diet": (
        "1) 大衆点評 / 小紅書で「halal / vegetarian」などのキーワードを検索し、"
        "最近の現地レビューを読んでください。\n"
        "2) 洋食チェーン（KFC / マクドナルド）や国際ホテルのレストランが最も"
        "安全な代替手段です。\n"
        "3) アレルギー：「私はXにアレルギーがあります、避けてください」という"
        "中国語をスマホに保存し、注文時に見せてください。\n"
        "出典：レビュープラットフォーム情報（2026-09確認）"
    ),
    "translation": (
        "1) 百度翻訳 / 有道翻訳をダウンロードすれば、メニューや標識の写真翻訳が"
        "使えます。\n"
        "2) ガイドカードの「緊急フレーズ」をスクリーンショットして、そのまま"
        "スタッフに見せてください。\n"
        "3) 主要な観光地と地下鉄駅には英語の標識があり、地下鉄のアナウンスにも"
        "英語が含まれています。\n"
        "出典：翻訳ツールと都市の標識（2026-09確認）"
    ),
}
