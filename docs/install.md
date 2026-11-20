# 安装指南（Install Guide）

## 方式一：DSH 插件

### 环境要求
- DeepSeek Harness (DSH) 0.2.x 或更高
- Node.js 20+（与插件 package.json engines 一致）

### 安装
```bash
dsh plugin --profile web add github:yourname/dsh-examboost-ai
# 桌面版用 desktop profile
dsh plugin --profile desktop add github:yourname/dsh-examboost-ai
```

装完重启 DSH（Web 版强制刷新浏览器 Ctrl+F5）。

### 使用
- 侧边栏出现「ExamBoost」入口
- 对话中可直接说「帮我出一道行测数量题」
- `/examboost` 命令可用

## 方式二：Skill 直接使用（推荐给不装插件的用户）

### 手机 / 网页聊天
1. 打开 [`dist/examboost-full.md`](dist/examboost-full.md)（单文件版）
2. 复制全文发给你的 AI
3. 加一句「请按这些规则辅导我备考」

### Claude Code / Codex
```bash
git clone github.com/yourname/dsh-examboost-ai.git
cd dsh-examboost-ai
cp -r skills/examboost ~/.claude/skills/
# 或 Codex：
cp -r skills/examboost ~/.agents/skills/
```

### Kimi / 豆包 / 通义千问
- Kimi Work：插件市场 → 从 GitHub 导入 `yourname/dsh-examboost-ai`
- 豆包：技能上传 → 选择 `skills/examboost` 文件夹（含 SKILL.md）
- 千问：MCP 商店 / 自定义 MCP + 技能上传

## 方式三：独立软件部署

对你的 AI 说：
```
帮我把 ExamBoost 部署到本地
```

AI 将读取 `skills/examboost/scripts/deploy.md`，执行 `app/deploy.sh`，自动完成：
1. 环境检查（Python 3.8+）
2. 复制文件到 `~/ExamBoost/`
3. 检查依赖（后端仅用 Python 标准库，无第三方依赖）
4. 初始化数据目录
5. 启动服务 → 自动打开浏览器 `http://localhost:3000`

### 手机/平板访问

部署完成后会显示手机访问地址（如 `http://192.168.1.100:3000`）：
1. 手机连接到与电脑相同的 WiFi
2. 手机浏览器打开该地址，即可使用
3. 也可点击「添加到主屏」，像独立 App 一样使用（PWA）

### AI 助手（本地免费模型）

独立软件可接入 **dsh-our-free-model**（Ebony-Vinyl）自行调用免费大模型（DeepSeek V4.1 Flash、Kimi K3 等），不依赖 AI 应用：
1. 在 `dsh-our-free-model` 仓库运行 `npm run start:standalone`（默认端口 18900），或 DSH 插件启用「本地转发」（18899）
2. ExamBoost「设置」→ 填服务地址 → 测试连接 → 选模型 → 保存
3. 「AI 助手」页直接提问

> 免费模型无需登录/Key，但免费池可能记录 prompt，请勿发送敏感内容。

## 排障

| 问题 | 解决 |
|------|------|
| 端口占用 | 修改 `app/server.py` 中 PORT 或 `app/deploy.sh` 中 PORT |
| Python 未安装 | 安装 Python 3.8+，或改用 Node 版 |
| 浏览器未自动打开 | 手动访问 `http://localhost:3000` |
| DSH 插件未生效 | 重启 DSH，确认 package.json 已声明 dsh.bundle.patch |
