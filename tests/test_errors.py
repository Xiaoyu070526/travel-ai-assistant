"""``src.utils.errors`` 的单元测试（Day 6）。

验证异常类型的层级关系、可选属性，以及 Day 3 的 ``DataLoadError`` 被
re-export 后仍是同一个类对象（不是重复定义）。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils import errors  # noqa: E402
from src.utils.data_loader import DataFileNotFoundError, DataLoadError  # noqa: E402


class TestExceptionHierarchy(unittest.TestCase):
    def test_api_errors_are_api_error_subclasses(self):
        for exc_cls in (
            errors.APITimeoutError,
            errors.APIAuthenticationError,
            errors.APIResponseError,
        ):
            with self.subTest(exc=exc_cls.__name__):
                self.assertTrue(issubclass(exc_cls, errors.APIError))

    def test_configuration_error_is_independent(self):
        self.assertTrue(issubclass(errors.ConfigurationError, Exception))
        self.assertFalse(issubclass(errors.ConfigurationError, errors.APIError))

    def test_guide_generation_error_is_independent(self):
        self.assertTrue(issubclass(errors.GuideGenerationError, Exception))
        self.assertFalse(issubclass(errors.GuideGenerationError, errors.APIError))


class TestAPIErrorStatusCode(unittest.TestCase):
    def test_default_status_code_is_none(self):
        err = errors.APIError("boom")
        self.assertIsNone(err.status_code)

    def test_status_code_is_stored(self):
        err = errors.APIAuthenticationError("bad key", status_code=401)
        self.assertEqual(err.status_code, 401)

    def test_authentication_error_is_an_api_error(self):
        err = errors.APIAuthenticationError("bad key", status_code=403)
        self.assertIsInstance(err, errors.APIError)
        self.assertEqual(err.status_code, 403)


class TestDataLoadErrorReExport(unittest.TestCase):
    def test_reexported_data_load_error_is_the_same_class(self):
        self.assertIs(errors.DataLoadError, DataLoadError)

    def test_reexported_data_file_not_found_is_the_same_class(self):
        self.assertIs(errors.DataFileNotFoundError, DataFileNotFoundError)


if __name__ == "__main__":
    unittest.main(verbosity=2)
