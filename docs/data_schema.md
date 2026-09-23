# 数据结构设计（Day 3）

本文档描述 `data/processed/` 下三个 JSON 数据文件的结构，以及 `src/utils/data_loader.py` 的读取约定。

## 1. 目录与文件

```
data/processed/
├── cities.json        # 城市
├── attractions.json   # 景点
└── apps.json          # App
```

## 2. 通用文件结构

三个文件都采用「元信息 + 数据列表」的结构：

```json
{
  "_meta": {
    "schema_version": "0.1.0",
    "data_type": "sample",
    "note": "示例数据说明……",
    "created_at": "2026-09-23",
    "updated_at": "2026-09-23"
  },
  "cities": [ { ... }, { ... } ]
}
```

- `_meta`：数据集元信息（版本、是否示例数据、字段约定、时间戳）。**读取函数不会返回 `_meta`**，只返回数据列表。
- 数据列表的键名分别是 `cities` / `attractions` / `apps`。
- `data_loader` 兼容顶层直接是列表的写法（`[ { ... } ]`），便于后续接入简单数据源。
- 文件编码统一为 **UTF-8**，读写均不转义中文。

## 3. `cities.json`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `city_id` | string | 城市唯一标识（主键），英文小写短横线风格，如 `beijing` |
| `city_name` | string | 城市中文名，如 `北京` |
| `description` | string | 城市简介 |
| `transport` | string | 市内交通的通用说明 |
| `tips` | string[] | 出行提示列表 |
| `app_ids` | string[] | 关联的 App ID，对应 `apps.json` 的 `app_id` |
| `attraction_ids` | string[] | 关联的景点 ID，对应 `attractions.json` 的 `attraction_id` |

## 4. `attractions.json`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `attraction_id` | string | 景点唯一标识（主键） |
| `city_id` | string | 所属城市，对应 `cities.json` 的 `city_id` |
| `name` | string | 景点名称 |
| `description` | string | 景点简介 |
| `reservation_required` | bool \| null | 是否需要预约；`null` 表示尚未核实 |
| `passport_booking_status` | string | 护照预订支持情况，取值：`supported` / `not_supported` / `unknown` |
| `entry_method` | string \| null | 入场方式；`null` 表示尚未核实 |
| `alternative_attraction_ids` | string[] | 备选景点 ID，可用于「首选约满时推荐替代项」 |
| `source_url` | string \| null | 信息来源链接；`null` 表示尚无已核实来源 |
| `updated_at` | string | 本条记录更新时间（`YYYY-MM-DD`） |

## 5. `apps.json`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `app_id` | string | App 唯一标识（主键） |
| `name` | string | App 名称 |
| `category` | string | 分类，如 `支付`、`地图导航`、`出行打车` |
| `description` | string | 功能简介 |
| `download_links` | object | 下载链接，键为 `ios` / `android` / `official_website`，值为 string \| null |

## 6. 示例数据说明（重要）

`data/processed/` 下的数据目前全部是 **示例数据（sample data）**，用途是打通开发与测试流程，**不是真实的旅游信息**。

因此，凡涉及真实世界事实、需要核实才能确定的字段，**一律留空而不做编造**：

- `reservation_required` / `entry_method` / `source_url` 固定为 `null`
- `passport_booking_status` 固定为 `"unknown"`
- `download_links` 中的链接固定为 `null`

`description` / `transport` / `tips` 等字段只包含通用说明性文字，不含票价、开放时间、预约规则等具体信息。

后续接入官方数据源（或人工核实）后，再逐步填充上述字段，并同步更新 `updated_at` 与 `_meta.updated_at`。

## 7. 读取模块 `src/utils/data_loader.py`

| 函数 | 返回 | 说明 |
| --- | --- | --- |
| `load_cities()` | `list[dict]` | 读取全部城市 |
| `get_city(city_id)` | `dict \| None` | 按 ID 查询城市，找不到返回 `None` |
| `load_attractions()` | `list[dict]` | 读取全部景点 |
| `get_attractions_by_city(city_id)` | `list[dict]` | 查询某城市的景点，无结果返回 `[]` |
| `get_attraction(attraction_id)` | `dict \| None` | 按 ID 查询景点 |
| `load_apps()` | `list[dict]` | 读取全部 App |
| `get_app(app_id)` | `dict \| None` | 按 ID 查询 App |
| `get_attractions_by_ids(ids)` | `list[dict]` | 批量按 ID 查询景点，保持传入顺序 |
| `get_apps_by_ids(ids)` | `list[dict]` | 批量按 ID 查询 App，保持传入顺序 |

所有函数都接受可选的 `data_dir` 参数，用于在测试中指到临时目录。

### 错误处理约定

| 情况 | 行为 |
| --- | --- |
| 数据文件不存在 | 抛 `DataFileNotFoundError`（同时是 `DataLoadError` 和标准库的 `FileNotFoundError`） |
| JSON 格式非法 | 抛 `DataLoadError` |
| 顶层缺少约定字段 / 字段类型不对 | 抛 `DataLoadError` |
| 按 ID 查询但 ID 不存在 | 返回 `None`（列表查询返回 `[]`），**不抛异常** |

「文件缺失」和「记录不存在」被有意区分开：前者说明数据文件没生成好，属于部署/构建问题，应当尽早暴露；后者是正常的业务情况，交给调用方决定如何展示。

## 8. 运行测试

在项目根目录执行：

```bash
python -m unittest discover -s tests -t . -v
```

测试使用标准库 `unittest`，无需额外安装依赖。若已安装 pytest，也可运行：

```bash
pytest tests -v
```

Windows 控制台若出现中文乱码，可先设置编码：

```bash
set PYTHONIOENCODING=utf-8
```
