"""``src.api.llm_client`` 的单元测试（Day 6）。

所有测试都用 ``unittest.mock`` 模拟 ``requests.post``，**不会真正调用 DeepSeek API**，
因此无需配置 API Key 也能通过。

覆盖：API Key 缺失、超时、HTTP 错误、非法 JSON、空响应、正常生成结构、fallback、
重试，以及日志不泄漏 API Key。
"""

from __future__ import annotations

import io
import json
import logging
import sys
import unittest
from pathlib import Path
from unittest import mock

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api import llm_client  # noqa: E402
from src.api.llm_client import LLMClient  # noqa: E402
from src.utils import logging_config  # noqa: E402
from src.utils.errors import (  # noqa: E402
    APIAuthenticationError,
    APIError,
    APIResponseError,
    APITimeoutError,
    ConfigurationError,
)

SECRET = "sk-test-secret-123"

CONTEXT = {
    "nationality": "USA",
    "arrival_date": "2026-10-01",
    "chinese_level": "none",
    "city": {"city_id": "beijing", "city_name": "北京"},
    "attraction": {"attraction_id": "beijing-forbidden-city", "name": "故宫博物院"},
    "passport_booking_status": "unknown",
    "reservation_required": None,
    "entry_method": None,
    "alternative_attraction_ids": [],
    "source_url": None,
    "updated_at": "2026-09-23",
}

VALID_GUIDE_BODY = {
    "title": "故宫博物院 (Forbidden City) 攻略",
    "destination": {"city": "北京", "attraction": "故宫博物院"},
    "booking": {
        "passport_status": "unknown",
        "status_label": "需人工确认",
        "steps": [{"step": 1, "action": "确认预约", "note": "需人工确认"}],
        "source_url": None,
    },
    "transport": {
        "recommended_route": "需人工确认",
        "steps": ["使用地图查询"],
        "estimated_time": "需人工确认",
    },
    "alternatives": [],
    "emergency": {"problem": "预约已满", "steps": ["改期"]},
    "notice": "信息仅供参考，以官方最新信息为准",
}


def _mock_response(status_code=200, json_body=None, json_error=None):
    resp = mock.Mock()
    resp.status_code = status_code
    if json_error is not None:
        resp.json.side_effect = json_error
    else:
        resp.json.return_value = json_body if json_body is not None else {}
    return resp


def _text_response(text):
    """构造 Messages 接口成功响应（content 中一段 text）。"""
    return _mock_response(200, {"content": [{"type": "text", "text": text}]})


class TestAPIKeyMissing(unittest.TestCase):
    def test_complete_raises_configuration_error_without_key(self):
        client = LLMClient(auth_token="")
        with self.assertRaises(ConfigurationError):
            client.complete("system", "user")

    def test_generate_guide_returns_fallback_without_key(self):
        client = LLMClient(auth_token="")
        result = client.generate_guide(CONTEXT)
        self.assertEqual(result["status"], "fallback")
        self.assertIn("notice", result)


class TestTimeoutsAndRetries(unittest.TestCase):
    @mock.patch("requests.post")
    def test_timeout_raises_api_timeout_error(self, mock_post):
        client = LLMClient(auth_token=SECRET, max_retries=0)
        mock_post.side_effect = requests.exceptions.Timeout("timeout")
        with self.assertRaises(APITimeoutError):
            client.complete("system", "user")

    @mock.patch("requests.post")
    def test_retries_then_raises_timeout(self, mock_post):
        client = LLMClient(auth_token=SECRET, max_retries=2)
        client._sleep = mock.Mock()  # 避免真实等待
        mock_post.side_effect = requests.exceptions.Timeout("timeout")
        with self.assertRaises(APITimeoutError):
            client.complete("system", "user")
        self.assertEqual(mock_post.call_count, 3)  # 1 次初始 + 2 次重试


class TestHTTPErrors(unittest.TestCase):
    @mock.patch("requests.post")
    def test_401_raises_authentication_error(self, mock_post):
        client = LLMClient(auth_token=SECRET, max_retries=0)
        mock_post.return_value = _mock_response(401, {"error": "bad key"})
        with self.assertRaises(APIAuthenticationError):
            client.complete("system", "user")

    @mock.patch("requests.post")
    def test_403_raises_authentication_error(self, mock_post):
        client = LLMClient(auth_token=SECRET, max_retries=0)
        mock_post.return_value = _mock_response(403, {})
        with self.assertRaises(APIAuthenticationError):
            client.complete("system", "user")

    @mock.patch("requests.post")
    def test_500_raises_api_error(self, mock_post):
        client = LLMClient(auth_token=SECRET, max_retries=0)
        mock_post.return_value = _mock_response(500, {})
        with self.assertRaises(APIError):
            client.complete("system", "user")


class TestResponseParsing(unittest.TestCase):
    @mock.patch("requests.post")
    def test_invalid_json_raises_response_error(self, mock_post):
        client = LLMClient(auth_token=SECRET, max_retries=0)
        mock_post.return_value = _mock_response(200, json_error=ValueError("not json"))
        with self.assertRaises(APIResponseError):
            client.complete("system", "user")

    @mock.patch("requests.post")
    def test_empty_content_raises_response_error(self, mock_post):
        client = LLMClient(auth_token=SECRET, max_retries=0)
        mock_post.return_value = _mock_response(200, {"content": []})
        with self.assertRaises(APIResponseError):
            client.complete("system", "user")

    @mock.patch("requests.post")
    def test_string_content_is_accepted(self, mock_post):
        client = LLMClient(auth_token=SECRET, max_retries=0)
        mock_post.return_value = _mock_response(200, {"content": "hello"})
        self.assertEqual(client.complete("system", "user"), "hello")


class TestGenerateGuideSuccess(unittest.TestCase):
    @mock.patch("requests.post")
    def test_generate_guide_returns_success_structure(self, mock_post):
        client = LLMClient(auth_token=SECRET, max_retries=0)
        mock_post.return_value = _text_response(
            json.dumps(VALID_GUIDE_BODY, ensure_ascii=False)
        )
        result = client.generate_guide(CONTEXT)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["title"], VALID_GUIDE_BODY["title"])
        for field in ("booking", "transport", "alternatives", "emergency", "notice"):
            self.assertIn(field, result)

    @mock.patch("requests.post")
    def test_request_uses_expected_url_headers_and_payload(self, mock_post):
        client = LLMClient(
            auth_token=SECRET,
            base_url="https://example.deepseek.com/anthropic",
            model="deepseek-flash",
            max_retries=0,
        )
        mock_post.return_value = _text_response(json.dumps(VALID_GUIDE_BODY, ensure_ascii=False))
        client.generate_guide(CONTEXT)

        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://example.deepseek.com/anthropic/v1/messages")
        self.assertEqual(kwargs["headers"]["authorization"], f"Bearer {SECRET}")
        self.assertEqual(kwargs["json"]["model"], "deepseek-flash")
        self.assertEqual(kwargs["json"]["max_tokens"], llm_client.MAX_TOKENS)
        # 请求体中包含 system 与 user 消息
        self.assertIn("system", kwargs["json"])
        self.assertEqual(kwargs["json"]["messages"][0]["role"], "user")


class TestGenerateGuideFallback(unittest.TestCase):
    @mock.patch("requests.post")
    def test_returns_fallback_on_http_error(self, mock_post):
        client = LLMClient(auth_token=SECRET, max_retries=0)
        mock_post.return_value = _mock_response(500, {})
        result = client.generate_guide(CONTEXT)
        self.assertEqual(result["status"], "fallback")
        self.assertEqual(result["title"], "暂时无法生成完整攻略")
        self.assertIn("notice", result)

    @mock.patch("requests.post")
    def test_returns_fallback_on_invalid_guide_json(self, mock_post):
        client = LLMClient(auth_token=SECRET, max_retries=0)
        mock_post.return_value = _text_response("this is not json")
        result = client.generate_guide(CONTEXT)
        self.assertEqual(result["status"], "fallback")

    @mock.patch("requests.post")
    def test_returns_fallback_on_missing_required_fields(self, mock_post):
        client = LLMClient(auth_token=SECRET, max_retries=0)
        mock_post.return_value = _text_response(json.dumps({"title": "只有标题"}))
        result = client.generate_guide(CONTEXT)
        self.assertEqual(result["status"], "fallback")

    def test_fallback_does_not_fabricate_travel_info(self):
        result = llm_client.build_fallback()
        text = json.dumps(result, ensure_ascii=False)
        self.assertEqual(result["status"], "fallback")
        # fallback 只包含兜底文案，不含票价、开放时间、具体路线/购票渠道等编造信息
        for fabricated in ("票价", "开放时间", "号线", "地铁站", "微信购票"):
            self.assertNotIn(fabricated, text)


class TestModuleLevelGenerateGuide(unittest.TestCase):
    def test_returns_fallback_when_unconfigured(self):
        """默认客户端在未配置 Key 时也应返回 fallback，而非抛异常。"""
        with mock.patch("src.utils.config.get_auth_token", return_value=None):
            result = llm_client.generate_guide(CONTEXT)
        self.assertEqual(result["status"], "fallback")


class TestNoSecretLeakInLogs(unittest.TestCase):
    def test_client_registers_secret_for_redaction(self):
        LLMClient(auth_token=SECRET)
        self.assertIn(SECRET, logging_config._secrets)

    def test_secrets_filter_redacts_token(self):
        logging_config.register_secret(SECRET)
        filt = logging_config._SecretsFilter()
        record = logging.LogRecord(
            "test", logging.INFO, "", 0, "failed with token=%s", (SECRET,), None
        )
        self.assertTrue(filt.filter(record))
        self.assertNotIn(SECRET, record.getMessage())
        self.assertIn("[REDACTED]", record.getMessage())

    @mock.patch("requests.post")
    def test_client_logs_do_not_contain_token(self, mock_post):
        client = LLMClient(auth_token=SECRET, max_retries=0)
        logger = logging.getLogger("src.api.llm_client")

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler.addFilter(logging_config._SecretsFilter())
        logger.addHandler(handler)

        try:
            mock_post.side_effect = requests.exceptions.Timeout("timeout")
            with self.assertRaises(APITimeoutError):
                client.complete("system", "user")
        finally:
            logger.removeHandler(handler)

        output = stream.getvalue()
        self.assertNotIn(SECRET, output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
