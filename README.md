# ExamBoost AI

综合备考学习工具。一套系统覆盖考公考编、考研、四六级、K12、职业资格与自学，提供三种用法：装进 AI 应用的插件、复制即用的 Skill、以及部署在本机的独立软件。

**中文 | [English](README.en.md)**

---

## 这是什么

三种形态共用同一套学习引擎，功能等价，可以按需选一种，也可以混着用：

| 形态 | 位置 | 适合谁 |
|------|------|--------|
| 🖥️ 独立软件 | `app/` | 想要一个真正的刷题应用，手机电脑都能用 |
| 📄 Skill | `skills/examboost/` + `dist/examboost-full.md` | 不想装任何东西，复制规则发给 AI 就用 |
| 📦 dsh-go 插件 | `dsh-go-plugin/` | 在 DSH 手机 App 里直接看进度、抽题、记错题 |

## 快速开始

### 独立软件（推荐先试这个）

需要 Python 3.8+，除此之外不装任何依赖。

```bash
git clone https://github.com/schvinkk/dsh-examboost-ai.git
cd dsh-examboost-ai/app
bash deploy.sh
```

浏览器会自动打开 `http://localhost:3000`。手机连同一个 WiFi，访问部署结束时打印的局域网地址即可；在浏览器菜单里选「添加到主屏」，它就像一个独立 App。

也可以对你的 AI 说一句「帮我把 ExamBoost 部署到本地」，它会照着 [docs/GUIDE.md](docs/GUIDE.md) 做完这些步骤。

### Skill

把 [dist/examboost-full.md](dist/examboost-full.md) 全文复制发给你的 AI（DSH、Kimi、豆包、通义千问、Claude Code 等都可以），加一句「请按这些规则辅导我备考」。

想装成真正的 skill 目录：

```bash
git clone https://github.com/schvinkk/dsh-examboost-ai.git
cp -r dsh-examboost-ai/skills/examboost ~/.claude/skills/    # Claude Code
cp -r dsh-examboost-ai/skills/examboost ~/.agents/skills/    # Codex
```

### dsh-go 插件

在 DSH 手机 App 的本机环境里：

```bash
dsh plugin --profile web add /绝对路径/dsh-examboost-ai/dsh-go-plugin
```

装完立刻生效。输入框上方会出现「抽一题」「讲这题」两个胶囊，长按 AI 回复可以「记入错题本」，输入框上方的状态条实时显示今日待复习与错题数，「全部功能」里有学习看板、错题本、今日复习三个面板。插件直接读独立软件写在 `data/` 的那些文件，两边数据是同一份，不存在同步问题。

## 功能

### 学习引擎

- **内置题库 320 题**，全部为模拟原创题（不冒充真题），带答案与解析：
  - 考公考编 160 题：行测 90（政治理论、常识、言语、数量、判断、资料分析）、公基 30、申论 20、面试 10、时政 10
  - 考研 / 四六级 / K12 / 职业资格 / 通用 160 题
- **按条件抽题**：学段、科目、题型、难度、关键词任意组合；连续抽取自动避免重复
- **错题本**：自动记录，同一题重复答错会累计次数，可标记「已消灭」
- **间隔复习（SM-2）**：答错的题自动进入复习队列，自评记忆效果后调整下次间隔
- **掌握度追踪（BKT）**：按科目算掌握概率，低于 60% 的自动列为薄弱项，可定向只刷薄弱
- **模拟考试**：整卷计时，交卷统一判分并出逐题解析
- **学习计划**：填考试日期与每日时长，自动切分基础 / 强化 / 冲刺三阶段，附每周任务清单
- **打卡与统计**：连续天数、分科目正确率、近 7 天答题量

### AI 能力（零配置）

不需要注册、不需要填 Key。程序按顺序自动探测这几路，哪路通用哪路，失败自动回落：

1. 本机 `dsh-our-free-model` 本地转发（装了该插件并打开开关时优先用）
2. 本机 `dsh-our-free-model` 独立服务（18900）
3. **Kilo 免费网关** —— 无需凭据，29 个免费模型，默认走这条
4. Pollinations 匿名池 —— 备用，同 IP 约 45 秒一次

有了 AI 之后可以做：

- **对话辅导**：讲题、方法、框架，内置备考导师提示词
- **资料出题**：粘贴考纲、笔记、真题解析，让 AI 出成套选择题
- **知识点拆解**：把一段资料拆成结构化知识点清单，标出可能考法
- **逐题讲解**：刷题页一键让 AI 讲当前这道题

想用自己的模型（DeepSeek、Kimi、本地 Ollama 等 OpenAI 兼容服务），在「设置 → 模型接入」里填 Base URL 即可，会排在最优先。

### 离线刷题包

把题目打包成**单个 HTML 文件**：零依赖、双击就开、完全离线。文件内自带刷题、背题、错题、SM-2 复习、统计、进度导出导入，答题记录存在浏览器 localStorage 里，关掉再打开还在。可以直接发给同学。

### 资料渠道

- **资源中心**：内置国考专题网站、研招网、中国教育考试网、中国人事考试网、阳光高考等官方平台，以及华图、中公、粉笔等培训机构入口，可自行增删
- **网盘检索**：聚合 PanSeek、PanHub、PanSou、盘小子四个开源网盘搜索服务，输入关键词直达结果页，支持收藏

## 项目结构

```
dsh-examboost-ai/
├── app/                      # 独立软件
│   ├── server.py             # HTTP 服务与 API 路由（标准库）
│   ├── edata.py              # 存储层 + SM-2 / BKT 算法
│   ├── ellm.py               # 模型接入：探测、回落、限流重试
│   ├── eqbank.py             # 题库加载、筛选、抽题
│   ├── eqiz.py               # 离线刷题包生成器
│   ├── index.html            # 前端界面
│   ├── static/               # 样式、前端逻辑、图标
│   ├── data_bank/            # 内置题库（320 题）
│   ├── sources.json          # 资源中心信息源
│   ├── pan_search.json       # 网盘搜索服务配置
│   ├── manifest.json / sw.js # PWA
│   └── deploy.sh             # 一键部署
├── skills/examboost/         # Skill 形态
│   ├── SKILL.md              # 主规则
│   ├── references/           # 12 个模块参考（行测、申论、公基、公文、面试、时政、报考、职测、综应、K12、复习、通用学习）
│   └── scripts/deploy.md     # 供 AI 执行的部署说明
├── dist/examboost-full.md    # Skill 单文件合并版
├── dsh-go-plugin/            # DSH 手机 App 原生插件
├── docs/                     # 教程、架构、安装、对比、更新日志
├── CREDITS.md                # 借鉴的开源项目署名
└── LICENSE                   # MIT
```

## 数据与隐私

学习数据全部写在 `app/data/` 下的 JSON 文件里，程序不上传任何内容。`llm_config.json` 权限设为 0600，接口不会回显完整 Key，`/data/` 路径禁止通过网页直接访问。

需要注意：走匿名免费模型通道时，请求内容会经过第三方网关，这些服务通常会记录 prompt 用于改进模型。**不要把身份证号、账号密码这类敏感信息粘进去。** 介意这一点的话，在设置里换成自己的模型服务。

## 已知限制

- 题库 320 题是内置起步量，覆盖主要考点但不可能穷尽；支持导入自己的题目（JSON 或 AI 生成后入库）
- 申论、面试类题目采用客观化考法（给材料选最准确的一项），不是真正的写作批改
- 匿名免费池有速率限制，高峰期出题可能要等十几秒
- 离线刷题包的进度存在浏览器 localStorage，换浏览器或清缓存会丢，重要数据用「导出存档」备份

## 文档

- [docs/GUIDE.md](docs/GUIDE.md) —— 保姆级教程，每个文件在哪用、怎么用
- [docs/install.md](docs/install.md) —— 三种形态的安装细节
- [docs/architecture.md](docs/architecture.md) —— 架构与模块划分
- [docs/COMPARISON.md](docs/COMPARISON.md) —— 与同类开源项目的差异
- [docs/changelog.md](docs/changelog.md) —— 更新日志

## License

[MIT](LICENSE)。借鉴的开源项目均在 [CREDITS.md](CREDITS.md) 实名署名。
