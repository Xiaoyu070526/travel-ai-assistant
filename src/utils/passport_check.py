"""护照可行性校验逻辑

实现 "能订吗" 校验：根据用户身份信息和景点知识库，
判断该景点对该用户是否可预订、是否需要人工辅助、是否不可预订。
"""

from src.utils.content_loader import load_attraction

#: 状态枚举 -> 各语言展示标签（status 保持规范枚举，status_label 按语言展示）
_STATUS_LABEL = {
    "✅ 可订": {"zh": "✅ 可订", "en": "✅ Bookable online", "ja": "✅ 予約可"},
    "⚠️ 需人工": {"zh": "⚠️ 需人工", "en": "⚠️ Manual required", "ja": "⚠️ 要確認"},
    "❌ 不可": {"zh": "❌ 不可", "en": "❌ Not available", "ja": "❌ 不可"},
}


def _msg(lang: str, zh: str, en: str, ja: str) -> str:
    """按语言返回文案：zh/en/ja，其它语言回退英文。"""
    if lang == "zh":
        return zh
    if lang == "ja":
        return ja
    return en


def _status_label(status: str, lang: str) -> str:
    entry = _STATUS_LABEL.get(status)
    if not entry:
        return status
    return entry.get(lang) or entry["en"]


def check_passport_bookability(
    city: str,
    attraction_id: str,
    has_chinese_phone: bool = False,
    lang: str = "zh",
) -> dict:
    """检查景点对护照游客的预订可行性

    Args:
        city: 城市拼音名，如 'beijing'
        attraction_id: 景点ID，如 'gugong'
        has_chinese_phone: 用户是否有中国手机号
        lang: 界面语言（zh / en / ja）

    Returns:
        {
            "status": "✅ 可订" | "⚠️ 需人工" | "❌ 不可",  # 规范枚举（供配色映射）
            "status_label": 按语言展示的状态标签,
            "reason": 原因说明,
            "action": 建议操作,
            "details": 详细判断依据,
        }
    """
    attr = load_attraction(city, attraction_id)
    if not attr:
        return {
            "status": "❌ 不可",
            "status_label": _status_label("❌ 不可", lang),
            "reason": _msg(lang,
                          "知识库中未收录该景点信息",
                          "No info about this attraction in the knowledge base",
                          "ナレッジベースにこの観光地の情報がありません"),
            "action": _msg(lang,
                           "建议去官网确认或咨询客服",
                           "Check the official website or contact customer service",
                           "公式サイトで確認するか、カスタマーサービスに問い合わせてください"),
            "details": _msg(lang, "无数据", "No data", "データなし"),
        }

    p = attr["passport"]

    # 判断逻辑
    if not p["passport_accepted"]:
        return {
            "status": "❌ 不可",
            "status_label": _status_label("❌ 不可", lang),
            "reason": _msg(lang,
                           "该景点不接受护照预订",
                           "This attraction does not accept passport booking",
                           "この観光地はパスポートでの予約を受け付けていません"),
            "action": _msg(lang,
                           "需使用中国身份证，或咨询是否有外籍游客特殊通道",
                           "A Chinese ID is required, or ask whether there is a special channel for foreign visitors",
                           "中国の身分証が必要です。または外国人の特別ルートがあるか確認してください"),
            "details": f"{attr['name']} " + _msg(lang,
                                                "官方政策不接受护照",
                                                "official policy does not accept passports",
                                                "公式ポリシーではパスポートを受け付けていません"),
        }

    if not p["bookable_online"]:
        return {
            "status": "⚠️ 需人工",
            "status_label": _status_label("⚠️ 需人工", lang),
            "reason": _msg(lang,
                           "该景点不支持在线预订，需现场购票",
                           "This attraction does not support online booking; buy tickets on site",
                           "この観光地はオンライン予約に対応していません。現地でチケットを購入してください"),
            "action": _msg(lang,
                           "建议抵达后直接前往售票窗口，携带护照原件",
                           "Go directly to the ticket window on arrival with your original passport",
                           "到着後、パスポート原本を持って直接チケット窓口へお越しください"),
            "details": f"{attr['name']} " + _msg(lang,
                                                "仅支持现场购票",
                                                "only supports on-site ticket purchase",
                                                "現地購入のみ対応"),
        }

    if p["requires_chinese_phone"] and not has_chinese_phone:
        return {
            "status": "⚠️ 需人工",
            "status_label": _status_label("⚠️ 需人工", lang),
            "reason": _msg(lang,
                           "在线预订需要中国手机号接收验证码",
                           "Online booking requires a China mobile number for the verification code",
                           "オンライン予約には認証コード受信用の中国の携帯番号が必要です"),
            "action": _msg(lang,
                           "建议请酒店/导游协助预订，或使用支持国际手机号的平台（如 Ctrip 国际版）",
                           "Ask your hotel/guide to help book, or use a platform that supports international numbers (e.g., Ctrip international)",
                           "ホテル/ガイドに予約を依頼するか、国際電話番号対応のプラットフォーム（Ctrip国際版など）をご利用ください"),
            "details": f"{attr['name']} " + _msg(lang,
                                                "预订系统需中国手机号验证",
                                                "booking system requires a China mobile number for verification",
                                                "予約システムは中国の携帯番号での認証が必要"),
        }

    # 全部条件满足
    return {
        "status": "✅ 可订",
        "status_label": _status_label("✅ 可订", lang),
        "reason": _msg(lang,
                       "护照可直接在线预订",
                       "Passport can be used for online booking directly",
                       "パスポートで直接オンライン予約できます"),
        "action": _msg(lang,
                       f"通过 {p['platform']} 预订，提前 {p['advance_booking_days']} 天",
                       f"Book via {p['platform']}, {p['advance_booking_days']} day(s) in advance",
                       f"{p['platform']}で予約、{p['advance_booking_days']}日前までに"),
        "details": (
            f"{attr['name']} " + _msg(lang,
                                      "接受护照在线预订，",
                                      "accepts passport online booking, ",
                                      "パスポートでのオンライン予約を受け付けており、")
            + _msg(lang,
                   f"门票 ¥{p['price_cny']}，",
                   f"ticket ¥{p['price_cny']}, ",
                   f"チケット ¥{p['price_cny']}、")
            + _msg(lang,
                   f"建议提前 {p['advance_booking_days']} 天预订",
                   f"book {p['advance_booking_days']} day(s) in advance",
                   f"{p['advance_booking_days']}日前までの予約をおすすめ")
        ),
    }


def get_city_summary(city: str) -> list[dict]:
    """获取城市所有景点的护照可行性摘要列表"""
    from src.utils.content_loader import load_city_data

    data = load_city_data(city)
    if not data:
        return []

    summary = []
    for attr in data["attractions"]:
        p = attr["passport"]
        summary.append({
            "id": attr["id"],
            "name": attr["name"],
            "name_en": attr["name_en"],
            "status": attr["status"],
            "bookable_online": p["bookable_online"],
            "passport_accepted": p["passport_accepted"],
            "requires_phone": p["requires_chinese_phone"],
            "price": p["price_cny"],
            "advance_days": p["advance_booking_days"],
        })
    return summary


if __name__ == "__main__":
    # 自测
    print("=== 故宫（有中国手机号）===")
    print(check_passport_bookability("beijing", "gugong", has_chinese_phone=True, lang="ja"))
    print("\n=== 故宫（无中国手机号）===")
    print(check_passport_bookability("beijing", "gugong", has_chinese_phone=False, lang="en"))
