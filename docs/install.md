# 安装指南

三种形态互不依赖，按需选一种即可。核心引擎相同。

---

## 一、独立软件

### 要求

- Python 3.8 及以上（只用标准库，不需要 pip 装任何东西）
- 能联网（AI 功能需要；纯刷题、错题、复习离线也能用）

检查：

```bash
python3 --version
```

### 安装并启动

```bash
git clone https://github.com/schvinkk/dsh-examboost-ai.git
cd dsh-examboost-ai/app
bash deploy.sh
```

脚本会检查环境、准备目录、启动服务、尝试打开浏览器，最后打印本机与局域网地址。

常用参数：

```bash
bash deploy.sh --port 8080              # 换端口
bash deploy.sh --data-dir ~/my-study    # 数据放别处，升级程序不会覆盖
bash deploy.sh --no-open                # 不自动开浏览器
```

不想用脚本，直接跑也可以：

```bash
cd app && python3 server.py --port 3000
```

启动时会打印：

```
ExamBoost AI v1.0.0 已启动
  本机访问   : http://localhost:3000
  手机/平板  : http://192.168.x.x:3000  （需同一 WiFi）
  内置题库   : 323 题，用户题库 0 题
  AI 模型    : Kilo 免费网关（推荐）
```

最后一行就是当前生效的 AI 通道。显示「未检测到」时看下面的排障。

### 停止 / 重启 / 看日志

```bash
kill $(cat ~/ExamBoost/server.pid)     # 停止
bash deploy.sh                          # 重启（会自动先停旧实例）
tail -f ~/ExamBoost/server.log          # 日志
```

### 手机端

1. 手机与电脑连同一个 WiFi
2. 手机浏览器打开部署结束时打印的局域网地址
3. 浏览器菜单 →「添加到主屏」，之后从桌面图标进入就是全屏独立窗口（PWA）

Android 上如果用 Termux 之类的环境跑服务，`deploy.sh` 会自动尝试 `termux-open-url`。

### Windows

没有 bash 的话，装 Python 后在项目目录打开命令行：

```
cd app
python server.py
```

然后浏览器访问 `http://localhost:3000`。

---

## 二、Skill

不需要安装任何东西，复制文本给 AI 就行。

### 手机 / 网页聊天

1. 打开 [dist/examboost-full.md](../dist/examboost-full.md)
2. 全选复制，发给你的 AI（DSH、Kimi、豆包、通义千问、Claude Code 等）
3. 后面加一句：`请按这些规则辅导我备考`

单文件版已经把 12 个模块参考合并进去了，不用另外找 references 文件。

### Claude Code / Codex

```bash
git clone https://github.com/schvinkk/dsh-examboost-ai.git
cp -r dsh-examboost-ai/skills/examboost ~/.claude/skills/    # Claude Code
cp -r dsh-examboost-ai/skills/examboost ~/.agents/skills/    # Codex
```

目录结构：

```
skills/examboost/
├── SKILL.md              主规则
├── references/           12 个模块参考
│   ├── xingce.md  shenlun.md  zhice.md  zongying.md
│   ├── gongji.md  gongwen.md  interview.md  shizheng.md
│   ├── baokao.md  k12.md  review.md  study.md
└── scripts/deploy.md     让 AI 照着部署独立软件的说明
```

### Kimi / 豆包 / 通义千问

各家入口名称不同，思路一致：找到「技能 / Skill / 自定义指令」入口，把 SKILL.md 内容（或 dist 单文件）粘进去，或上传 `skills/examboost` 目录。

---

## 三、dsh-go 原生插件

给 DSH 手机 App 的原生界面加学习入口。

### 安装

```bash
dsh plugin --profile web add /绝对路径/dsh-examboost-ai/dsh-go-plugin
```

装上即生效，不用重启引擎。

### 会出现什么

| 位置 | 内容 |
|------|------|
| 输入框上方胶囊 | 「抽一题」「讲这题」 |
| 长按 AI 回复的菜单 | 「记入错题本」 |
| 输入框上方状态条 | 今日待复习数、错题数、正确率 |
| 对话详情页 / 全部功能 | 学习看板、错题本、今日复习三个面板 |

面板里的按钮可以直接把题目塞进输入框，让当前对话的 AI 带你做。

### 数据来源

插件不另存一份数据，直接读独立软件写在 `app/data/` 的 JSON 文件。它会按顺序探测这些位置，取第一个存在的：

```
$EXAMBOOST_DATA                       环境变量，优先级最高
~/ExamBoost/data                      deploy.sh 的默认落点
~/.examboost/data
~/dsh-examboost-ai/app/data
~/AI空间/ExamBoost-AI/app/data         手机上常见的存放位置
<当前工作目录>/data
<当前工作目录>/app/data
```

独立软件装在别的地方时，设一下环境变量再重启引擎：

```bash
export EXAMBOOST_DATA=/你的路径/data
```

没找到数据目录时，面板会显示一句提示让你先部署独立软件，不会假装自己有数据。

### 校验与卸载

```bash
# 校验（需要 DSH 自带的 dsh-go-plugin 技能）
node ~/.dsh/skills/dsh-go-plugin/kit/bin/check.mjs ./dsh-go-plugin --load

# 卸载
dsh plugin --profile web remove local-examboost
```

---

## 排障

| 现象 | 处理 |
|------|------|
| 端口被占用 | `deploy.sh` 会自动改用邻近端口并打印实际端口；也可以 `--port 8080` 指定 |
| 浏览器没自动打开 | 手动访问启动日志里打印的地址 |
| 手机打不开局域网地址 | 确认同一 WiFi；电脑防火墙放行该端口；路由器开了 AP 隔离就关掉 |
| 顶栏显示「AI 未就绪」 | 检查网络；或设置 → 模型接入 → 填自己的 OpenAI 兼容 Base URL |
| AI 出题等很久 | 匿名免费池高峰期会排队，正常 10-60 秒；换自己的模型最快 |
| 刷新页面还是旧版 | 已修（Service Worker 走网络优先）；仍异常就浏览器强制刷新 Ctrl+Shift+R |
| 改了 `lib/index.js` 插件没反应 | 原生插件的 JS 改动需要在 App「引擎」页重启引擎 |
| 想清空学习数据 | 设置 → 数据 → 清空学习数据（会二次确认），或直接备份后删 `app/data/` |
| 题库文件报错 | `python3 tools/validate_bank.py` 自检 |

### 手动验证服务是否正常

```bash
curl http://localhost:3000/api/health
curl http://localhost:3000/api/status
curl http://localhost:3000/api/ai/providers
```

`/api/ai/providers` 会列出每一路通道的可用性与失败原因，AI 有问题先看这里。
