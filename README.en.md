# ExamBoost AI

> High-Efficiency Study & Exam Prep Tool · Covers General Learning + Chinese Civil Service Exams
>
> One-Click Deploy · Plugin + Skill + Standalone App (Triple Form)

**English | [中文](README.md)**

---

## 🎯 What is this

**ExamBoost AI** is an AI-powered high-efficiency study & exam prep tool covering:

- **General Learning**: material parsing, knowledge extraction, spaced repetition, mastery tracking
- **Civil Service / Public Institution Exams**: Xingce, Shenlun, Zhice, Zongying, Gongji, Gongwen, Interview, Current Affairs, Application Guidance

### Triple Form

| Form | Description | For |
|------|-------------|-----|
| 📦 **Plugin** | Install into DSH / Kimi / Doubao AI apps | Users who want full integration |
| 📄 **Skill** | Download and give to any AI | Users who don't want plugins |
| 🖥️ **Standalone App** | Ask AI to auto-deploy as local app | Users who want standalone experience |

---

## ✨ Features

### 📚 General Learning
- Multi-format material parsing (PDF / Word / PPT / Markdown / images)
- Auto knowledge point extraction & structuring
- Spaced repetition (SM-2 / FSRS)
- Mastery tracking (BKT model)
- Mistake book & error attribution

### 🎯 Civil Service / Public Institution Exams
- **Xingce**: politics, general knowledge, verbal, quantitative, logical reasoning, data analysis
- **Shenlun**: summarization, analysis, countermeasures, implementation, essay writing
- **Zhice**: public institution aptitude test
- **Zongying**: A-E category training
- **Gongji**: public foundation knowledge
- **Gongwen**: document types, formatting, error correction
- **Interview**: structured questions, scoring, reference frameworks
- **Current Affairs**: hot topic tracking
- **Application**: major → position matching, competition analysis

### 🔄 Exam Prep Efficiency Engine
- Past exam analysis & topic weight calculation
- Weak point identification & priority sorting
- Personalized learning path generation
- Progress prediction & adjustment

### 📦 Cloud Drive Material Search (Full Material Channels)
- One-click search across public cloud drive shares for study materials (past papers, courseware, courses, notes, etc.)
- Aggregates PanSeek / PanHub / PanSou / PanXiaozi open-source cloud drive search services, covering Aliyun Drive, Quark, Baidu, 115, Xunlei, etc.
- Search-to-result in one step; supports self-hosted local search (Docker one-click deploy)
- Cloud drive material favorites: save found material links for later use
- Import found materials into "Generate Quiz Tool": AI creates questions and generates an offline quiz webpage

---

## 🚀 Install & Use

### Method 1: DSH Plugin

```bash
dsh plugin --profile web add github:yourname/dsh-examboost-ai
```

### Method 2: Skill (All AI Apps)

Copy [`dist/examboost-full.md`](dist/examboost-full.md) content to your AI and say:

> Please guide my exam prep according to these rules

### Method 3: Standalone App Deployment

Tell your AI:

> Deploy ExamBoost to my local machine

---

## 📥 Download & Use Quick Guide (Which Package, How to Use)

> This repository is a **triple-form** repo containing the plugin, Skill, and standalone app. **You don't need to download everything** — pick the one that suits you best. All three forms share the same core engine with equivalent features.

| What you want | Which package / directory | How to use |
|---------------|--------------------------|------------|
| Use directly inside **DSH / Kimi / Doubao** AI apps | `dsh-plugin/` (plugin form) | Run `dsh plugin --profile web add github:yourname/dsh-examboost-ai` to install; restart the AI app to use in sidebar/chat |
| **No plugin** — paste rules to any AI | `dist/examboost-full.md` (full Skill, single file, all references included) | Copy the full text to your AI (DSH, Kimi, Doubao, Tongyi Qianwen, Claude Code, etc.) and add: "Please guide my exam prep according to these rules" |
| Want a **standalone app**, use like an app on browser/phone | `app/` (standalone form) | Tell your AI "Deploy ExamBoost to my local machine"; it runs `app/deploy.sh`, opens the browser automatically, and is accessible from phones on the same WiFi |
| Want to **view full source and docs** | Whole repo | `git clone` and follow the step-by-step guide in [docs/GUIDE.md](docs/GUIDE.md) |

> How to choose? Want convenience → plugin; want quick trial → Skill; want a standalone UI and local AI → standalone app. All three share the same core engine and can be switched anytime.

## 🧱 Project Foundation & Credits

ExamBoost AI is **not built from scratch, nor is it a simple copy**. It is built on top of excellent open-source projects through **integration, optimization, and innovation**:

- **Positioning**: integrates the strengths of multiple open-source projects + optimization/fusion + innovation (offline quiz tool generator, resource center, local AI compute, all-grade universal adaptation, private-tutor-style full-process assistance), forming one comprehensive exam-prep system covering all grades and subjects.
- **Plugins & Skills borrowed**: borrows from **48** open-source projects covering civil service exams, general learning, quizzes/exams, K12, cloud drive search, etc. **Every project's author and license is credited by name in [CREDITS.md](CREDITS.md)**. No project source code is copied; only its design ideas and approaches are referenced. Released under MIT.
- **Technical foundation**: backend Python 3 standard library `http.server` (no third-party dependencies, ready to run); frontend native HTML/CSS/JS (responsive + PWA); DSH plugin built on the DeepSeek Harness plugin spec.

> Full credits and licenses: [CREDITS.md](CREDITS.md); comparison with similar projects: [docs/COMPARISON.md](docs/COMPARISON.md).

---

## 🔑 Keywords

exam prep, study, AI, civil service, kaogong, xingce, shenlun, flashcards, spaced repetition, mistake book

---

## 📄 License

[MIT License](LICENSE)
