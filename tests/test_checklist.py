"""Checklist（DeepSeek）生成逻辑单元测试：空响应重试与友好提示。

不真实调用 DeepSeek API——用 mock 模拟 ``_deepseek_text`` 抛出
``APIResponseError``（即 DeepSeek 返回空内容）或返回正常内容，
验证 ``_generate_checklist`` 的「重试一次 → 仍失败则友好提示」逻辑。
"""

from unittest import mock

import pytest

from src import app
from src.utils.errors import APIResponseError


def _city_data() -> dict:
    return {
        "city": {
            "name": "北京",
            "name_en": "Beijing",
            "description": "测试城市",
            "transport": {
                "airport": "首都机场",
                "airport_to_city": "机场快轨",
                "city_transport": "地铁",
            },
            "apps": [],
            "essentials": {},
        },
        "attractions": [],
    }


def _identity() -> dict:
    return {
        "language": "en",
        "nationality": "United States",
        "arrival_date": "2026-10-01",
        "chinese_level": "None",
    }


@pytest.fixture(autouse=True)
def _mock_streamlit():
    """替换 Streamlit 的 ``st``，避免真实渲染，并固定界面语言为 en。"""
    st_mock = mock.MagicMock()
    st_mock.session_state.identity = _identity()
    with mock.patch.object(app, "st", st_mock):
        yield st_mock


def test_checklist_retries_once_then_succeeds():
    """第一次 DeepSeek 返回空内容，第二次成功 → 正常显示清单。"""
    city_data = _city_data()
    identity = _identity()

    with mock.patch.object(
        app,
        "_deepseek_text",
        side_effect=[APIResponseError("API 返回内容为空"), "✅ 清单内容"],
    ) as deepseek:
        app._generate_checklist(city_data, identity)

    assert deepseek.call_count == 2
    app.st.success.assert_called_once()
    app.st.markdown.assert_called_once_with("✅ 清单内容")
    app.st.warning.assert_not_called()
    app.st.error.assert_not_called()


def test_checklist_two_empty_responses_shows_friendly_warning():
    """连续两次空内容 → 不抛异常，进入友好提示（不伪造 AI 内容）。"""
    city_data = _city_data()
    identity = _identity()

    with mock.patch.object(
        app,
        "_deepseek_text",
        side_effect=[APIResponseError("API 返回内容为空"), APIResponseError("API 返回内容为空")],
    ) as deepseek:
        app._generate_checklist(city_data, identity)  # 不应抛异常

    assert deepseek.call_count == 2
    app.st.success.assert_not_called()
    app.st.warning.assert_called_once()
    app.st.error.assert_not_called()
