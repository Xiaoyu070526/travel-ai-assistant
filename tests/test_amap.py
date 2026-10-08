"""``src.api.amap`` 的单元测试（Day 9）。

所有测试都用 ``unittest.mock`` 模拟 ``requests.get``，**不会真正调用高德 API**，
也不会读取或使用真实 Key。
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api import amap  # noqa: E402
from src.api.amap import (  # noqa: E402
    AmapAPIError,
    AmapConfigError,
    AmapError,
    AmapParseError,
    AmapRequestError,
    get_weather,
)

TEST_KEY = "test-amap-key"

FORECAST = {
    "city": "北京市",
    "adcode": "110000",
    "province": "北京",
    "reporttime": "2026-10-08 11:00:00",
    "casts": [{"date": "2026-10-09", "dayweather": "晴", "nightweather": "多云"}],
}


def _weather_response(status="1", forecasts=None, info=""):
    body = {"status": status, "info": info}
    if forecasts is not None:
        body["forecasts"] = forecasts
    resp = mock.Mock()
    resp.status_code = 200
    resp.json.return_value = body
    return resp


class TestGetWeatherConfig(unittest.TestCase):
    @mock.patch.dict(os.environ, {"AMAP_MAP_KEY": ""})
    def test_missing_key_raises_config_error(self):
        with self.assertRaises(AmapConfigError):
            get_weather("beijing")

    @mock.patch.dict(os.environ, {"AMAP_MAP_KEY": TEST_KEY})
    def test_unsupported_city_raises_amap_error(self):
        with self.assertRaises(AmapError):
            get_weather("tokyo")


class TestGetWeatherRequestErrors(unittest.TestCase):
    @mock.patch.dict(os.environ, {"AMAP_MAP_KEY": TEST_KEY})
    @mock.patch("requests.get")
    def test_network_error_raises_request_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("boom")
        with self.assertRaises(AmapRequestError):
            get_weather("beijing")

    @mock.patch.dict(os.environ, {"AMAP_MAP_KEY": TEST_KEY})
    @mock.patch("requests.get")
    def test_http_non_200_raises_request_error(self, mock_get):
        resp = mock.Mock()
        resp.status_code = 500
        mock_get.return_value = resp
        with self.assertRaises(AmapRequestError):
            get_weather("beijing")


class TestGetWeatherAPIAndParseErrors(unittest.TestCase):
    @mock.patch.dict(os.environ, {"AMAP_MAP_KEY": TEST_KEY})
    @mock.patch("requests.get")
    def test_amap_business_error_raises_api_error(self, mock_get):
        mock_get.return_value = _weather_response(status="0", info="INVALID_USER_KEY")
        with self.assertRaises(AmapAPIError):
            get_weather("beijing")

    @mock.patch.dict(os.environ, {"AMAP_MAP_KEY": TEST_KEY})
    @mock.patch("requests.get")
    def test_invalid_json_raises_parse_error(self, mock_get):
        resp = mock.Mock()
        resp.status_code = 200
        resp.json.side_effect = ValueError("not json")
        mock_get.return_value = resp
        with self.assertRaises(AmapParseError):
            get_weather("beijing")

    @mock.patch.dict(os.environ, {"AMAP_MAP_KEY": TEST_KEY})
    @mock.patch("requests.get")
    def test_missing_forecasts_raises_parse_error(self, mock_get):
        mock_get.return_value = _weather_response(status="1", forecasts=[])
        with self.assertRaises(AmapParseError):
            get_weather("beijing")


class TestGetWeatherSuccess(unittest.TestCase):
    @mock.patch.dict(os.environ, {"AMAP_MAP_KEY": TEST_KEY})
    @mock.patch("requests.get")
    def test_success_returns_first_forecast(self, mock_get):
        mock_get.return_value = _weather_response(status="1", forecasts=[FORECAST])
        result = get_weather("beijing", extensions="all")
        self.assertEqual(result, FORECAST)
        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], amap.AMAP_WEATHER_URL)
        self.assertEqual(kwargs["params"]["city"], "110000")
        self.assertEqual(kwargs["params"]["extensions"], "all")

    @mock.patch.dict(os.environ, {"AMAP_MAP_KEY": TEST_KEY})
    @mock.patch("requests.get")
    def test_key_is_not_present_in_error_or_log(self, mock_get):
        # 业务错误场景下，异常信息不得包含 Key。
        mock_get.return_value = _weather_response(status="0", info="DAILY_QUERY_OVER_LIMIT")
        with self.assertRaises(AmapAPIError) as ctx:
            get_weather("beijing")
        self.assertNotIn(TEST_KEY, str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
