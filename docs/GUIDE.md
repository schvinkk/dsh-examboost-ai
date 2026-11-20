# ExamBoost AI 保姆级教程（完整版）

> 本教程从零开始，讲清楚**每个文件是什么、在哪里用、怎么用**。即使您完全不懂技术，照着做也能用起来。

---

## 目录

1. [文件速查表（每个文件在哪用）](#一文件速查表)
2. [形态一：dsh-go 插件怎么装怎么用](#二形态一dsh-go-插件)
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

### 📦 dsh-go 插件文件（DSH 手机 App 原生界面用）

| 文件 | 在哪用 | 怎么用 |
|------|--------|--------|
| `dsh-go-plugin/package.json` | 插件清单 | 声明胶囊、菜单项、状态条、面板与图标 |
| `dsh-go-plugin/cordis.patch.yml` | 挂载配置 | 告诉 DSH 引擎挂载本插件 |
| `dsh-go-plugin/lib/index.js` | 宿主端逻辑 | 读学习数据文件、画原生视图、处理点按 |

> **用法**：不需要手动打开这些文件，用 `dsh plugin --profile web add <目录>` 一键安装。插件直接读独立软件写在 `app/data/` 的数据，两边同一份，不需要同步。

### 🖥️ 独立软件文件（本地/浏览器/手机用）

| 文件 | 在哪用 | 怎么用 |
|------|--------|--------|
| `app/deploy.sh` | 部署入口 | `bash deploy.sh` 一条命令装好并启动 |
| `app/server.py` | 后端服务 | HTTP 服务与 API 路由（纯标准库） |
| `app/edata.py` | 存储层 | JSON 读写与原子替换，含 SM-2 / BKT 算法 |
| `app/eqbank.py` | 题库层 | 题库加载、筛选、防重复抽题 |
| `app/ellm.py` | 模型层 | 自动探测可用模型并逐级回落 |
| `app/eqiz.py` | 离线包生成 | 把题目打包成单 HTML 文件 |
| `app/index.html` + `static/` | 界面 | 浏览器打开即用，手机自适应 |
| `app/data_bank/*.json` | 内置题库 | 320 道题，只读，升级不覆盖用户数据 |
| `app/sources.json` | 资源中心 | 官方平台与培训机构入口 |
| `app/pan_search.json` | 网盘搜 | 4 个网盘搜索服务及自建命令 |
| `app/manifest.json` + `sw.js` | PWA | 手机「添加到主屏」，断网可开 |
| `app/data/` | 学习数据 | 运行时自动生成，不上传 |

> **用法**：`deploy.sh` 是总入口，用户只需要它；其余文件由服务自己调用。

### 🛠️ 开发工具

| 文件 | 用途 |
|------|------|
| `tools/validate_bank.py` | 校验内置题库（字段、选项前缀、答案与解析一致性、去重）：`python3 tools/validate_bank.py` |

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

## 二、形态一：dsh-go 插件

> 适用：使用 **DSH 手机 App（dsh-go）** 的用户。装完在原生界面里就能抽题、看进度、记错题，不用切到网页版。

### 怎么装（3 步）

**第 1 步：拿到项目目录**

```bash
git clone https://github.com/schvinkk/dsh-examboost-ai.git
```

**第 2 步：安装插件**

在 DSH 的本机环境里执行（路径换成你 clone 的位置）：

```bash
dsh plugin --profile web add /绝对路径/dsh-examboost-ai/dsh-go-plugin
```

装上即生效，不用重启引擎。

**第 3 步：验证**

- 输入框上方出现「抽一题」「讲这题」两个胶囊 = 成功
- 长按 AI 助手的回复，菜单里出现「记入错题本」
- 「全部功能」里能看到「学习看板」「错题本」「今日复习」

### 怎么用

| 想做什么 | 操作 |
|----------|------|
| 随手练一题 | 点「抽一题」，题目自动填进输入框，发送即可 |
| 让 AI 讲当前这题 | 把题目放在输入框，点「讲这题」 |
| 做错的题记下来 | 长按 AI 的讲解回复 →「记入错题本」 |
| 看今天该复习什么 | 点输入框上方的状态条，打开学习看板 |

### 数据从哪来

插件不自己存数据，直接读独立软件写在 `app/data/` 的 JSON 文件。所以：

1. 先部署独立软件（见第四节），或
2. 用环境变量指定数据位置：`export EXAMBOOST_DATA=/你的路径/data`，然后在 App「引擎」页重启引擎

没找到数据时，面板会明确提示「还没有找到学习数据」，不会显示假数字。

### 卸载

```bash
dsh plugin --profile web remove local-examboost
```

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
git clone github.com/schvinkk/dsh-examboost-ai.git
cd dsh-examboost-ai

# 2. 安装 Skill
cp -r skills/examboost ~/.claude/skills/
# 或 Codex：
cp -r skills/examboost ~/.agents/skills/
```

### 用法 C：Kimi Work（桌面端）

1. 打开 Kimi Work → 插件市场
2. 点「创建插件」→「从 GitHub 导入」
3. 填仓库地址：`github.com/schvinkk/dsh-examboost-ai`
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
[1/5] 检查运行环境…
  ✓ Python 3.12（纯标准库，无需 pip 安装任何依赖）
[2/5] 准备程序目录…
  ✓ 已复制到 /root/ExamBoost
  · 学习数据目录：/root/ExamBoost/data
[3/5] 检查端口 3000…
  ✓ 端口可用
[4/5] 启动服务…
  ✓ 已启动（PID 12345，端口 3000）
[5/5] 访问地址…
======================================
  ✅ 部署完成
  本机     : http://localhost:3000
  手机/平板: http://192.168.x.x:3000  （需同一 WiFi）
  停止服务 : kill $(cat /root/ExamBoost/server.pid)
======================================
```

**完成！** 浏览器自动打开 ExamBoost 界面，像独立软件一样用。

### AI 功能：开箱即用，不用配置

ExamBoost 会自己找能用的模型，按这个顺序探测，哪路通用哪路，失败自动换下一路：

| 顺序 | 通道 | 需要做什么 |
|------|------|-----------|
| 1 | 你自己填的服务 | 可选。设置里填 Base URL 就排到最前 |
| 2 | 本机 `dsh-our-free-model` 本地转发（18899） | 装了该插件并打开开关时自动用 |
| 3 | 本机 `dsh-our-free-model` 独立服务（18900） | 同上 |
| 4 | **Kilo 免费网关** | 什么都不用装，联网就能用（29 个免费模型） |
| 5 | Pollinations 匿名池 | 备用，同 IP 约 45 秒一次 |

所以**部署完直接就能用**：AI 助手对话、资料出题、知识点拆解、逐题讲解都不需要注册、不需要 Key、不需要先装别的插件。顶栏右侧的紫色小条会显示当前实际生效的是哪一路。

想换成自己的模型（DeepSeek、Kimi、本地 Ollama 等任何 OpenAI 兼容端点）：设置 → 模型接入 → 填 Base URL → 测试连接 → 保存。

> **提醒**：匿名免费通道会把请求经过第三方网关，这类服务通常会记录 prompt。不要把身份证号、账号密码等敏感内容粘进去。介意就换成自己的模型服务。

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
3. **自建服务**：想完全自己掌控，页面里给出了每个服务的 Docker 部署命令，本机跑起来后直接访问它的地址即可（这些服务都是开源项目，见 `app/pan_search.json` 里的仓库链接）
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
| **DSH 手机 App（dsh-go）** | 原生插件 + Skill + 独立软件 | `dsh plugin --profile web add ./dsh-go-plugin` |
| **DSH 网页版 / 桌面版** | Skill + 独立软件 | 复制 `dist/examboost-full.md`，或跑 `app/deploy.sh` |
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

**Q1：dsh-go 插件装不上？**
- 路径要用绝对路径：`dsh plugin --profile web add /绝对路径/dsh-examboost-ai/dsh-go-plugin`
- 装完不用重启引擎；改了 `lib/index.js` 才需要在 App「引擎」页重启
- 面板显示「还没有找到学习数据」时，先部署独立软件，或设 `EXAMBOOST_DATA` 指向数据目录

**Q2：Skill 发给 AI 后没反应？**
- 确认复制了**完整全文**（从第一行 `---` 到结尾）
- 加一句明确指令：`请按这些规则辅导我备考`

**Q3：手机访问不了电脑上的 ExamBoost？**
- 确认手机和电脑连**同一个 WiFi**
- 确认电脑防火墙放行该端口
- 用部署完成时显示的局域网地址（不是 localhost）
- 路由器开了「AP 隔离」要关掉，否则设备之间不通

**Q4：端口 3000 被占用？**
- `deploy.sh` 会自动改用邻近端口并在日志里打印实际端口
- 想固定住：`bash deploy.sh --port 8080`

**Q5：部署时提示没 Python？**
- Debian/Ubuntu：`sudo apt-get install -y python3`
- macOS：`brew install python3`
- Windows：去 python.org 装，然后 `python server.py`

**Q6：AI 功能完全没反应 / 顶栏显示「AI 未就绪」？**
- 先看服务启动日志最后一行，它写了当前用的是哪路模型
- 浏览器里访问 `http://localhost:3000/api/ai/providers`，会列出每一路的可用性与失败原因
- 最常见是没有外网：匿名通道需要联网
- 有网络还不行就在设置里填自己的服务地址

**Q7：AI 出题转很久？**
- 匿名免费池高峰期排队，10-60 秒属正常；资料长、题量大更久
- 想快就在设置里换成自己的模型服务

**Q8：改了代码刷新页面还是旧的？**
- 已修：页面导航走网络优先，不再被 Service Worker 缓存挡住
- 仍异常就强制刷新（Ctrl+Shift+R）

**Q9：想卸载 ExamBoost？**
- 独立软件：`kill $(cat ~/ExamBoost/server.pid)` 然后删 `~/ExamBoost/`
- 数据想留就先备份：浏览器访问 `http://localhost:3000/api/export` 下载完整学习数据
- dsh-go 插件：`dsh plugin --profile web remove local-examboost`

**Q10：题目是真考题吗？**
- 不是。内置 320 题全部标注「模拟原创题」，按考纲编写，不冒充真题，也不提供所谓真题回忆版
- 想练自己的题：生成页粘贴 JSON 导入，或让 AI 根据你的资料出题后「存进我的题库」

---

## 版权与致谢

借鉴来源与作者署名见 [`CREDITS.md`](../CREDITS.md)。本项目 MIT 开源，向所有开源作者致敬。
