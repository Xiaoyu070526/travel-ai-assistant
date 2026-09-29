# 旅游AI助手 - 队友入职指南

欢迎加入！以下是你需要完成的环境配置步骤。

## 一、前提条件

你需要自备：
- **Python**（不需要单独装，conda 会自带）
- **一台能访问国内网络的电脑**

## 二、环境安装

### 步骤1：安装 Miniconda

访问 [清华大学 Miniconda 镜像页](https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/)，下载对应系统的最新版安装包，安装时**勾选 "Add to PATH"**。

### 步骤2：创建虚拟环境

打开终端（CMD / Git Bash / PowerShell），执行：

```bash
conda create -n travel_ai_assistant python=3.10 -y
conda activate travel_ai_assistant
```

### 步骤3：安装项目依赖

在项目根目录（包含 `requirements.txt` 的目录）执行：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

> 如果 `gradio` 安装报错，额外执行：`pip install "huggingface_hub==0.25.2"`

## 三、申请 API Key（每人独立）

**⚠️ 重要：API Key 是个人账户凭证，不共享、不入 Git。**

### 1. 通义千问 API Key

1. 访问 [阿里云百炼平台](https://bailian.console.aliyun.com)
2. 用支付宝/淘宝账号登录（免费注册）
3. 开通"百炼"服务
4. 进入 **我的资源** → **API-Key 管理** → **创建我的 API-Key**
5. 复制 Key（以 `sk-` 开头）

### 2. 高德地图 API Key

1. 访问 [高德开放平台](https://lbs.amap.com)
2. 注册开发者账号，完成实名认证
3. 进入 **控制台 → 应用管理 → 我的应用** → **创建新应用**
4. 在应用下 **添加 Key**：服务平台选 **"Web服务"**，类型选 **"Web服务API"**
5. 复制 Key（一串字母数字混合，无 `sk-` 前缀）

## 四、配置环境变量

在项目根目录找到 `.env.example` 文件，**复制一份重命名为 `.env`**，填入你申请到的两个 Key：

```
DASHSCOPE_API_KEY=sk-你的通义千问Key粘贴到这里
AMAP_MAP_KEY=你的高德地图Key粘贴到这里
```

> `.env` 已被 `.gitignore` 排除，永远不会进入版本库。

## 五、验证环境

```bash
python test_env.py
```

正常输出：
```
[Python] 当前版本: 3.10.x
[依赖包] 所有核心依赖安装成功
[.env] 环境变量文件存在
[通义千问API] Key已配置
[高德地图API] Key已配置
环境检查完成！
```

## 六、启动应用

```bash
streamlit run src/app.py
```

浏览器打开提示的 `http://localhost:8501` 即可。

---

## 协作规范

| 规则 | 说明 |
|------|------|
| **代码入 Git** | 所有 `.py`、配置、文档通过 Git 推送共享 |
| **Key 不入 Git** | `.env` 永远本地保留，队友各自申请自己的 |
| **问卷数据不入 Git** | `data/raw/` 放原始数据，已被 `.gitignore` 排除 |
| **CI 自动检查** | 每次 push / PR 会跑 flake8 + pytest，确保代码质量 |

## 常见问题

**Q：队友能不能直接用我的 Key？**
A：技术上可以，但强烈不建议。Key 绑定你的阿里云/高德账号，调用量计费也在你头上。每个人用自己的最干净。

**Q：streamlit 端口被占用怎么办？**
A：`streamlit run src/app.py --server.port 8502` 换一个端口。

**Q：高德接口返回 "INVALID_USER_KEY"？**
A：Key 未激活或权限未开通。确认应用下选的是 **Web服务** 平台，且账号已完成实名认证。