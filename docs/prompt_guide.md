# 攻略生成 Prompt 说明（Day 6）

本文档说明「入境旅游搭子」攻略生成所用的 Prompt 模板、结构化输出 schema、
输出样例与使用方式。代码实现位于 `src/api/prompts.py`（模板 + 解析/校验）
与 `src/api/llm_client.py`（调用与 fallback）。

## 1. 目标

把「景点知识库 + 游客上下文」转成一份**结构化 JSON 攻略**，供后续
Streamlit 用卡片逐块渲染（买票、路线、备选、应急），而不是一大段纯文本。

## 2. Prompt 接收的上下文

`build_user_prompt(context)` 会把以下字段（存在才注入）拍平后以 JSON 注入用户消息：

| 字段 | 说明 |
| --- | --- |
| `nationality` | 游客国籍 |
| `arrival_date` | 到达日期 |
| `chinese_level` | 中文水平 |
| `city` | 城市（字符串，或字典会取 `city_name`） |
| `attraction` | 景点（字符串，或字典会取 `name`） |
| `passport_booking_status` | 护照预订支持情况：`supported` / `not_supported` / `unknown` |
| `reservation_required` | 是否需要预约：`bool` / `null` |
| `entry_method` | 入场方式：`string` / `null` |
| `alternative_attraction_ids` | 备选景点 ID 列表 |
| `source_url` | 信息来源链接：`string` / `null` |
| `updated_at` | 知识库记录更新时间 |

`city` / `attraction` 可直接传 `data_loader` 返回的字典，`build_user_prompt`
会自动取可读名称。

## 3. Prompt 强调的硬约束

- **只使用知识库信息**，不编造知识库中没有的内容。
- 预约 / 购票 / 护照 / 开放时间 / 票价等**动态真实信息必须谨慎**：
  `null` / `unknown` / 缺失 → 明确写「**需人工确认**」并提示「请以官方最新信息为准」。
- 不确定时不得断言「可以 / 不可以在线用护照购票」。
- 给出**官方来源提示**：有 `source_url` 引用它，没有就提示查官方渠道。
- **面向外国游客**：简单、清晰、可执行；默认英文输出，专有名词可附中文。
- 只输出**合法 JSON**，不含多余文字或 Markdown 围栏。

## 4. 结构化输出 schema

模型输出的是**攻略正文**（不含 `status`，`status` 由客户端包裹）。
字段如下：

```json
{
  "title": "攻略标题（简短）",
  "destination": { "city": "城市名", "attraction": "景点名" },
  "booking": {
    "passport_status": "supported | not_supported | unknown",
    "status_label": "面向游客的一句话状态说明",
    "steps": [{ "step": 1, "action": "动作", "note": "补充说明" }],
    "source_url": "官方来源链接或 null"
  },
  "transport": {
    "recommended_route": "推荐路线的一句话说明",
    "steps": ["分步骤出行说明"],
    "estimated_time": "预计耗时；不确定则写「需人工确认」"
  },
  "alternatives": [{ "attraction_id": "备选景点ID", "reason": "推荐理由" }],
  "emergency": { "problem": "可能遇到的突发问题", "steps": ["应对步骤"] },
  "notice": "固定的免责提示"
}
```

### 字段含义（供 Streamlit 卡片渲染）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `title` | string | 卡片标题 |
| `destination.city` / `.attraction` | string | 目的地定位 |
| `booking.passport_status` | string | 沿用知识库的 `passport_booking_status`，不改写 |
| `booking.status_label` | string | 购票/预约的一句话结论，unknown 时必须含「需人工确认」 |
| `booking.steps[]` | object[] | 买票/预约步骤，`step`/`action`/`note` |
| `booking.source_url` | string\|null | 官方来源链接，未核实为 `null` |
| `transport.recommended_route` | string | 推荐路线一句话 |
| `transport.steps[]` | string[] | 出行分步骤 |
| `transport.estimated_time` | string | 预计耗时，不确定标「需人工确认」 |
| `alternatives[]` | object[] | 备选景点，只取知识库 `alternative_attraction_ids` |
| `emergency.problem` / `.steps[]` | string / string[] | 应急话术 |
| `notice` | string | 免责提示，固定为「信息仅供参考，以官方最新信息为准」 |

### 稳定性 / 扩展性约定

- 最外层 7 个字段（`title`/`destination`/`booking`/`transport`/`alternatives`/`emergency`/`notice`）
  由 `REQUIRED_GUIDE_FIELDS` 校验，缺失即判定生成失败并走 fallback。
- 需要新增卡片时，**新增字段而不是删改旧字段**；旧字段保持不变，卡片渲染向后兼容。
- `status` 由客户端包裹（`success` / `fallback`），模型不产出，避免模型自行决定状态。

## 5. 完整输出样例

见 `docs/guide_output_example.json`（北京 + 故宫）。样例用于展示结构，**不虚构真实
购票政策**：`reservation_required` / `entry_method` / `source_url` 均为 `null`，
`passport_booking_status` 为 `unknown`，购票步骤明确写「需人工确认」。

## 6. 使用方式

```python
from src.utils import data_loader
from src.api.llm_client import generate_guide

city = data_loader.get_city("beijing")
attraction = data_loader.get_attraction("beijing-forbidden-city")

context = {
    "nationality": "USA",
    "arrival_date": "2026-10-01",
    "chinese_level": "none",
    "city": city,          # dict，自动取 city_name
    "attraction": attraction,  # dict，自动取 name
    "passport_booking_status": attraction["passport_booking_status"],
    "reservation_required": attraction["reservation_required"],
    "entry_method": attraction["entry_method"],
    "alternative_attraction_ids": attraction["alternative_attraction_ids"],
    "source_url": attraction["source_url"],
    "updated_at": attraction["updated_at"],
}

result = generate_guide(context)   # 永远返回 dict，不抛异常
print(result["status"])            # success 或 fallback
```

- 返回 `status == "success"` 时按第 4 节字段渲染卡片；
- 返回 `status == "fallback"` 时直接渲染 fallback 文案（见 `docs/api.md`）。

## 7. 调整输出语言的说明

默认输出英文（面向外国游客）。如需改为中文，只需修改
`src/api/prompts.py` 中 `SYSTEM_PROMPT` 第 3 条的「默认用英文输出」表述，
不影响 schema 与解析逻辑。
