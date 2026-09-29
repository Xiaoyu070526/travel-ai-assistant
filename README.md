# 旅游AI助手项目

基于大模型（通义千问）与地图服务（高德）的旅游智能助手，提供问卷数据分析与个性化旅游推荐能力。

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
#   DASHSCOPE_API_KEY=你的通义千问Key
#   AMAP_MAP_KEY=你的高德地图Key

# 4. 验证环境
python test_env.py

# 5. 启动应用
streamlit run src/app.py
```

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
│   |   |-- qwen.py               # 通义千问API调用
│   |   |-- amap.py               # 高德地图API调用
│   |-- utils/
│   |   |-- config.py             # 配置管理
│   |   |-- data_loader.py        # 数据加载
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