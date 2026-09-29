"""护照可行性校验逻辑

实现 "能订吗" 校验：根据用户身份信息和景点知识库，
判断该景点对该用户是否可预订、是否需要人工辅助、是否不可预订。
"""

from src.utils.content_loader import load_attraction


def check_passport_bookability(
    city: str,
    attraction_id: str,
    has_chinese_phone: bool = False,
) -> dict:
    """检查景点对护照游客的预订可行性

    Args:
        city: 城市拼音名，如 'beijing'
        attraction_id: 景点ID，如 'gugong'
        has_chinese_phone: 用户是否有中国手机号

    Returns:
        {
            "status": "✅ 可订" | "⚠️ 需人工" | "❌ 不可",
            "reason": 原因说明,
            "action": 建议操作,
            "details": 详细判断依据,
        }
    """
    attr = load_attraction(city, attraction_id)
    if not attr:
        return {
            "status": "❌ 不可",
            "reason": "知识库中未收录该景点信息",
            "action": "建议去官网确认或咨询客服",
            "details": "无数据",
        }

    p = attr["passport"]

    # 判断逻辑
    if not p["passport_accepted"]:
        return {
            "status": "❌ 不可",
            "reason": "该景点不接受护照预订",
            "action": "需使用中国身份证，或咨询是否有外籍游客特殊通道",
            "details": f"{attr['name']} 官方政策不接受护照",
        }

    if not p["bookable_online"]:
        return {
            "status": "⚠️ 需人工",
            "reason": "该景点不支持在线预订，需现场购票",
            "action": "建议抵达后直接前往售票窗口，携带护照原件",
            "details": f"{attr['name']} 仅支持现场购票",
        }

    if p["requires_chinese_phone"] and not has_chinese_phone:
        return {
            "status": "⚠️ 需人工",
            "reason": "在线预订需要中国手机号接收验证码",
            "action": "建议请酒店/导游协助预订，或使用支持国际手机号的平台（如 Ctrip 国际版）",
            "details": f"{attr['name']} 预订系统需中国手机号验证",
        }

    # 全部条件满足
    return {
        "status": "✅ 可订",
        "reason": "护照可直接在线预订",
        "action": f"通过 {p['platform']} 预订，提前 {p['advance_booking_days']} 天",
        "details": (
            f"{attr['name']} 接受护照在线预订，"
            f"门票 ¥{p['price_cny']}，"
            f"建议提前 {p['advance_booking_days']} 天预订"
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
    result = check_passport_bookability("beijing", "gugong", has_chinese_phone=True)
    print(result)

    print("\n=== 故宫（无中国手机号）===")
    result = check_passport_bookability("beijing", "gugong", has_chinese_phone=False)
    print(result)

    print("\n=== 上海迪士尼（无中国手机号）===")
    result = check_passport_bookability("shanghai", "disney", has_chinese_phone=False)
    print(result)

    print("\n=== 北京景点摘要 ===")
    summary = get_city_summary("beijing")
    for s in summary:
        print(f"  {s['name']}: {s['status']} (¥{s['price']}, 提前{s['advance_days']}天)")
