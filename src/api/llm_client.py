"""DeepSeek Anthropic-compatible LLM 客户端（Day 6-7）。

通过 ``requests`` 调用 DeepSeek 的 Anthropic-compatible Messages 接口，
把「景点知识库 + 游客上下文」转成结构化的游玩攻略 JSON。

设计约定
--------
- 所有密钥从环境变量 / ``.env`` 读取（见 :mod:`src.utils.config`），绝不硬编码。
- 低层 :meth:`LLMClient.complete` 负责请求 / 重试 / 错误映射，失败时抛出明确的
  异常类型（见 :mod:`src.utils.errors`），便于上层按类型处理。
- 高层 :meth:`LLMClient.generate_guide` 组装 prompt、调用模型并校验输出，
  任何失败都 **不抛出异常**，而是返回统一的 fallback 结构，保证上层 Streamlit
  不会因为 AI 服务故障而崩溃。

用法::

    from src.api.llm_client import generate_guide

    result = generate_guide({...})  # 永远返回 dict，status 为 success 或 fallback
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from src.api import prompts
from src.utils import config, logging_config
from src.utils.errors import (
    APIAuthenticationError,
    APIError,
    APIResponseError,
    APITimeoutError,
    ConfigurationError,
    GuideGenerationError,
)

logger = logging_config.get_logger(__name__)

#: 每次请求的 max_tokens（结构化攻略 JSON 足够，且避免过大）
MAX_TOKENS = 4096

#: 可重试的 HTTP 状态码
_RETRYABLE_STATUS = {408, 409, 429}


def build_fallback(message: str | None = None) -> dict[str, Any]:
    """返回统一的 fallback 结构（攻略生成失败时使用）。

    fallback 中**不包含任何编造的旅游信息**，只有兜底文案。
    """
    return {
        "status": "fallback",
        "title": "暂时无法生成完整攻略",
        "message": message or "AI服务暂时不可用，请稍后重试。",
        "notice": "购票、预约和入园信息请以官方最新信息为准。",
    }


class LLMClient:
    """DeepSeek Anthropic-compatible API 客户端。"""

    def __init__(
        self,
        base_url: str | None = None,
        auth_token: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        # base_url / model / timeout / max_retries：显式传值优先，否则读配置。
        self.base_url = (base_url or config.get_base_url()).rstrip("/")
        self.model = model or config.get_model()
        self.timeout = timeout if timeout is not None else config.get_timeout()
        self.max_retries = (
            max_retries if max_retries is not None else config.get_max_retries()
        )

        # auth_token：显式传入非 None 时用它（含空字符串，表示「明确未配置」），
        # 否则回退到环境变量 / .env。
        if auth_token is None:
            auth_token = config.get_auth_token()
        self.auth_token = auth_token

        # 把 token 登记到日志过滤器，作为「不打印密钥」的第二道防线。
        logging_config.register_secret(self.auth_token)

    @property
    def messages_url(self) -> str:
        """Anthropic-compatible Messages 接口地址。"""
        return f"{self.base_url}/v1/messages"

    def _headers(self) -> dict[str, str]:
        """构造请求头；token 只进入 header，绝不进入日志。"""
        return {
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
            # DeepSeek 兼容两种鉴权：Bearer token 与 x-api-key，一并带上。
            "authorization": f"Bearer {self.auth_token}",
            "x-api-key": self.auth_token,
        }

    def _ensure_configured(self) -> None:
        if not self.auth_token:
            raise ConfigurationError(
                "未配置 API Key：请设置环境变量 ANTHROPIC_AUTH_TOKEN"
                "（或 ANTHROPIC_API_KEY），或在项目根目录创建 .env 文件。"
            )

    # ------------------------------------------------------------------ #
    # 重试 / 错误映射
    # ------------------------------------------------------------------ #

    @staticmethod
    def _is_retryable(error: Exception) -> bool:
        """判断异常是否值得重试（超时 / 429 / 5xx）。"""
        if isinstance(error, APITimeoutError):
            return True
        if isinstance(error, APIError):
            status_code = error.status_code
            return status_code is not None and (
                status_code in _RETRYABLE_STATUS or status_code >= 500
            )
        return False

    def _sleep(self, attempt: int) -> None:
        """重试前的退避等待（指数退避，封顶 8 秒）。"""
        delay = min(2 ** attempt, 8)
        logger.info("LLM retry backoff %.1fs", delay)
        time.sleep(delay)

    def _map_status(self, resp: "requests.Response") -> APIError | None:
        """把 HTTP 状态码映射为异常；2xx 返回 ``None``。"""
        status_code = resp.status_code
        if 200 <= status_code < 300:
            return None
        if status_code in (401, 403):
            return APIAuthenticationError(
                f"API Key 无效或无权限（HTTP {status_code}）", status_code=status_code
            )
        return APIError(f"LLM API 返回错误（HTTP {status_code}）", status_code=status_code)

    @staticmethod
    def _extract_text(resp: "requests.Response") -> str:
        """从 Messages 接口响应中提取模型生成的文本。

        :raises APIResponseError: 响应不是合法 JSON、缺少 content、或内容为空。
        """
        try:
            payload = resp.json()
        except ValueError as exc:
            raise APIResponseError("API 返回内容不是合法 JSON") from exc

        if not isinstance(payload, dict):
            raise APIResponseError("API 返回结构不符合预期")

        content = payload.get("content")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            texts = [
                block.get("text")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            text = "".join(part for part in texts if isinstance(part, str))
        else:
            text = ""

        text = text.strip()
        if not text:
            raise APIResponseError("API 返回内容为空")
        return text

    # ------------------------------------------------------------------ #
    # 低层：请求 / 重试 / 错误映射
    # ------------------------------------------------------------------ #

    def complete(self, system: str, user: str) -> str:
        """调用 Messages 接口并返回模型生成的文本，失败时抛对应异常。

        :raises ConfigurationError: API Key 缺失
        :raises APITimeoutError: 请求超时（重试耗尽后）
        :raises APIAuthenticationError: 401/403
        :raises APIError: 其他 HTTP / 网络错误（重试耗尽后）
        :raises APIResponseError: 返回内容无法解析或为空
        """
        self._ensure_configured()

        payload = {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }

        total_attempts = self.max_retries + 1
        last_error: Exception | None = None

        for attempt in range(total_attempts):
            started = time.perf_counter()
            logger.info(
                "LLM request start (attempt=%d/%d, model=%s)",
                attempt + 1,
                total_attempts,
                self.model,
            )

            try:
                resp = requests.post(
                    self.messages_url,
                    headers=self._headers(),
                    json=payload,
                    timeout=self.timeout,
                )
            except requests.Timeout as exc:
                last_error = APITimeoutError("LLM API 请求超时")
                logger.warning(
                    "LLM request timeout (attempt=%d/%d, elapsed=%.2fs)",
                    attempt + 1,
                    total_attempts,
                    time.perf_counter() - started,
                )
            except requests.RequestException as exc:
                last_error = APIError(f"网络错误：{type(exc).__name__}")
                logger.warning(
                    "LLM request network error (attempt=%d/%d, error=%s)",
                    attempt + 1,
                    total_attempts,
                    type(exc).__name__,
                )
            else:
                elapsed = time.perf_counter() - started
                status_error = self._map_status(resp)
                if status_error is not None:
                    last_error = status_error
                    logger.warning(
                        "LLM request failed (attempt=%d/%d, status=%d, error=%s, elapsed=%.2fs)",
                        attempt + 1,
                        total_attempts,
                        resp.status_code,
                        type(status_error).__name__,
                        elapsed,
                    )
                else:
                    text = self._extract_text(resp)
                    logger.info(
                        "LLM request success (attempt=%d/%d, elapsed=%.2fs)",
                        attempt + 1,
                        total_attempts,
                        elapsed,
                    )
                    return text

            # 走到这里说明本次尝试失败（last_error 已赋值）
            if not self._is_retryable(last_error) or attempt >= self.max_retries:
                logger.error("LLM request final failure (error=%s)", type(last_error).__name__)
                raise last_error  # type: ignore[misc]

            self._sleep(attempt)

        # 理论上不会走到这里（上面总会 return 或 raise），作为兜底。
        raise APIError("LLM 请求失败：重试耗尽")

    # ------------------------------------------------------------------ #
    # 高层：生成攻略（永不抛出异常，失败返回 fallback）
    # ------------------------------------------------------------------ #

    def generate_guide(self, context: dict[str, Any]) -> dict[str, Any]:
        """根据上下文生成结构化攻略，失败时返回 fallback 结构，绝不抛出异常。

        :return: ``{"status": "success", ...攻略字段}`` 或 fallback 结构。
        """
        system = prompts.SYSTEM_PROMPT
        user = prompts.build_user_prompt(context)

        try:
            text = self.complete(system, user)
        except ConfigurationError as exc:
            logger.error("Guide generation failed (configuration): %s", exc)
            return build_fallback()
        except APIError as exc:
            logger.error("Guide generation failed (api error=%s): %s", type(exc).__name__, exc)
            return build_fallback()
        except Exception as exc:  # noqa: BLE001 —— 用户侧边界，兜底防崩溃
            logger.error("Guide generation failed (%s)", type(exc).__name__, exc_info=True)
            return build_fallback()

        try:
            body = prompts.parse_guide_json(text)
            prompts.validate_guide(body)
        except GuideGenerationError as exc:
            logger.error("Guide generation failed (parse/validate): %s", exc)
            return build_fallback()

        result: dict[str, Any] = {"status": "success"}
        result.update(body)
        return result


def generate_guide(
    context: dict[str, Any],
    client: LLMClient | None = None,
) -> dict[str, Any]:
    """模块级便捷入口：使用默认客户端生成攻略。

    :param context: 见 :func:`src.api.prompts.build_user_prompt` 的 context 约定。
    :param client: 可选，传入自定义的 :class:`LLMClient`（便于测试）。
    """
    if client is None:
        client = LLMClient()
    return client.generate_guide(context)
