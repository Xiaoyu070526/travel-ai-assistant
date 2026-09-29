"""日志配置（Day 6-7）。

基于标准库 :mod:`logging`，把日志写入项目根目录的 ``logs/app.log``。

记录内容
--------
- 请求开始 / 成功 / 失败
- 错误类型（异常类名）
- 请求耗时

禁止记录
--------
- API Key / Authorization header
- 游客敏感信息

通过 :func:`register_secret` 登记敏感字符串（如 API token），
:class:`_SecretsFilter` 会把日志中出现这些字符串的位置替换为 ``[REDACTED]``，
作为代码层面「绝不打印密钥」之外的第二道防线。
"""

from __future__ import annotations

import logging
from pathlib import Path

#: 日志目录与文件（本文件位于 <root>/src/utils/logging_config.py）
LOG_DIR: Path = Path(__file__).resolve().parents[2] / "logs"
LOG_FILE: Path = LOG_DIR / "app.log"

_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

#: 已登记的敏感字符串集合
_secrets: set[str] = set()

_configured = False


def register_secret(secret: str | None) -> None:
    """登记一个敏感字符串，后续所有日志输出都会将其打码。"""
    if secret:
        _secrets.add(secret)


class _SecretsFilter(logging.Filter):
    """把日志消息中的敏感字符串替换为 ``[REDACTED]``。"""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for secret in _secrets:
            if secret and secret in message:
                message = message.replace(secret, "[REDACTED]")
        record.msg = message
        record.args = ()
        return True


def _configure_root() -> None:
    """配置根 logger（幂等，只执行一次）。"""
    global _configured
    if _configured:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(_FORMAT)
    secrets_filter = _SecretsFilter()

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.addFilter(secrets_filter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """返回指定名称的 logger，并确保根日志已完成配置。"""
    _configure_root()
    return logging.getLogger(name)
