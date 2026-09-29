# 队友接管：创建 GitHub 仓库并推送代码

> 本指南面向负责将本项目推送到 GitHub 的队友。你已拿到本地源码和完整的协作包，按照以下步骤操作即可在 10 分钟内完成仓库创建与首次推送。

---

## 前置信息

- **项目本地路径**：`D:\Projects\travel-ai-assistant`（或队友已自行放置的任意路径）
- **Git 状态**：项目已初始化本地仓库，有 10 次提交历史，无需从零创建
- **仓库建议命名**：`travel-ai-assistant`
- **可见性建议**：Private（项目含业务内容，后续再决定开源）
- **已排除的敏感文件**：`.env`（含 API Key）已被 `.gitignore` 排除，不会上传

---

## 第 1 步：创建 GitHub 仓库（约 2 分钟）

1. 浏览器打开 https://github.com/new
2. 填写仓库信息：
   - **Repository name**：`travel-ai-assistant`
   - **Description**：旅游 AI 助手项目 - 基于通义千问 + 高德地图的智能旅行规划应用
   - **Visibility**：选择 **Private**（私有）或 **Public**（公开）
   - **⚠️ 重要**：**不要勾选**以下三项（本地已有对应文件，勾选会产生冲突）：
     - [ ] Add a README file
     - [ ] Add .gitignore
     - [ ] Choose a license
3. 点击 **Create repository**

---

## 第 2 步：配置 SSH 密钥（约 3 分钟）

### 2.1 生成 SSH 密钥（如已生成过可跳过）

打开 Git Bash（或 Terminal），执行：

```bash
# 生成 ed25519 密钥（推荐）
ssh-keygen -t ed25519 -C "你的邮箱@example.com"

# 按三次回车（使用默认路径，不设置密码）
```

### 2.2 添加公钥到 GitHub

1. 复制公钥内容：
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```
   输出类似：`ssh-ed25519 AAAA... 你的邮箱@example.com`

2. 登录 GitHub → 右上角头像 → **Settings** → 左侧 **SSH and GPG keys**
3. 点击 **New SSH key**
   - Title：随意，如 `my-pc` 或 ` teammate-laptop`
   - Key：粘贴上一步复制的公钥全文
4. 点击 **Add SSH key**

### 2.3 测试连接

```bash
ssh -T git@github.com
```

首次连接会提示确认指纹，输入 `yes`，看到 `Hi xxx! You've successfully authenticated` 即成功。

---

## 第 3 步：本地仓库关联远程并推送（约 2 分钟）

### 3.1 绑定远程仓库

在项目目录下打开终端（Git Bash / CMD / PowerShell），执行：

```bash
cd D:\Projects\travel-ai-assistant

# 将 "你的GitHub用户名" 替换为实际的 GitHub ID（英文）
git remote add origin git@github.com:你的GitHub用户名/travel-ai-assistant.git
```

**示例**：如果你的 GitHub 用户名是 `zhangsan`，命令为：
```bash
git remote add origin git@github.com:zhangsan/travel-ai-assistant.git
```

### 3.2 验证远程地址

```bash
git remote -v
```

应输出：
```
origin  git@github.com:你的GitHub用户名/travel-ai-assistant.git (fetch)
origin  git@github.com:你的GitHub用户名/travel-ai-assistant.git (push)
```

### 3.3 推送代码

```bash
# 确认当前分支名
# 如主分支不是 main，执行：git branch -M main

# 首次推送（-u 建立上游跟踪关系）
git push -u origin main
```

---

## 第 4 步：添加队友为协作者（约 1 分钟）

1. 打开 GitHub 仓库页面：`https://github.com/你的用户名/travel-ai-assistant`
2. 点击 **Settings** → 左侧 **Manage access**（或 **Collaborators**）
3. 点击 **Add people** → 输入队友的 GitHub 用户名或邮箱
4. 选择权限级别：
   - **Write**（推荐）：允许推送代码、创建 PR
   - **Admin**：允许管理仓库设置
5. 队友会收到邮件邀请，接受后即有写权限

---

## 第 5 步：队友拉取仓库（其他队员后续操作）

仓库推送完成后，其他队友无需再处理本地仓库，直接克隆即可：

```bash
# 克隆仓库（替换为你的 GitHub 用户名）
git clone git@github.com:你的GitHub用户名/travel-ai-assistant.git

# 进入项目目录
cd travel-ai-assistant

# 按 teammate-setup.md 完成环境搭建和 .env 配置
```

---

## 常见问题排查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `Permission denied (publickey)` | SSH 密钥未添加到 GitHub | 重新执行第 2 步，确认公钥已粘贴 |
| `fatal: remote origin already exists` | 远程地址已绑定 | 先执行 `git remote remove origin`，再重新添加 |
| `rejected: non-fast-forward` | 远程仓库已有提交 | 如仓库为空则不可能出现；如有 README 等文件，先 `git pull origin main --allow-unrelated-histories` 合并 |
| `Could not resolve hostname` | 网络问题或 SSH 配置错误 | 检查网络，或改用 HTTPS：`git remote set-url origin https://github.com/你的用户名/travel-ai-assistant.git` |

---

## 快捷参考卡

```bash
# 一次性复制执行（修改用户名后）
cd D:\Projects\travel-ai-assistant
git remote add origin git@github.com:你的GitHub用户名/travel-ai-assistant.git
git branch -M main
git push -u origin main
```

---

## 推送后检查清单

- [ ] GitHub 仓库页面能看到所有文件（确认 .env 不在其中）
- [ ] `README.md` 正确渲染
- [ ] `teammate-setup.md` 存在（其他队友入职指南）
- [ ] Settings → Manage access 已添加所有队友
- [ ] 队友能成功执行 `git clone git@github.com:你的用户名/travel-ai-assistant.git`

---

*文档版本：v1.0 | 生成时间：2026-09-23*
