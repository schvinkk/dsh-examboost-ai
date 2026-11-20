# ExamBoost AI

A study and exam-prep tool that covers Chinese civil service exams, postgraduate entrance exams, CET-4/6, K-12, professional certifications and self-study. One engine, three ways to use it: a plugin for AI apps, a copy-paste Skill, or a standalone app you deploy locally.

**English | [中文](README.md)**

---

## What is this

All three forms share the same engine, so features are equivalent — pick whichever fits, or mix them.

| Form | Location | Best for |
|------|----------|----------|
| 🖥️ Standalone app | `app/` | You want a real practice app on desktop and phone |
| 📄 Skill | `skills/examboost/` + `dist/examboost-full.md` | You don't want to install anything, just paste rules to an AI |
| 📦 dsh-go plugin | `dsh-go-plugin/` | You want progress, drills and mistakes inside the DSH phone app |

## Quick start

### Standalone app (recommended first try)

Requires Python 3.8+ and nothing else — no pip installs.

```bash
git clone https://github.com/schvinkk/dsh-examboost-ai.git
cd dsh-examboost-ai/app
bash deploy.sh
```

Your browser opens `http://localhost:3000`. On a phone on the same WiFi, use the LAN address printed at the end of the deploy; "Add to home screen" makes it behave like its own app.

You can also just tell your AI "deploy ExamBoost locally" and it will follow [docs/GUIDE.md](docs/GUIDE.md).

### Skill

Copy [dist/examboost-full.md](dist/examboost-full.md) in full and send it to your AI (DSH, Kimi, Doubao, Tongyi Qianwen, Claude Code, …), followed by "please guide my exam prep according to these rules".

To install it as a real skill directory:

```bash
git clone https://github.com/schvinkk/dsh-examboost-ai.git
cp -r dsh-examboost-ai/skills/examboost ~/.claude/skills/    # Claude Code
cp -r dsh-examboost-ai/skills/examboost ~/.agents/skills/    # Codex
```

### dsh-go plugin

Inside the DSH phone app's local environment:

```bash
dsh plugin --profile web add /absolute/path/to/dsh-examboost-ai/dsh-go-plugin
```

Effective immediately, no restart. Two capsules appear above the input box ("抽一题" draw a question, "讲这题" explain it), long-pressing an AI reply lets you log it into the mistake book, a status strip shows today's due reviews and open mistakes, and three panels (dashboard, mistakes, review) live under "All features". The plugin reads the same JSON files the standalone app writes under `data/`, so there is no sync step.

## Features

### Learning engine

- **320 built-in questions**, all written as original mock items (never passed off as real past papers), each with answer and explanation:
  - Civil service 160: Xingce 90 (political theory, general knowledge, verbal, quantitative, logical reasoning, data analysis), Gongji 30, Shenlun 20, Interview 10, Current affairs 10
  - Postgrad / CET / K-12 / certifications / general 160
- **Filtered drawing**: combine stage, subject, question type, difficulty and keyword; consecutive draws avoid repeats automatically
- **Mistake book**: records misses, counts repeats of the same question, supports "cleared" marking
- **Spaced repetition (SM-2)**: wrong answers enter the review queue; self-graded recall adjusts the next interval
- **Mastery tracking (BKT)**: per-subject mastery probability; anything under 60% is flagged weak and can be drilled exclusively
- **Timed mock exam**: answer a full paper under the clock, get batch grading with per-question explanations
- **Study plan**: enter exam date and daily hours, get base / intensive / sprint phases with weekly task lists
- **Streaks and stats**: consecutive days, per-subject accuracy, last 7 days of activity

### AI features (zero configuration)

No signup, no API key. The app probes these in order and falls back automatically:

1. Local `dsh-our-free-model` forward port (used first when that plugin is installed and its switch is on)
2. Local `dsh-our-free-model` standalone service (port 18900)
3. **Kilo free gateway** — no credential required, 29 free models; this is the default working path
4. Pollinations anonymous pool — backup, roughly one request per 45 seconds per IP

With AI available you can:

- **Chat for tutoring** — explanations, methods, frameworks, with a built-in exam-tutor system prompt
- **Generate questions from material** — paste a syllabus, notes or past-paper analysis and get a set of multiple-choice items
- **Extract knowledge points** — turn a passage into a structured list with likely question formats
- **Explain the current question** — one tap from the practice screen

To use your own model (DeepSeek, Kimi, local Ollama, any OpenAI-compatible endpoint), set the Base URL under Settings → Model access; it takes top priority.

### Offline quiz packages

Questions are packed into a **single HTML file**: no dependencies, double-click to open, fully offline. The file includes practice, browse, mistakes, SM-2 review, statistics, and save/load of your progress. Answers persist in browser localStorage, so closing and reopening keeps your state. Easy to send to a classmate.

### Material channels

- **Resource center**: built-in official portals (national civil service recruitment, Yanzhaowang for postgrad, NEEA for CET and teacher certification, personnel exam bureau, Gaokao platform) plus training providers (Huatu, Zhonggong, Fenbi); add or remove your own
- **Cloud drive search**: aggregates four open-source search services (PanSeek, PanHub, PanSou, PanXiaozi); type a keyword and jump straight to results, with favorites

## Project layout

```
dsh-examboost-ai/
├── app/                      # standalone app
│   ├── server.py             # HTTP server and API routes (stdlib only)
│   ├── edata.py              # storage layer + SM-2 / BKT algorithms
│   ├── ellm.py               # model access: probing, fallback, rate-limit retry
│   ├── eqbank.py             # question bank loading, filtering, drawing
│   ├── eqiz.py               # offline quiz package generator
│   ├── index.html            # UI
│   ├── static/               # styles, frontend logic, icons
│   ├── data_bank/            # built-in questions (320)
│   ├── sources.json          # resource center entries
│   ├── pan_search.json       # cloud drive search services
│   ├── manifest.json / sw.js # PWA
│   └── deploy.sh             # one-command deploy
├── skills/examboost/         # Skill form
│   ├── SKILL.md              # main rules
│   ├── references/           # 12 module references
│   └── scripts/deploy.md     # deployment instructions for AI
├── dist/examboost-full.md    # Skill, single merged file
├── dsh-go-plugin/            # DSH phone app native plugin
├── docs/                     # guide, architecture, install, comparison, changelog
├── CREDITS.md                # open-source projects referenced
└── LICENSE                   # MIT
```

## Data and privacy

All study data stays in JSON files under `app/data/`; nothing is uploaded. `llm_config.json` is chmod 0600, the API never returns a full key, and `/data/` is blocked over HTTP.

One thing to know: anonymous free model channels route your prompts through third-party gateways, which typically log requests for model improvement. **Do not paste ID numbers, passwords or similar secrets.** If that bothers you, point the app at your own model service in Settings.

## Known limitations

- 320 questions is a starting set covering the main topics, not exhaustive. You can import your own (JSON, or save AI-generated sets into the bank)
- Shenlun and interview items use objective multiple-choice framing rather than true essay grading
- Anonymous pools are rate-limited; generation may take ten-plus seconds at peak
- Offline package progress lives in browser localStorage and is lost if you clear it — use "Export save" to back up

## Docs

- [docs/GUIDE.md](docs/GUIDE.md) — step-by-step guide, what each file is for
- [docs/install.md](docs/install.md) — install details for all three forms
- [docs/architecture.md](docs/architecture.md) — modules and design
- [docs/COMPARISON.md](docs/COMPARISON.md) — how it differs from similar projects
- [docs/changelog.md](docs/changelog.md) — release history

## License

[MIT](LICENSE). Open-source projects referenced are credited by name in [CREDITS.md](CREDITS.md).
