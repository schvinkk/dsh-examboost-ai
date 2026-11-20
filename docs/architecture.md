# 架构说明（Architecture）

## 综合型架构

```
┌─────────────────────────────────────────┐
│        通用学习引擎（所有人群都用）        │
│  资料解析 · 知识点 · 间隔复习(SM-2)       │
│  掌握度(BKT) · 错题本 · 刷题判分          │
│  学习计划 · 进度持久化                    │
└──────────────────┬──────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│ 考试适配层（按需） │  │ 效率增强（通用）   │
│ 考公/考研/四六级   │  │ 真题分析·薄弱点    │
│ 期末/证书/面试    │  │ 进度可视化·打卡   │
└──────────────────┘  └──────────────────┘
```

## 三重形态

| 形态 | 目录 | 用途 |
|------|------|------|
| DSH 插件 | `dsh-plugin/` | DeepSeek Harness 一键安装，提供工具+界面 |
| Skill | `skills/examboost/` + `dist/examboost-full.md` | 所有 AI 应用可用，不装插件也能用 |
| 独立软件 | `app/` | AI 自动部署到本地，浏览器/手机访问 |

## 核心引擎模块

| 模块 | 实现 | 借鉴来源 |
|------|------|---------|
| 间隔复习 SM-2 | `app/server.py` sm2_review() | StudyHub、lookatstudy、StudyBros |
| 掌握度 BKT | `app/server.py` bkt_update() | dsh-plugin-lookatstudy |
| 题库 | `SEED_QUESTIONS` + API | kaogong-shuati、exam-practice |
| 错题本 | `mistakes.json` + API | daan、kaogong-study-tracker |
| 学习计划 | `plan.json` + API | workbuddy、study-coach |
| 统计 | `stats.json` + API | study-coach |

## 数据存储

- 位置：`app/data/`（本地，不上传）
- 文件：`stats.json`（答题统计）、`mistakes.json`（错题本）、`knowledge.json`（BKT 掌握度）、`cards.json`（SM-2 复习卡）、`plan.json`（学习计划）、`state.json`（插件状态）、`llm_config.json`（本地 AI 配置）、`sources_custom.json`（自定义信息源）、`pan_favorites.json`（网盘搜收藏）

## 技术栈

- 后端：Python 3 标准库 `http.server`（无第三方依赖，开箱即用）
- 前端：原生 HTML/CSS/JS（无构建，响应式 + PWA）
- 部署：`app/deploy.sh`（AI 自动执行）

## 手机/平板支持

- 局域网访问：server.py 绑定 `0.0.0.0`，手机同 WiFi 访问 `http://电脑IP:3000`
- PWA：`manifest.json` + `sw.js`，可添加到主屏，离线可用
