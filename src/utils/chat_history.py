"""聊天对话持久化（保留对话，应对后续行程追问）。

本模块是「保留聊天对话」功能的核心，独立于既有业务代码，便于接入与测试：

- :class:`ChatHistoryStore`：把对话历史读写到本机本地 JSON 文件
  （默认 ``data/chat_history.json``，已在 ``.gitignore`` 中忽略，不会提交到仓库），
  使浏览器刷新 / 切换页面后对话不丢失。
- :func:`build_conversation_block`：把历史格式化为可注入 LLM 的文本块，
  让模型在回答「后续行程问题」（如「那第二天的安排呢？」「改到下午可以吗？」）
  时看到完整上下文。

设计约定
--------
- 只读 ``role`` / ``content`` 两个字段，丢弃其它未知字段，避免把任何密钥或
  临时状态写进磁盘；``content`` 一律当普通文本，不记录 API Key。
- 文件损坏 / 缺失 / 解析失败一律安全降级为空历史，绝不抛异常中断页面。
- 文件写入失败（如磁盘只读）只记日志、不阻断对话。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.utils import logging_config

logger = logging_config.get_logger(__name__)

#: 项目根目录（本文件位于 <root>/src/utils/chat_history.py）
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

#: 默认持久化路径；已在 .gitignore 中忽略，不进入 Git。
DEFAULT_PATH: Path = PROJECT_ROOT / "data" / "chat_history.json"

#: 注入 prompt 的最大轮数（1 轮 = 1 问 1 答），控制上下文长度、避免超长。
MAX_TURNS = 20

#: 允许的 role 取值（与 st.chat_message 一致）。
_VALID_ROLES = ("user", "assistant")


# --------------------------------------------------------------------------- #
# 输入净化：只保留 role/content，剔除一切意外字段
# --------------------------------------------------------------------------- #

def _sanitize(history: list[dict[str, Any]]) -> list[dict[str, str]]:
    """净化外部读入的历史，只保留合法的 role/content 文本对。"""
    clean: list[dict[str, str]] = []
    for msg in history:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = msg.get("content")
        if role not in _VALID_ROLES or not isinstance(content, str):
            continue
        clean.append({"role": role, "content": content})
    return clean


# --------------------------------------------------------------------------- #
# 持久化存储
# --------------------------------------------------------------------------- #

class ChatHistoryStore:
    """把对话历史读写到本地 JSON 文件，刷新 / 跳转后不丢失。

    用法（在 Streamlit 中）::

        store = ChatHistoryStore()              # 或复用模块级单例 chat_store
        st.session_state.chat_history = store.load()   # 启动时恢复
        store.save(st.session_state.chat_history)       # 每轮之后保存
        store.clear()                                 # 用户清空对话
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else DEFAULT_PATH
        # 确保父目录存在（data/ 可能尚未创建）
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # noqa: BLE001 —— 目录创建失败不阻断对话
            logger.warning("聊天记录目录创建失败：%s", exc)

    # ---- 读 ----
    def load(self) -> list[dict[str, str]]:
        """读取历史；文件缺失 / 损坏 / 非列表一律返回空列表。"""
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("聊天记录读取失败，已重置为空：%s", exc)
            return []
        if not isinstance(raw, list):
            logger.warning("聊天记录格式异常（非列表），已重置为空")
            return []
        return _sanitize(raw)

    # ---- 写 ----
    def save(self, history: list[dict[str, Any]]) -> None:
        """保存历史到磁盘；失败只记日志，不影响对话进行。"""
        try:
            payload = _sanitize(list(history))
            self.path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:  # noqa: BLE001 —— 持久化失败不应中断用户
            logger.warning("聊天记录写入失败（不影响本次对话）：%s", exc)

    # ---- 清 ----
    def clear(self) -> None:
        """删除本地记录文件；不存在时静默忽略。"""
        try:
            if self.path.exists():
                self.path.unlink()
        except Exception as exc:  # noqa: BLE001
            logger.warning("聊天记录清除失败：%s", exc)


# --------------------------------------------------------------------------- #
# 注入 prompt 的对话上下文
# --------------------------------------------------------------------------- #

def format_conversation(history: list[dict[str, Any]], max_turns: int = MAX_TURNS) -> str:
    """把历史转成「role: content」逐行文本（仅取最近 max_turns 轮）。

    :param history: 对话历史（与 ``st.session_state.chat_history`` 同结构）。
    :param max_turns: 最多保留的轮数；超出只取最近部分，控制 prompt 长度。
    """
    if not history:
        return ""
    recent = history[-(max_turns * 2):]  # 1 轮 = user + assistant
    lines = []
    for msg in recent:
        role = "游客" if msg.get("role") == "user" else "助手"
        content = msg.get("content", "")
        if isinstance(content, str) and content.strip():
            lines.append(f"{role}：{content}")
    return "\n".join(lines)


def build_conversation_block(history: list[dict[str, Any]], max_turns: int = MAX_TURNS) -> str:
    """生成可注入 LLM prompt 的「历史上下文」块。

    - 历史为空时返回空串（prompt 中不出现任何历史相关文字）。
    - 非空时附带中文说明头，提示模型这是此前对话、需据此回答追问 / 续问。
    """
    transcript = format_conversation(history, max_turns=max_turns)
    if not transcript:
        return ""
    return (
        "以下是你与这位游客此前的对话记录（用于理解追问 / 续问，"
        "请据此连贯回答后续行程问题，不要假装没聊过）：\n"
        f"{transcript}\n"
    )


# --------------------------------------------------------------------------- #
# 模块级单例：app.py 直接复用，避免重复实例化
# --------------------------------------------------------------------------- #

chat_store = ChatHistoryStore()
