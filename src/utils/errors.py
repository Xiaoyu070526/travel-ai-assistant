"""统一异常类型（Day 6-7）。

集中定义攻略生成与 LLM API 调用过程中会用到的异常，便于上层（Streamlit）
按类型捕获并给出友好提示，而不是依赖脆弱的字符串匹配。

异常层次
--------
- :class:`ConfigurationError`：配置缺失 / 非法（独立于 API 异常）
- :class:`APIError`：LLM API 调用失败的基类
    - :class:`APITimeoutError`：请求超时
    - :class:`APIAuthenticationError`：API Key 无效或无权限（401/403）
    - :class:`APIResponseError`：返回内容无法解析（非法 JSON / 空响应）
- :class:`GuideGenerationError`：拿到模型输出后，组装 / 校验结构化攻略失败

.. note::
    ``DataLoadError`` / ``DataFileNotFoundError`` 已在
    :mod:`src.utils.data_loader`（Day 3）中定义，这里通过 re-export 统一入口，
    **避免重复定义同名异常**，因此调用方可以只从本模块导入全部异常。
"""

from __future__ import annotations

from .data_loader import DataFileNotFoundError, DataLoadError

__all__ = [
    "DataLoadError",
    "DataFileNotFoundError",
    "ConfigurationError",
    "APIError",
    "APITimeoutError",
    "APIAuthenticationError",
    "APIResponseError",
    "GuideGenerationError",
]


class ConfigurationError(Exception):
    """配置错误：缺少必要的环境变量，或配置值非法（如 API Key 未设置）。"""


class APIError(Exception):
    """调用 LLM API 失败的基础异常。

    表示网络层或服务端返回的、无法成功取得有效结果的情况。
    ``status_code`` 为可选属性，用于区分是否可重试（429 / 5xx）。
    """

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class APITimeoutError(APIError):
    """请求超时。"""


class APIAuthenticationError(APIError):
    """API Key 无效或没有权限（对应 HTTP 401 / 403）。"""


class APIResponseError(APIError):
    """API 返回内容无法解析（非法 JSON、空响应、缺少必要字段等）。"""


class GuideGenerationError(Exception):
    """攻略生成失败。

    表示模型返回了内容，但无法从中组装出符合 schema 的结构化攻略
    （例如不是合法 JSON、缺少必要字段）。
    """
