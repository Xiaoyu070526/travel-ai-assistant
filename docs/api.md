# LLM API 客户端与错误处理（Day 6）

本文档说明 `src/api/llm_client.py` 的用途、配置、接口与异常处理约定。

## 1. 用途

封装 DeepSeek 的 **Anthropic-compatible Messages 接口**（`POST {base_url}/v1/messages`），
把「景点知识库 + 游客上下文」转成结构化攻略 JSON。底层使用 `requests`（已在
`requirements.txt` 中），未引入额外依赖。

## 2. 环境变量

所有配置从环境变量或项目根目录的 `.env` 读取（`python-dotenv`），**绝不硬编码密钥**。

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `ANTHROPIC_BASE_URL` | 否 | `https://api.deepseek.com/anthropic` | Anthropic-compatible 接口地址 |
| `ANTHROPIC_AUTH_TOKEN` | 是 | 无 | 你的 API Key（优先） |
| `ANTHROPIC_API_KEY` | 否 | 无 | 兼容别名，token 未设置时使用 |
| `ANTHROPIC_MODEL` | 否 | `deepseek-flash` | 模型名 |
| `ANTHROPIC_TIMEOUT` | 否 | `60` | 请求超时（秒） |
| `ANTHROPIC_MAX_RETRIES` | 否 | `3` | 基础重试次数 |

## 3. 配置方法

1. 复制示例文件：`cp .env.example .env`
2. 填入自己的 Key：`ANTHROPIC_AUTH_TOKEN=sk-...`
3. `.env` 已在 `.gitignore` 中，不会被提交；`ANTHROPIC_BASE_URL` 可省略使用默认值。

> **安全**：`.env` 与 `*.log`、`logs/*` 均在 `.gitignore` 中。文档里不放真实 Key。
> 代码把 token 登记到日志过滤器，任何日志输出都会把 token 替换为 `[REDACTED]`。

## 4. 函数接口

### 高层（推荐）

```python
from src.api.llm_client import generate_guide

result = generate_guide(context, client=None)  # -> dict，永不抛异常
```

### 低层

```python
from src.api.llm_client import LLMClient

client = LLMClient(
    base_url=None,     # 默认读 ANTHROPIC_BASE_URL
    auth_token=None,   # None 读环境变量；空字符串表示「明确未配置」
    model=None,
    timeout=None,
    max_retries=None,
)
text = client.complete(system, user)  # -> str，失败抛异常
guide = client.generate_guide(context)  # -> dict，失败返回 fallback
```

## 5. 输入参数（`generate_guide` 的 `context`）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `nationality` | str | 游客国籍 |
| `arrival_date` | str | 到达日期 |
| `chinese_level` | str | 中文水平 |
| `city` | str\|dict | 城市名，或 `data_loader` 的城市字典 |
| `attraction` | str\|dict | 景点名，或 `data_loader` 的景点字典 |
| `passport_booking_status` | str | `supported`/`not_supported`/`unknown` |
| `reservation_required` | bool\|null | 是否需要预约 |
| `entry_method` | str\|null | 入场方式 |
| `alternative_attraction_ids` | str[] | 备选景点 ID |
| `source_url` | str\|null | 信息来源 |
| `updated_at` | str | 记录更新时间 |

## 6. 输出 JSON

成功时（`status == "success"`）为「status 包裹 + 攻略正文」：

```json
{
  "status": "success",
  "title": "...",
  "destination": { "city": "...", "attraction": "..." },
  "booking": { "passport_status": "...", "status_label": "...", "steps": [...], "source_url": null },
  "transport": { "recommended_route": "...", "steps": [...], "estimated_time": "..." },
  "alternatives": [...],
  "emergency": { "problem": "...", "steps": [...] },
  "notice": "..."
}
```

字段详解见 `docs/prompt_guide.md` 第 4 节。

## 7. 异常类型（`src/utils/errors.py`）

| 异常 | 触发场景 | 是否可重试 |
| --- | --- | --- |
| `ConfigurationError` | API Key 未配置 | 否 |
| `APITimeoutError` | 请求超时 | 是 |
| `APIAuthenticationError` | 401 / 403（Key 无效或无权限） | 否 |
| `APIError` | 其他 HTTP 错误（4xx/5xx）或网络错误 | 429 / 5xx 可重试 |
| `APIResponseError` | 返回非 JSON / 缺少 content / 空响应 | 否 |
| `GuideGenerationError` | 模型输出无法解析为攻略 JSON / 缺字段 | 否 |

`DataLoadError` / `DataFileNotFoundError` 由 Day 3 的 `data_loader` 定义，在
`errors.py` 中 re-export，方便统一从 `src.utils.errors` 导入。

## 8. fallback 行为

`generate_guide` 捕获上述所有异常（及任何意外异常），返回统一 fallback，
**不会把异常抛给 Streamlit**：

```json
{
  "status": "fallback",
  "title": "暂时无法生成完整攻略",
  "message": "AI服务暂时不可用，请稍后重试。",
  "notice": "购票、预约和入园信息请以官方最新信息为准。"
}
```

fallback 中**不含任何编造的旅游信息**，具体错误原因记录在日志中。

## 9. 调用示例

```python
from src.utils import data_loader
from src.api.llm_client import generate_guide

attraction = data_loader.get_attraction("beijing-forbidden-city")
context = {
    "nationality": "USA",
    "arrival_date": "2026-10-01",
    "chinese_level": "none",
    "city": data_loader.get_city("beijing"),
    "attraction": attraction,
    "passport_booking_status": attraction["passport_booking_status"],
    "reservation_required": attraction["reservation_required"],
    "entry_method": attraction["entry_method"],
    "alternative_attraction_ids": attraction["alternative_attraction_ids"],
    "source_url": attraction["source_url"],
    "updated_at": attraction["updated_at"],
}

result = generate_guide(context)
if result["status"] == "success":
    print(result["title"], result["booking"]["status_label"])
else:
    print(result["title"], "->", result["message"])
```

## 10. 如何运行测试

在项目根目录执行：

```bash
python -m unittest discover -s tests -t . -v
```

测试**不真正调用 DeepSeek API**，使用 `unittest.mock` 模拟 `requests.post`，
因此无需配置 Key 也能通过。涉及的用例见 `tests/test_llm_client.py` 与
`tests/test_errors.py`。
