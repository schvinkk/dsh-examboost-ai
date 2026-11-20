# ExamBoost AI 保姆级教程（完整版）

> 本教程从零开始，讲清楚**每个文件是什么、在哪里用、怎么用**。即使您完全不懂技术，照着做也能用起来。

---

## 目录

1. [文件速查表（每个文件在哪用）](#一文件速查表)
2. [形态一：DSH 插件怎么装怎么用](#形态一dsh-插件)
3. [形态二：Skill 怎么用（不装插件）](#形态二skill-怎么用)
4. [形态三：独立软件怎么部署（含手机）](#形态三独立软件)
5. [各平台安装教程](#各平台安装教程)
6. [手机/平板使用教程](#手机平板使用教程)
7. [常见问题（FAQ）](#常见问题faq)

---

## 一、文件速查表

> **重点：每个文件都有明确的用途和适用平台，按需使用，别装错。**

### 📄 Skill 文件（所有 AI 应用通用）

| 文件 | 在哪用 | 怎么用 |
|------|--------|--------|
| `skills/examboost/SKILL.md` | **所有 AI 应用**（DSH、Kimi、豆包、通义千问、Claude Code 等） | 把这个文件（或其所在的 `examboost` 文件夹）交给 AI，AI 就学会辅导备考 |
| `skills/examboost/references/study.md` | 通用学习模块 | AI 自动读取，用户无需手动操作 |
| `skills/examboost/references/xingce.md` | 行测模块 | AI 自动读取 |
| `skills/examboost/references/shenlun.md` | 申论模块 | AI 自动读取 |
| `skills/examboost/references/zhice.md` | 职测模块 | AI 自动读取 |
| `skills/examboost/references/zongying.md` | 综应模块 | AI 自动读取 |
| `skills/examboost/references/gongji.md` | 公基模块 | AI 自动读取 |
| `skills/examboost/references/gongwen.md` | 公文模块 | AI 自动读取 |
| `skills/examboost/references/interview.md` | 面试模块 | AI 自动读取 |
| `skills/examboost/references/shizheng.md` | 时政模块 | AI 自动读取 |
| `skills/examboost/references/baokao.md` | 报考咨询模块 | AI 自动读取 |
| `skills/examboost/references/review.md` | 复习与错题模块 | AI 自动读取 |
| `skills/examboost/scripts/deploy.md` | **AI 部署独立软件时** | AI 读取后自动执行部署步骤 |

> **核心理解**：SKILL.md 是"说明书"，references/ 是"各科资料库"，AI 按任务需要自动读取对应文件，用户不用手动打开。

### 📦 DSH 插件文件（仅 DeepSeek Harness 用）

| 文件 | 在哪用 | 怎么用 |
|------|--------|--------|
| `dsh-plugin/package.json` | DSH 插件安装 | 插件清单，声明插件信息 |
| `dsh-plugin/cordis.patch.yml` | DSH 插件挂载 | 告诉 DSH 如何挂载本插件 |
| `dsh-plugin/index.js` | DSH 宿主端 | 提供工具、HTTP 接口（服务端） |
| `dsh-plugin/client.js` | DSH 客户端 | 客户端界面入口（界面开发中，当前为占位） |

> **用法**：这三个形态文件**不需要手动打开**，通过 `dsh plugin add github:yourname/dsh-examboost-ai` 一键安装。

### 🖥️ 独立软件文件（本地/浏览器/手机用）

| 文件 | 在哪用 | 怎么用 |
|------|--------|--------|
| `app/server.py` | 本地服务器 | 启动本地服务，提供 Web 界面（AI 自动调用） |
| `app/index.html` | 浏览器/手机 | Web 界面，浏览器自动打开 |
| `app/deploy.sh` | AI 部署脚本 | AI 执行它来自动部署整个软件 |
| `app/manifest.json` | 手机 PWA | 手机"添加到主屏"用 |
| `app/sw.js` | 离线缓存 | 断网也能用 |
| `app/sources.json` | 资源中心 | 内置 11 个考试信息源（公告/考纲/培训） |
| `app/pan_search.json` | 网盘搜 | 内置 4 个网盘搜索服务及自建命令 |
| `app/static/icon.svg` | 手机/浏览器图标 | 应用图标 |

> **用法**：`deploy.sh` 是总入口，AI 执行它就会自动装好一切。用户不用手动操作。

### 📤 发布文件（给用户看的）

| 文件 | 在哪用 | 怎么用 |
|------|--------|--------|
| `README.md` | GitHub 首页 | 项目说明（用户搜到后先看这个） |
| `README.en.md` | GitHub 英文版 | 英文说明 |
| `CREDITS.md` | 版权署名 | 借鉴来源与作者（尊重版权） |
| `LICENSE` | 开源协议 | MIT |
| `dist/examboost-full.md` | **手机/网页用户** | 复制全文发给 AI 即可用 |
| `docs/install.md` | 安装指南 | 各平台安装步骤 |
| `docs/GUIDE.md` | **本教程** | 保姆级教程 |

---

## 二、形态一：DSH 插件

> 适用：使用 **DeepSeek Harness（DSH）** 的用户。安装后插件集成到 DSH，提供工具 + 界面。

### 怎么装（3 步）

**第 1 步：确认已装 DSH**
```
如果还没装 DSH，先按官方教程装好（需要 Node.js 20+）
```

**第 2 步：安装插件**
```bash
# Web 版
dsh plugin --profile web add github:yourname/dsh-examboost-ai

# 桌面版
dsh plugin --profile desktop add github:yourname/dsh-examboost-ai
```

**第 3 步：重启并验证**
- 重启 DSH（Web 版强制刷新浏览器 Ctrl+F5）
- 侧边栏出现「ExamBoost」入口 = 安装成功

### 怎么用
- 侧边栏点「ExamBoost」进入学习面板
- 对话中直接说：「帮我出一道行测数量题」
- 或输入 `/examboost` 命令

---

## 三、形态二：Skill 怎么用（不装插件）

> 适用：**不想装插件**的用户，或使用 **Kimi、豆包、通义千问、Claude Code** 等任何 AI 应用。

### 用法 A：手机 / 网页聊天（最简单）

**第 1 步：打开单文件版**
- 打开 [`dist/examboost-full.md`](../dist/examboost-full.md)

**第 2 步：复制全文**
- 全选复制（Ctrl+A → Ctrl+C）

**第 3 步：发给你的 AI**
- 粘贴到 DSH、Kimi、豆包、通义千问等任何 AI 的输入框
- 加一句：`请按这些规则辅导我备考`

**完成！** AI 就变成您的备考导师了。

### 用法 B：Claude Code / Codex（本地客户端）

```bash
# 1. 下载项目
git clone github.com/yourname/dsh-examboost-ai.git
cd dsh-examboost-ai

# 2. 安装 Skill
cp -r skills/examboost ~/.claude/skills/
# 或 Codex：
cp -r skills/examboost ~/.agents/skills/
```

### 用法 C：Kimi Work（桌面端）

1. 打开 Kimi Work → 插件市场
2. 点「创建插件」→「从 GitHub 导入」
3. 填仓库地址：`github.com/yourname/dsh-examboost-ai`
4. 导入完成即可用

### 用法 D：豆包（电脑版）

1. 打开豆包 → 侧边栏「技能·连接器·伙伴」
2. 点「技能」→「新建」→「上传技能」
3. 选择 `skills/examboost` 文件夹（含 SKILL.md）
4. 上传完成，启用即可

### 用法 E：通义千问

1. 打开千问 → 自定义 MCP / 技能
2. 上传技能包（zip 打包 `skills/examboost`）
3. 挂载到智能体

---

## 四、形态三：独立软件

> 适用：想要**像独立 App 一样用**的用户，**电脑端和手机/平板都能用**。

### 怎么部署（只需对 AI 说一句话）

**第 1 步：把项目给 AI**
- 在 DSH / Claude Code / Kimi 等任何 AI 中，打开本项目目录

**第 2 步：对 AI 说**
```
帮我把 ExamBoost 部署到本地
```

**第 3 步：AI 自动完成**
```
[1/6] 检查环境（Python 3.8+）
[2/6] 复制文件到 ~/ExamBoost/
[3/6] 安装依赖
[4/6] 初始化数据目录
[5/6] 启动服务 http://localhost:3000
[6/6] 自动打开浏览器
✅ 部署完成！
本机访问: http://localhost:3000
手机/平板访问(同一WiFi): http://192.168.x.x:3000
```

**完成！** 浏览器自动打开 ExamBoost 界面，像独立软件一样用。

### 使用 AI 助手（本地免费模型）

独立软件默认不带 AI 算力。要让它**自己调用大模型**分析辅助（不依赖 AI 应用），接入免费模型：

**第 1 步：启动 dsh-our-free-model 独立服务**
- 方式 A（推荐）：在 `dsh-our-free-model` 仓库目录运行 `npm run start:standalone`（默认端口 18900）
- 方式 B：在 DSH 里装好该插件，启用「本地转发」（默认端口 18899）

**第 2 步：在 ExamBoost 设置页配置**
1. 打开 ExamBoost → 点「⚙️ 设置」
2. 服务地址填：`http://127.0.0.1:18900/v1`（或转发端口 18899）
3. 点「测试连接」→ 看到模型列表即成功
4. 选一个模型（如 deepseek-v4.1-flash），点「保存」

**第 3 步：使用**
- 点「🤖 AI 助手」→ 直接提问
- AI 会用免费模型分析、出题、讲解、批改

> **意义**：这样 ExamBoost 独立部署后也能自行调用大模型，不必依赖某个 AI 应用。

### 手动部署（如果 AI 没自动做）

```bash
# 1. 给部署脚本加执行权限
chmod +x app/deploy.sh

# 2. 运行
bash app/deploy.sh
```

### 电脑端怎么用
- 浏览器自动打开 `http://localhost:3000`
- 数据保存到 `~/ExamBoost/data/`

### 📦 网盘搜：找资料（资料渠道齐全）
独立软件里的「📦 网盘搜」页面，帮你在网盘上找学习资料（真题、课件、课程、笔记等）：

1. **搜索**：输入关键词（如「考研数学 真题」「公务员 行测」「高中物理」），选择搜索服务，点「搜索」直达结果（新标签页打开）
2. **内置服务**：PanSeek、PanHub、PanSou、盘小子，覆盖阿里云盘、夸克、百度、115、迅雷等全平台网盘
3. **自建服务**：想完全自己掌控，按页面里给出的 Docker 命令一键部署本地网盘搜索（默认 `localhost:4000`），部署后在服务下拉框选「本地部署」即可
4. **收藏**：搜到有用的资料，复制分享链接填到「我的网盘资料收藏」，方便以后随时打开
5. **资料→刷题闭环**：找到的资料文本，粘贴到「🛠️ 生成刷题工具」，AI 自动出题生成离线刷题网页，保存后即可刷题（见下）

### 🛠️ 生成刷题工具：资料变刷题软件
「🛠️ 生成刷题工具」页面把资料变成**单文件、双击即用**的离线刷题网页：

1. **AI 生成**：粘贴资料文本，AI 自动出题，点「生成刷题工具」下载 HTML 网页，双击打开即可刷题（支持判分、错题本、统计，数据存浏览器本地）
2. **手动导入**：会 JSON 的话直接粘贴题目 JSON，同样生成离线刷题网页

---

## 五、各平台安装教程

### 📊 总览

| 平台 | 支持形态 | 安装方式 |
|------|---------|---------|
| **DeepSeek Harness** | 插件 + Skill | `dsh plugin add github:yourname/dsh-examboost-ai` |
| **Kimi Work** | 插件（GitHub导入）+ Skill | 插件市场→从 GitHub 导入 |
| **豆包（电脑版）** | 插件 + Skill | 上传技能包 |
| **通义千问** | 插件（MCP）+ Skill | 上传技能 / MCP |
| **Claude Code** | Skill | `cp -r skills/examboost ~/.claude/skills/` |
| **Codex** | Skill | `cp -r skills/examboost ~/.agents/skills/` |
| **手机/平板浏览器** | 独立软件（局域网/PWA） | 见下节 |
| **任何聊天 AI** | Skill 单文件版 | 复制 `dist/examboost-full.md` |

---

## 六、手机/平板使用教程

> 三种方式，任选一种。

### 方式 A：手机访问电脑上的 ExamBoost（推荐）

**前提**：电脑已部署 ExamBoost（见形态三），手机和电脑连**同一个 WiFi**。

**第 1 步**：看部署完成后显示的手机地址
```
手机/平板访问(同一WiFi): http://192.168.x.x:3000
```

**第 2 步**：手机打开浏览器，输入该地址
- iPhone Safari / Android Chrome 均可
- 就能在手机上用 ExamBoost 了

### 方式 B：添加到手机主屏（PWA，像 App 一样）

**iPhone Safari**：
1. 打开 `http://电脑IP:3000`
2. 点分享按钮 →「添加到主屏幕」
3. 桌面出现 ExamBoost 图标，点开就能用

**Android Chrome**：
1. 打开 `http://电脑IP:3000`
2. 点菜单（⋮）→「添加到主屏幕」
3. 桌面出现 ExamBoost 图标

> 添加主屏后，即使断网也能用（离线缓存）。

### 方式 C：手机上直接发 Skill 给 AI

**最简单！** 手机上的 Kimi、豆包、通义千问等任何 AI：
1. 复制 [`dist/examboost-full.md`](../dist/examboost-full.md) 全文
2. 粘贴给手机上的 AI
3. 说：`请按这些规则辅导我备考`

> 手机也能用 Skill，完全不依赖电脑。

---

## 七、常见问题（FAQ）

**Q1：DHS 插件装不上？**
- 确认 DSH 版本 ≥ 0.2，Node.js ≥ 20
- 重启 DSH 后再试

**Q2：Skill 发给 AI 后没反应？**
- 确认复制了**完整全文**（从 `---` 开头到结尾）
- 加一句明确指令：`请按这些规则辅导我备考`

**Q3：手机访问不了电脑上的 ExamBoost？**
- 确认手机和电脑连**同一个 WiFi**
- 确认电脑防火墙放行 3000 端口
- 用部署完成时显示的地址（不是 localhost）

**Q4：端口 3000 被占用？**
- 修改 `app/deploy.sh` 里的 `PORT=3001`
- 或改 `app/server.py` 的 `--port`

**Q5：部署时提示没 Python？**
- 安装 Python 3.8+：`python.org/downloads`
- 或改用 Node 版（后续提供）

**Q6：想卸载 ExamBoost？**
- 独立软件：删除 `~/ExamBoost/` 目录，`kill` 对应进程
- DSH 插件：`dsh plugin --profile web remove dsh-examboost-ai`

---

## 版权与致谢

借鉴来源与作者署名见 [`CREDITS.md`](../CREDITS.md)。本项目 MIT 开源，向所有开源作者致敬。
