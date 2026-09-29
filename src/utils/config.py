"""配置读取（Day 6-7）。

所有运行时配置一律从环境变量或项目根目录的 ``.env`` 文件读取，
**绝不硬编码任何密钥**。

读取函数每次调用都会重新读取 ``os.environ``，不缓存结果，
便于测试时用 ``mock.patch.dict(os.environ, ...)`` 覆盖，也便于运行时热更新。
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

#: 项目根目录（本文件位于 <root>/src/utils/config.py）
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

#: 默认读取的 .env 文件路径
ENV_FILE: Path = PROJECT_ROOT / ".env"

# --------------------------------------------------------------------------- #
# 默认值（均可被对应环境变量覆盖）
# --------------------------------------------------------------------------- #

DEFAULT_BASE_URL = "https://api.deepseek.com/anthropic"
DEFAULT_MODEL = "deepseek-flash"
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_RETRIES = 3

# --------------------------------------------------------------------------- #
# 环境变量名
# --------------------------------------------------------------------------- #

ENV_BASE_URL = "ANTHROPIC_BASE_URL"
ENV_AUTH_TOKEN = "ANTHROPIC_AUTH_TOKEN"
ENV_API_KEY = "ANTHROPIC_API_KEY"  # 兼容别名
ENV_MODEL = "ANTHROPIC_MODEL"
ENV_TIMEOUT = "ANTHROPIC_TIMEOUT"
ENV_MAX_RETRIES = "ANTHROPIC_MAX_RETRIES"


def load_env(env_file: str | Path | None = None) -> None:
    """加载 ``.env``（幂等，不会覆盖已存在的环境变量）。"""
    load_dotenv(env_file or ENV_FILE)


def get_base_url() -> str:
    """返回 Anthropic-compatible 接口的 base URL。"""
    return os.getenv(ENV_BASE_URL) or DEFAULT_BASE_URL


def get_auth_token() -> str | None:
    """返回认证 token。

    优先读 ``ANTHROPIC_AUTH_TOKEN``，其次兼容 ``ANTHROPIC_API_KEY``；
    都未设置时返回 ``None``（由调用方决定如何提示）。
    """
    return os.getenv(ENV_AUTH_TOKEN) or os.getenv(ENV_API_KEY)


def get_model() -> str:
    """返回模型名，默认 ``deepseek-flash``。"""
    return os.getenv(ENV_MODEL) or DEFAULT_MODEL


def get_timeout() -> float:
    """返回请求超时时间（秒），解析失败时回退到默认值。"""
    raw = os.getenv(ENV_TIMEOUT)
    if raw is None:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS


def get_max_retries() -> int:
    """返回基础重试次数，解析失败时回退到默认值。"""
    raw = os.getenv(ENV_MAX_RETRIES)
    if raw is None:
        return DEFAULT_MAX_RETRIES
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_MAX_RETRIES


# 导入即加载一次 .env，使后续 ``os.getenv`` 能直接读到其中的配置。
load_env()
