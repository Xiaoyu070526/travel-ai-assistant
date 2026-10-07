"""攻略生成 Prompt 模板与结构化输出 schema（Day 6-7）。

- :data:`SYSTEM_PROMPT`：系统提示，定义角色、约束与输出 schema。
- :func:`build_user_prompt`：把「游客上下文 + 知识库信息」组装成用户消息。
- :func:`parse_guide_json`：从模型原始输出中提取并解析 JSON。
- :func:`validate_guide`：校验结构化攻略的必填字段。

设计要点
--------
Prompt 强调「只使用知识库信息、不编造、不确定就标注需人工确认」，
输出的 JSON 面向后续 Streamlit 卡片渲染，字段稳定、可扩展。
"""

from __future__ import annotations

import json
import re
from typing import Any

from src.utils.errors import GuideGenerationError

# --------------------------------------------------------------------------- #
# 结构化输出的最外层必填字段（顺序即文档顺序）
# --------------------------------------------------------------------------- #

REQUIRED_GUIDE_FIELDS = (
    "title",
    "destination",
    "booking",
    "transport",
    "alternatives",
    "emergency",
    "notice",
)

#: Prompt 需要从上下文 / 知识库中读取的字段
CONTEXT_KEYS = (
    "nationality",
    "arrival_date",
    "chinese_level",
    "language",
    "output_language",
    "city",
    "attraction",
    "passport_booking_status",
    "reservation_required",
    "entry_method",
    "alternative_attraction_ids",
    "source_url",
    "updated_at",
)

# --------------------------------------------------------------------------- #
# Prompt 模板
# --------------------------------------------------------------------------- #

SYSTEM_PROMPT = """你是一名专业、谨慎的「入境旅游助手」，帮助到访中国的外国游客规划单个景点的游玩攻略。

请严格遵守以下规则：
1. 只使用用户消息中提供的「知识库信息」生成攻略，绝不编造知识库中没有的信息。
2. 涉及预约、购票、护照、开放时间、票价等动态/真实信息时必须非常谨慎：
   - 知识库中对应字段为 null、unknown 或缺失时，说明该信息尚未核实；
   - 此时必须在对应步骤中明确写出「需人工确认」，并提示「请以官方最新信息为准」；
   - 绝不猜测或编造预约规则、购票渠道、开放时间、票价。
3. 输出面向外国游客：使用简单、清晰、可执行的语言；输出语言严格遵循
   用户消息中 output_language 字段指定的语言（如 English / French / Japanese /
   Korean / 中文），不要混用其它语言。当 output_language 为中文时，全篇使用中文；
   否则全篇使用指定语言，景点、地点等专有名词可附中文原文。
4. 官方来源提示：如果知识库提供了 source_url 请引用；没有时明确提示
   「请通过景点官方渠道（官网 / 官方公众号 / 官方 App）确认」。
5. 输出必须是**合法的 JSON 对象**，严格符合下面的 schema，
   不要输出任何 JSON 之外的文字、解释或 Markdown 代码块标记。

输出 JSON 结构（字段含义）：
{
  "title": "攻略标题（简短）",
  "destination": {"city": "城市名", "attraction": "景点名"},
  "booking": {
    "passport_status": "supported | not_supported | unknown（沿用知识库）",
    "status_label": "面向游客的一句话购票/预约状态说明",
    "steps": [{"step": 1, "action": "动作", "note": "补充说明"}],
    "source_url": "官方来源链接，未核实时为 null"
  },
  "transport": {
    "recommended_route": "推荐路线的一句话说明",
    "steps": ["分步骤出行说明"],
    "estimated_time": "预计耗时；无法确定时写「需人工确认」"
  },
  "alternatives": [{"attraction_id": "备选景点ID", "reason": "推荐理由"}],
  "emergency": {"problem": "可能遇到的突发问题", "steps": ["应对步骤"]},
  "notice": "固定的免责提示"
}

对 booking 的额外要求：
- passport_status 一律沿用知识库中的 passport_booking_status，不要自行改写。
- 当 reservation_required 为 null 或 passport_booking_status 为 unknown 时，
  status_label 必须包含「需人工确认」，且步骤中要给出「通过官方渠道确认」的动作，
  不得断言「可以 / 不可以在线用护照购票」。
- 当 source_url 为 null 时，不要编造链接，写 null 并在步骤中提示查询官方渠道。

对 transport 的额外要求：
- 若知识库只提供概括性交通说明（如「地铁与公交可覆盖主要景点」），
  不要编造具体的地铁站名、公交线路号；改为建议使用地图 App 查询实时路线，
  并把 estimated_time 标注为「需人工确认」。

对 alternatives 的额外要求：
- 只使用知识库 alternative_attraction_ids 中给出的备选景点，不要自行推荐其他景点；
  若列表为空则输出空数组 []。

对 emergency 的额外要求：
- 只描述通用场景（如预约已满、无法进入、临时闭园），给出通用应对步骤，
  不要编造具体的退款、改签等规则。
"""


# --------------------------------------------------------------------------- #
# 上下文 / Prompt 组装
# --------------------------------------------------------------------------- #


def _to_plain(value: Any) -> Any:
    """把城市/景点字典等结构拍平成可读值，便于放进 prompt。"""
    if isinstance(value, dict):
        return (
            value.get("name")
            or value.get("city_name")
            or value.get("attraction")
            or value.get("attraction_id")
            or value
        )
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    return value


def _normalize_context(context: dict[str, Any]) -> dict[str, Any]:
    """只保留 Prompt 需要的字段，并对值做拍平处理。"""
    normalized: dict[str, Any] = {}
    for key in CONTEXT_KEYS:
        if key in context:
            normalized[key] = _to_plain(context[key])
    return normalized


def build_user_prompt(context: dict[str, Any]) -> str:
    """把游客上下文 + 知识库信息组装成用户消息。

    :param context: 包含 CONTEXT_KEYS 所列字段的字典；city / attraction 既可为
        字符串也可为字典（字典会取 name / city_name）。
    """
    knowledge = json.dumps(_normalize_context(context), ensure_ascii=False, indent=2)
    return (
        "请根据以下知识库信息，为这位外国游客生成景点游玩攻略。\n\n"
        f"知识库信息：\n{knowledge}\n\n"
        "请直接输出符合 schema 的 JSON 对象，不要输出其他任何内容。"
    )


# --------------------------------------------------------------------------- #
# 结构化输出解析 / 校验
# --------------------------------------------------------------------------- #


def parse_guide_json(text: str) -> dict[str, Any]:
    """从模型原始输出中提取 JSON 对象。

    - 支持被 Markdown 代码块围栏包裹的输出；
    - 否则取第一个 ``{`` 到最后一个 ``}`` 之间的内容；
    - 解析失败或结果不是对象时抛 :class:`GuideGenerationError`。
    """
    if not isinstance(text, str) or not text.strip():
        raise GuideGenerationError("模型输出为空")

    stripped = text.strip()

    fenced = re.search(r"```(?:json)?\s*(.*?)```", stripped, re.DOTALL)
    if fenced:
        stripped = fenced.group(1).strip()
    else:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise GuideGenerationError("模型输出中找不到 JSON 对象")
        stripped = stripped[start : end + 1]

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise GuideGenerationError("模型输出的 JSON 无法解析") from exc

    if not isinstance(data, dict):
        raise GuideGenerationError("模型输出不是 JSON 对象")

    return data


def validate_guide(body: dict[str, Any]) -> None:
    """校验结构化攻略的必填字段，缺失时抛 :class:`GuideGenerationError`。"""
    missing = [field for field in REQUIRED_GUIDE_FIELDS if body.get(field) is None]
    if missing:
        raise GuideGenerationError(
            "攻略 JSON 缺少必要字段：" + ", ".join(missing)
        )
