"""FAQ 知识库单元测试：覆盖调研高频痛点命中与未命中"""

from src.utils.faq_kb import match_faq, quick_questions


def test_faq_hits_high_frequency_pain_points():
    """调研高频痛点问题应命中对应条目"""
    cases = {
        "酒店说不能接外籍护照怎么办": "酒店说不能接外籍护照怎么办",
        "地铁怎么用护照买票": "地铁怎么用护照买票",
        "支付宝绑卡失败了": "支付宝/微信绑外卡失败或支付被拒怎么办",
        "网络断了": "网络断了 / SIM 卡怎么解决",
        "公安住宿登记": "公安住宿登记怎么办",
        "高铁票怎么用护照买": "高铁/火车票怎么用护照买",
        "怎么打车": "怎么打车 / 网约车",
        "景点只能用中文平台预约": "景点只能用中文平台预约怎么办",
    }
    for question, expected_q in cases.items():
        hit = match_faq(question)
        assert hit is not None, f"应命中: {question}"
        assert hit["question"] == expected_q, f"{question} -> {hit['question']}, 期望 {expected_q}"


def test_faq_miss_unrelated_question():
    """无关问题应返回 None（不误判）"""
    assert match_faq("今天北京天气怎么样") is None
    assert match_faq("我想学做菜") is None


def test_quick_questions_non_empty():
    """快捷提问列表非空且为字符串"""
    qs = quick_questions()
    assert len(qs) >= 5
    assert all(isinstance(q, str) and q for q in qs)


def test_faq_answers_have_source():
    """每条 FAQ 答案应包含来源标注（不编造原则）"""
    from src.utils.faq_kb import FAQ_KB

    assert len(FAQ_KB) >= 8
    for item in FAQ_KB:
        assert "来源" in item["answer"], f"{item['id']} 缺少来源标注"
