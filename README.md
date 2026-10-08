# 旅游AI助手项目

基于 DeepSeek（Anthropic-compatible 接口）与高德地图的入境旅游助手，提供城市与景点推荐、行程规划、途中求助和旅行方案 PDF 下载。

## 环境要求

- Python 3.10（通过 conda 虚拟环境管理）
- Miniconda / Anaconda
- Git

## 快速开始

```bash
# 1. 激活虚拟环境
conda activate travel_ai_assistant

# 2. 安装依赖（国内镜像加速）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 配置 API Key
# 复制 .env.example 为 .env 并填入你的 Key：
#   ANTHROPIC_AUTH_TOKEN=你的DeepSeekKey
#   AMAP_MAP_KEY=你的高德地图Key

# 4. 验证代码（先安装开发测试工具）
pip install pytest
python -m pytest tests/ -q

# 5. 启动应用
streamlit run src/app.py
```

## 完整旅行方案与 PDF 下载

1. 在身份页填写到达日期、旅行天数（1–7 天）、人数、房间数、全团预算、兴趣、节奏与住宿位置。
2. 城市和景点按本地知识库的兴趣匹配排序，仍可自主选择；进入「行程规划」。
3. 选择日期、景点，按实际需要修改每晚住宿、每天餐饮／市内交通、住宿晚数与现金备用假设。
4. 点击「保存基础旅行方案（无需 AI）」；有 DeepSeek 配置时也可生成 AI 时间安排建议。
5. 查看保存的方案，在下方点击「下载完整旅行方案 PDF」。内容包括每日景点、天气与衣物、全团预算、住宿与交通准备、行李、入境／退税官方确认清单、景点详情、来源与免责声明。

方案和 PDF 只保存在当前 Streamlit 会话的服务器内存中，不写入用户数据库，重新连接可能丢失。下载点击和页面重运行不会重新请求 AI；修改需求、费用假设、天气或景点后，旧方案会标记为过期，需重新保存／生成才能下载。

### 范围与限制

- 预算的住宿、餐饮和交通是可修改假设，门票来自知识库成人参考价；未知门票不会按免费处理。现金备用不重复加到费用中。未含国际／城际交通、保险和购物等未录入费用。
- 人流、排队与游玩时长是规则估算。按每天日期和节奏分配，包含用餐休息、城区往返与换乘缓冲；长城、兵马俑、迪士尼按独立日安排。优先满足知识库明确的周闭馆限制，再均衡各天负荷、聚合同区域景点。交通缓冲只是规划假设，不是实时导航；开放日期及节假日例外仍需官方核实。
- 轻松／适中／紧凑每日负荷上限分别约 8／10／12 小时（含交通和休息），不代表当天必须用满。景点总时长已计入一次排队，AI 不应重复加上排队。单次最多规划 8 个景点；超出容量或日期限制的景点明确列为未安排，AI 生成按钮暂时禁用，基础 PDF 仍可导出。
- 未接入实时酒店库存、订房交易和路线优化；提供比较平台、地图入口与核实提示。
- 不判断免签资格，不计算退税金额；政策由用户通过移民、使领馆、税务及海关官方渠道核实。
- 没有对应日期天气预报时标注未知，不编造精确天气。
- 中英日静态方案可用，法／韩静态文案沿用英文回退，AI 输出遵循语言选择。

### PDF 字体与依赖

`reportlab` 已加入 `requirements.txt`。Windows 自动优先使用本地 Noto Sans SC／黑体，日文尝试 MS Gothic，韩文尝试 Malgun。找不到可嵌入字体时使用 ReportLab CJK 字体回退；为了跨设备可靠显示，部署时建议设置 `TRAVEL_PDF_FONT_PATH` 为涵盖输出语言的 TrueType `.ttf`（字体由部署者合法提供）。导出不会下载远程字体。

离线排版样例：`python tests/render_plan_samples.py`，中文样例在 `output/pdf/`，其他语言 QA 样例在 `tmp/pdfs/`，均不提交到 Git。页面测试使用 Streamlit `AppTest`（1.28+）；PDF 文本 QA 若安装了 PyMuPDF 会执行提取检查，应用运行本身无需 PyMuPDF。

## 目录结构

```
travel-ai-assistant/
│-- requirements.txt
│-- .env                          # 环境变量配置（不提交到Git）
│-- .gitignore                    # Git忽略规则
│-- README.md                     # 项目说明
│-- data/
│   |-- raw/                      # 原始问卷数据
│   |-- processed/                # 清洗后数据
│   |-- analysis/                 # 分析结果
│-- docs/                         # 项目文档
│-- src/
│   |-- app.py                    # Streamlit主应用
│   |-- api/
│   |   |-- llm_client.py         # DeepSeek API调用
│   |   |-- amap.py               # 高德地图API调用
│   |-- utils/
│   |   |-- config.py             # 配置管理
│   |   |-- data_loader.py        # 数据加载
│   |   |-- travel_plan.py        # 统一旅行方案、预算和逐日分配
│   |   |-- pdf_export.py         # 内存 PDF 导出
│-- tests/                        # 单元测试
│-- notebooks/                    # 数据分析Notebook
│-- logs/                         # 日志文件
```

## CI/CD

项目已配置 GitHub Actions（`.github/workflows/ci.yml`），每次 push / PR 自动运行 flake8 代码检查与 pytest 测试。

## 常用命令

| 操作 | 命令 |
|------|------|
| 激活环境 | `conda activate travel_ai_assistant` |
| 安装依赖 | `pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| 启动应用 | `streamlit run src/app.py` |
| 环境验证 | `python test_env.py` |
| 推送代码 | `git add . && git commit -m "信息" && git push` |
