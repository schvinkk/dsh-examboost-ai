#!/usr/bin/env python3
"""ExamBoost AI 本地服务器 - 综合备考学习引擎
启动后提供 Web 界面与 REST API，用户通过浏览器/手机访问。
数据保存在本地 data/ 目录，不上传任何内容。

核心功能：
- 题库：出题、判分、解析
- 错题本：记录、错因归因、二刷
- 间隔复习：SM-2 调度
- 知识点：抽取、掌握度（BKT）
- 学习计划：按考试日期排阶段
- 统计：准确率、掌握度、进度
"""
import json
import os
import sys
import socket
import argparse
import random
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
PORT = 3000

# 默认示例题库（综合型：覆盖通用 + 考公考编）
SEED_QUESTIONS = [
    {
        "id": "q_001",
        "subject": "行测",
        "type": "判断推理",
        "knowledge": "图形推理",
        "question": "从所给四个选项中，选择最合适的一个填入问号处，使之呈现一定规律：○△□ / △□○ / □○△ 问号处应填？",
        "options": ["A. ○", "B. △", "C. □", "D. 无法确定"],
        "answer": "A",
        "explanation": "题干图形按 ○△□ 循环排列，每行整体左移一位，问号处回到 ○。选 A。",
        "difficulty": 1,
        "source": "模拟原创题"
    },
    {
        "id": "q_002",
        "subject": "行测",
        "type": "数量关系",
        "knowledge": "数学运算",
        "question": "某班有 40 名学生，其中 25 人会游泳，18 人会打篮球，既会游泳又会打篮球的有 10 人。问既不会游泳也不会打篮球的有几人？",
        "options": ["A. 5", "B. 6", "C. 7", "D. 8"],
        "answer": "C",
        "explanation": "容斥原理：40 - (25 + 18 - 10) = 40 - 33 = 7。选 C。",
        "difficulty": 1,
        "source": "模拟原创题"
    },
    {
        "id": "q_003",
        "subject": "行测",
        "type": "言语理解",
        "knowledge": "逻辑填空",
        "question": "依次填入横线处最恰当的一项是：他做事十分______，从不拖泥带水，深受同事信赖。",
        "options": ["A. 拖沓", "B. 果断", "C. 犹豫", "D. 敷衍"],
        "answer": "B",
        "explanation": "'从不拖泥带水'提示做事利落，'果断'最契合。选 B。",
        "difficulty": 1,
        "source": "模拟原创题"
    },
    {
        "id": "q_004",
        "subject": "申论",
        "type": "归纳概括",
        "knowledge": "要点提炼",
        "question": "请根据给定材料，概括'基层减负'的具体举措。要求：全面、准确，不超过 150 字。",
        "options": [],
        "answer": "（开放题，按要点采分）",
        "explanation": "按要点采分制评分，每个得分点关联材料证据。",
        "difficulty": 2,
        "source": "模拟原创题"
    },
    {
        "id": "q_005",
        "subject": "考研政治",
        "type": "选择题",
        "knowledge": "马原",
        "question": "马克思主义哲学认为，物质的唯一特性是？",
        "options": ["A. 运动性", "B. 客观实在性", "C. 可知性", "D. 矛盾性"],
        "answer": "B",
        "explanation": "物质的唯一特性是客观实在性。选 B。",
        "difficulty": 1,
        "source": "模拟原创题"
    },
    {
        "id": "q_006",
        "subject": "英语",
        "type": "词汇",
        "knowledge": "高频词",
        "question": "The word 'abandon' most nearly means?",
        "options": ["A. 坚持", "B. 放弃", "C. 改进", "D. 收集"],
        "answer": "B",
        "explanation": "abandon 意为'放弃、抛弃'。选 B。",
        "difficulty": 1,
        "source": "模拟原创题"
    },
]


def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return default
    return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def get_lan_ip():
    """获取本机局域网 IP（手机/平板可访问）"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def sm2_review(repetitions, interval, ease, quality):
    """SM-2 间隔复习算法
    quality: 0-5 回答质量
    """
    if quality >= 3:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 3
        else:
            interval = round(interval * ease)
        repetitions += 1
    else:
        repetitions = 0
        interval = 1
    ease = max(1.3, ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    return repetitions, interval, ease


def bkt_update(prob, correct):
    """BKT 掌握度更新（简化）
    prob: 当前掌握概率 0-1
    correct: 是否答对
    学习概率 0.3，猜对 0.2，粗心 0.1
    """
    p_learn, p_guess, p_slip = 0.3, 0.2, 0.1
    if correct:
        new_p = (prob * (1 - p_slip)) / (prob * (1 - p_slip) + (1 - prob) * p_guess)
    else:
        new_p = (prob * p_slip) / (prob * p_slip + (1 - prob) * (1 - p_guess))
    return round(min(0.99, max(0.01, new_p)), 3)


class ExamBoostHandler(SimpleHTTPRequestHandler):
    """静态文件 + REST API 处理器"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_DIR), **kwargs)

    # ---------- 工具方法 ----------
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}

    # ---------- GET ----------
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/health":
            self.send_json({"ok": True, "app": "ExamBoost", "time": datetime.now().isoformat()})
        elif path == "/api/status":
            self.handle_status()
        elif path == "/api/questions":
            self.handle_get_questions()
        elif path == "/api/mistakes":
            self.handle_get_mistakes()
        elif path == "/api/review":
            self.handle_get_review()
        elif path == "/api/knowledge":
            self.handle_get_knowledge()
        elif path == "/api/plan":
            self.handle_get_plan()
        elif path == "/api/stats":
            self.handle_get_stats()
        elif path == "/api/llm/config":
            self.handle_get_llm_config()
        elif path == "/api/llm/test":
            self.handle_llm_test()
        elif path == "/api/sources":
            self.handle_get_sources()
        elif path == "/api/pan-search":
            self.handle_get_pan_search()
        elif path == "/":
            self.path = "/index.html"
            super().do_GET()
        else:
            super().do_GET()

    # ---------- POST ----------
    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/api/answer":
            self.handle_answer()
        elif path == "/api/mistakes":
            self.handle_add_mistake()
        elif path == "/api/review":
            self.handle_submit_review()
        elif path == "/api/knowledge":
            self.handle_add_knowledge()
        elif path == "/api/plan":
            self.handle_generate_plan()
        elif path == "/api/llm/config":
            self.handle_save_llm_config()
        elif path == "/api/llm/chat":
            self.handle_llm_chat()
        elif path == "/api/llm/test":
            self.handle_llm_test()
        elif path == "/api/sources":
            self.handle_add_source()
        elif path == "/api/generate-tool":
            self.handle_generate_tool()
        elif path == "/api/pan-search":
            self.handle_add_pan_favorite()
        elif path == "/api/generate-from-text":
            self.handle_generate_from_text()
        elif path == "/api/reset":
            self.handle_reset()
        else:
            self.send_json({"error": "未知接口"}, 404)

    # ---------- 业务处理 ----------
    def handle_status(self):
        state = load_json(DATA_DIR / "state.json", {})
        mistakes = load_json(DATA_DIR / "mistakes.json", [])
        knowledge = load_json(DATA_DIR / "knowledge.json", {})
        stats = load_json(DATA_DIR / "stats.json", {"total": 0, "correct": 0})
        self.send_json({
            "initialized": True,
            "total_questions": len(SEED_QUESTIONS),
            "total_mistakes": len(mistakes),
            "total_knowledge": len(knowledge),
            "stats": stats,
            "version": "0.2.1",
        })

    def handle_get_questions(self):
        params = self._parse_query()
        subject = params.get("subject", "")
        qtype = params.get("type", "")
        knowledge = params.get("knowledge", "")
        questions = SEED_QUESTIONS
        if subject:
            questions = [q for q in questions if q["subject"] == subject]
        if qtype:
            questions = [q for q in questions if q["type"] == qtype]
        if knowledge:
            questions = [q for q in questions if knowledge in q["knowledge"]]
        if not questions:
            self.send_json({"questions": [], "total": 0})
            return
        q = random.choice(questions)
        self.send_json({"questions": [q], "total": len(questions)})

    def handle_answer(self):
        payload = self.read_body()
        qid = payload.get("id", "")
        answer = payload.get("answer", "")
        subject = payload.get("subject", "")
        knowledge_tag = payload.get("knowledge", "")
        correct_answer = payload.get("correct_answer", "")
        ans = str(answer).strip().upper()
        correct = str(correct_answer).strip().upper()
        # correct_answer 为空时不判对，避免空答案误判
        is_correct = bool(correct) and ans == correct

        # 更新统计
        stats = load_json(DATA_DIR / "stats.json", {"total": 0, "correct": 0})
        stats["total"] = stats.get("total", 0) + 1
        if is_correct:
            stats["correct"] = stats.get("correct", 0) + 1
        save_json(DATA_DIR / "stats.json", stats)

        # 更新掌握度（BKT）
        knowledge = load_json(DATA_DIR / "knowledge.json", {})
        if subject:
            if subject not in knowledge:
                knowledge[subject] = {"prob": 0.2, "mastered": False}
            knowledge[subject]["prob"] = bkt_update(knowledge[subject]["prob"], is_correct)
            knowledge[subject]["mastered"] = knowledge[subject]["prob"] >= 0.8
        save_json(DATA_DIR / "knowledge.json", knowledge)

        # 记录错题
        if not is_correct:
            mistakes = load_json(DATA_DIR / "mistakes.json", [])
            mistakes.append({
                "id": f"m_{int(time.time()*1000)}",
                "subject": subject,
                "knowledge": knowledge_tag,
                "question": payload.get("question", ""),
                "answer": answer,
                "correct_answer": correct_answer,
                "reason": payload.get("reason", "未分类"),
                "status": "待复习",
                "created": datetime.now().isoformat(),
            })
            save_json(DATA_DIR / "mistakes.json", mistakes)

        self.send_json({"ok": True, "correct": is_correct, "stats": stats})

    def handle_get_mistakes(self):
        mistakes = load_json(DATA_DIR / "mistakes.json", [])
        self.send_json({"mistakes": mistakes, "total": len(mistakes)})

    def handle_add_mistake(self):
        payload = self.read_body()
        mistakes = load_json(DATA_DIR / "mistakes.json", [])
        mistakes.append({
            "id": f"m_{int(time.time()*1000)}",
            "subject": payload.get("subject", ""),
            "knowledge": payload.get("knowledge", ""),
            "question": payload.get("question", ""),
            "answer": payload.get("answer", ""),
            "correct_answer": payload.get("correct_answer", ""),
            "reason": payload.get("reason", "未分类"),
            "status": "待复习",
            "created": datetime.now().isoformat(),
        })
        save_json(DATA_DIR / "mistakes.json", mistakes)
        self.send_json({"ok": True, "id": mistakes[-1]["id"]})

    def handle_get_review(self):
        """获取到期复习的知识点（SM-2 调度）"""
        cards = load_json(DATA_DIR / "cards.json", [])
        today = datetime.now().date()
        due = []
        for c in cards:
            try:
                due_date = datetime.fromisoformat(c["due"]).date()
            except (ValueError, KeyError):
                continue
            if due_date <= today:
                due.append(c)
        self.send_json({"due": due, "total_due": len(due), "total_cards": len(cards)})

    def handle_submit_review(self):
        payload = self.read_body()
        cid = payload.get("id", "")
        quality = int(payload.get("quality", 3))
        cards = load_json(DATA_DIR / "cards.json", [])
        for c in cards:
            if c["id"] == cid:
                reps, interval, ease = sm2_review(
                    c.get("repetitions", 0), c.get("interval", 0), c.get("ease", 2.5), quality
                )
                c["repetitions"] = reps
                c["interval"] = interval
                c["ease"] = round(ease, 2)
                c["due"] = (datetime.now() + timedelta(days=interval)).isoformat()
                save_json(DATA_DIR / "cards.json", cards)
                self.send_json({"ok": True, "card": c})
                return
        self.send_json({"error": "卡片不存在"}, 404)

    def handle_get_knowledge(self):
        knowledge = load_json(DATA_DIR / "knowledge.json", {})
        self.send_json({"knowledge": knowledge, "total": len(knowledge)})

    def handle_add_knowledge(self):
        payload = self.read_body()
        knowledge = load_json(DATA_DIR / "knowledge.json", {})
        subject = payload.get("subject", "")
        if subject:
            knowledge.setdefault(subject, {"prob": 0.2, "mastered": False})
            if "notes" in payload:
                knowledge[subject]["notes"] = payload["notes"]
        save_json(DATA_DIR / "knowledge.json", knowledge)
        self.send_json({"ok": True, "knowledge": knowledge})

    def handle_get_plan(self):
        plan = load_json(DATA_DIR / "plan.json", None)
        self.send_json({"plan": plan})

    def handle_generate_plan(self):
        """生成学习计划：考试日期 + 每日时间 → 基础/强化/冲刺"""
        payload = self.read_body()
        exam_date = payload.get("exam_date", "")
        daily_hours = float(payload.get("daily_hours", 2))
        subject = payload.get("subject", "综合")
        try:
            target = datetime.fromisoformat(exam_date).date()
            today = datetime.now().date()
            days_left = (target - today).days
            if days_left <= 0:
                self.send_json({"error": "考试日期已过"}, 400)
                return
            phase1_end = today + timedelta(days=max(1, days_left // 3))
            phase2_end = today + timedelta(days=max(2, days_left * 2 // 3))
            plan = {
                "subject": subject,
                "exam_date": exam_date,
                "days_left": days_left,
                "daily_hours": daily_hours,
                "phases": [
                    {"name": "基础阶段", "start": today.isoformat(), "end": phase1_end.isoformat(),
                     "focus": "打基础，学方法", "hours": round(daily_hours * days_left * 0.3)},
                    {"name": "强化阶段", "start": (phase1_end + timedelta(days=1)).isoformat(), "end": phase2_end.isoformat(),
                     "focus": "专项训练，刷题", "hours": round(daily_hours * days_left * 0.4)},
                    {"name": "冲刺阶段", "start": (phase2_end + timedelta(days=1)).isoformat(), "end": target.isoformat(),
                     "focus": "真题模拟，查漏补缺", "hours": round(daily_hours * days_left * 0.3)},
                ],
                "generated": datetime.now().isoformat(),
            }
            save_json(DATA_DIR / "plan.json", plan)
            self.send_json({"ok": True, "plan": plan})
        except ValueError:
            self.send_json({"error": "日期格式错误，应为 YYYY-MM-DD"}, 400)

    def handle_get_stats(self):
        stats = load_json(DATA_DIR / "stats.json", {"total": 0, "correct": 0})
        knowledge = load_json(DATA_DIR / "knowledge.json", {})
        mistakes = load_json(DATA_DIR / "mistakes.json", [])
        cards = load_json(DATA_DIR / "cards.json", [])
        acc = round(stats["correct"] / stats["total"] * 100, 1) if stats["total"] else 0
        # 找出最弱科目（掌握度最低）
        weakest = min(knowledge.items(), key=lambda x: x[1]["prob"]) if knowledge else None
        self.send_json({
            "total_answered": stats["total"],
            "correct": stats["correct"],
            "accuracy": acc,
            "mistakes": len(mistakes),
            "cards": len(cards),
            "weakest": {"subject": weakest[0], "prob": weakest[1]["prob"]} if weakest else None,
            "knowledge": knowledge,
        })

    def handle_reset(self):
        """重置学习数据（谨慎操作）"""
        for f in ["state.json", "mistakes.json", "knowledge.json", "stats.json", "cards.json", "plan.json"]:
            p = DATA_DIR / f
            if p.exists():
                p.unlink()
        self.send_json({"ok": True, "reset": True})

    # ---------- LLM 调用层（对接 dsh-our-free-model 免费模型） ----------
    def handle_get_llm_config(self):
        """读取 LLM 配置（不回显完整 Key，只给指纹）"""
        cfg = load_json(DATA_DIR / "llm_config.json", {})
        key = cfg.get("api_key", "")
        masked = ""
        if key:
            masked = key[:4] + "…" + key[-4:] if len(key) > 8 else "已设置"
        self.send_json({
            "base_url": cfg.get("base_url", "http://127.0.0.1:18900/v1"),
            "model": cfg.get("model", ""),
            "has_key": bool(key),
            "key_fingerprint": masked,
        })

    def handle_save_llm_config(self):
        """保存 LLM 配置（Key 只写本地 0600 文件）"""
        payload = self.read_body()
        cfg = load_json(DATA_DIR / "llm_config.json", {})
        if "base_url" in payload:
            cfg["base_url"] = payload["base_url"].rstrip("/")
        if "model" in payload:
            cfg["model"] = payload["model"]
        if "api_key" in payload and payload["api_key"]:
            cfg["api_key"] = payload["api_key"]
        save_json(DATA_DIR / "llm_config.json", cfg)
        try:
            os.chmod(DATA_DIR / "llm_config.json", 0o600)
        except OSError:
            pass
        self.send_json({"ok": True, "saved": True})

    def handle_llm_chat(self):
        """调用免费模型（OpenAI 兼容 /v1/chat/completions）"""
        payload = self.read_body()
        cfg = load_json(DATA_DIR / "llm_config.json", {})
        base_url = cfg.get("base_url", "http://127.0.0.1:18900/v1")
        model = cfg.get("model", "") or payload.get("model", "")
        api_key = cfg.get("api_key", "")
        messages = payload.get("messages", [])
        if not model:
            self.send_json({"error": "未配置模型，请在设置中选择"}, 400)
            return
        if not messages:
            self.send_json({"error": "消息为空"}, 400)
            return
        body = {
            "model": model,
            "messages": messages,
            "temperature": payload.get("temperature", 0.7),
            "stream": False,
        }
        try:
            req = urllib.request.Request(
                base_url + "/chat/completions",
                data=json.dumps(body).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + api_key if api_key else "Bearer local",
                },
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
            content = data["choices"][0]["message"]["content"]
            self.send_json({"ok": True, "content": content})
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            self.send_json({"error": f"模型服务返回 {e.code}: {detail}"}, 502)
        except Exception as e:
            self.send_json({"error": f"调用失败: {e}"}, 502)

    def handle_llm_test(self):
        """测试 LLM 连接（列出模型）"""
        cfg = load_json(DATA_DIR / "llm_config.json", {})
        base_url = cfg.get("base_url", "http://127.0.0.1:18900/v1")
        api_key = cfg.get("api_key", "")
        try:
            req = urllib.request.Request(
                base_url + "/models",
                headers={"Authorization": "Bearer " + api_key if api_key else "Bearer local"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            models = [m["id"] for m in data.get("data", [])]
            self.send_json({"ok": True, "models": models[:30], "count": len(models)})
        except Exception as e:
            self.send_json({"ok": False, "error": str(e), "hint": "请确认已启动 dsh-our-free-model 独立服务（默认端口 18900）"})

    # ---------- 资源中心（官方平台 + 培训机构信息源） ----------
    def handle_get_sources(self):
        """获取信息源：内置 + 用户自定义"""
        builtin = load_json(APP_DIR / "sources.json", [])
        custom = load_json(DATA_DIR / "sources_custom.json", [])
        self.send_json({"sources": builtin + custom, "total": len(builtin) + len(custom), "builtin": len(builtin), "custom": len(custom)})

    def handle_add_source(self):
        """添加自定义信息源"""
        payload = self.read_body()
        name = payload.get("name", "").strip()
        url = payload.get("url", "").strip()
        if not name or not url:
            self.send_json({"error": "名称和网址必填"}, 400)
            return
        if not url.startswith("http"):
            self.send_json({"error": "网址需以 http(s):// 开头"}, 400)
            return
        custom = load_json(DATA_DIR / "sources_custom.json", [])
        custom.append({
            "id": f"c_{int(time.time()*1000)}",
            "name": name,
            "category": payload.get("category", "自定义"),
            "exam": payload.get("exam", ""),
            "url": url,
            "desc": payload.get("desc", ""),
            "note": "用户自定义",
            "custom": True,
        })
        save_json(DATA_DIR / "sources_custom.json", custom)
        self.send_json({"ok": True, "id": custom[-1]["id"]})

    # ---------- 网盘搜索（聚合网盘资料检索） ----------
    def handle_get_pan_search(self):
        """获取网盘搜索服务清单 + 用户收藏"""
        services = load_json(APP_DIR / "pan_search.json", [])
        favorites = load_json(DATA_DIR / "pan_favorites.json", [])
        self.send_json({"services": services, "favorites": favorites,
                        "service_count": len(services), "total_favorites": len(favorites)})

    def handle_add_pan_favorite(self):
        """保存用户的网盘资料收藏（链接/关键词）"""
        payload = self.read_body()
        action = payload.get("action", "add")
        favorites = load_json(DATA_DIR / "pan_favorites.json", [])
        if action == "add":
            title = payload.get("title", "").strip()
            url = payload.get("url", "").strip()
            if not title or not url:
                self.send_json({"error": "标题和链接必填"}, 400)
                return
            favorites.append({
                "id": f"p_{int(time.time()*1000)}",
                "title": title,
                "url": url,
                "desc": payload.get("desc", ""),
                "created": datetime.now().isoformat(),
            })
            save_json(DATA_DIR / "pan_favorites.json", favorites)
            self.send_json({"ok": True, "id": favorites[-1]["id"]})
        elif action == "delete":
            fid = payload.get("id", "")
            favorites = [f for f in favorites if f["id"] != fid]
            save_json(DATA_DIR / "pan_favorites.json", favorites)
            self.send_json({"ok": True, "deleted": True})
        else:
            self.send_json({"error": "未知操作"}, 400)

    # ---------- 刷题工具生成器 ----------
    def handle_generate_tool(self):
        """生成离线网页刷题工具：接收题目列表 → 返回自包含 HTML"""
        payload = self.read_body()
        title = payload.get("title", "模拟试卷")
        subject = payload.get("subject", "综合")
        questions = payload.get("questions", [])
        if not questions:
            self.send_json({"error": "题目列表为空"}, 400)
            return
        # 规范化题目字段
        clean = []
        for q in questions:
            item = {
                "question": q.get("question", ""),
                "options": q.get("options", []),
                "answer": q.get("answer", ""),
                "explanation": q.get("explanation", ""),
                "knowledge": q.get("knowledge", ""),
            }
            if item["question"]:
                clean.append(item)
        if not clean:
            self.send_json({"error": "无有效题目"}, 400)
            return
        html = generate_quiz_html(title, subject, clean)
        self.send_json({"ok": True, "title": title, "subject": subject, "count": len(clean), "html": html})

    def handle_generate_from_text(self):
        """用 LLM 从资料文本生成题目"""
        payload = self.read_body()
        text = payload.get("text", "")
        count = int(payload.get("count", 10))
        subject = payload.get("subject", "综合")
        title = payload.get("title", subject + "模拟卷")
        if not text.strip():
            self.send_json({"error": "资料文本为空"}, 400)
            return
        cfg = load_json(DATA_DIR / "llm_config.json", {})
        model = cfg.get("model", "")
        base_url = cfg.get("base_url", "http://127.0.0.1:18900/v1")
        api_key = cfg.get("api_key", "")
        if not model:
            self.send_json({"error": "未配置模型，请先在设置中选择"}, 400)
            return
        prompt = (
            "你是出题老师。根据以下学习资料，生成" + str(count) + "道选择题。"
            "每道题必须包含：question(题干)、options(4个选项字符串数组)、answer(正确选项字母 A/B/C/D)、"
            "explanation(解析)、knowledge(知识点)。只输出 JSON 数组，不要其它文字。\n\n"
            "学习资料：\n" + text[:8000]
        )
        try:
            req = urllib.request.Request(
                base_url + "/chat/completions",
                data=json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}).encode(),
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + api_key if api_key else "Bearer local"},
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode())
            content = data["choices"][0]["message"]["content"]
            questions = self._parse_llm_questions(content)
            if not questions:
                self.send_json({"error": "AI 未能生成有效题目，请重试或手动导入"}, 502)
                return
            html = generate_quiz_html(title, subject, questions)
            self.send_json({"ok": True, "title": title, "subject": subject, "count": len(questions), "questions": questions, "html": html})
        except Exception as e:
            self.send_json({"error": f"生成失败: {e}"}, 502)

    @staticmethod
    def _parse_llm_questions(content):
        """解析 LLM 返回的题目 JSON（容错处理 markdown 代码块）"""
        text = content.strip()
        if "```" in text:
            import re
            blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", text)
            if blocks:
                text = blocks[0].strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            import re
            arr = re.search(r"\[([\s\S]*)\]", text)
            if not arr:
                return []
            try:
                data = json.loads(arr.group(0))
            except json.JSONDecodeError:
                return []
        if isinstance(data, dict):
            data = [data]
        clean = []
        for q in data:
            if not isinstance(q, dict):
                continue
            item = {
                "question": q.get("question", ""),
                "options": q.get("options", []),
                "answer": q.get("answer", ""),
                "explanation": q.get("explanation", ""),
                "knowledge": q.get("knowledge", ""),
            }
            if item["question"] and item["options"] and item["answer"]:
                clean.append(item)
        return clean

    # ---------- 工具 ----------
    def _parse_query(self):
        from urllib.parse import urlparse, parse_qs
        # http.server 以 latin1 解码 URL，中文参数需还原为 UTF-8 再解析
        path = self.path
        try:
            path = path.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
        parsed = urlparse(path)
        return {k: v[0] for k, v in parse_qs(parsed.query).items()}

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {fmt % args}\n")


def generate_quiz_html(title, subject, questions):
    """生成自包含的离线网页刷题工具
    - 单 HTML 文件，内嵌题目，双击即用
    - localStorage 持久化：错题、统计、进度
    - 完全离线，不依赖服务器
    """
    quiz_json = json.dumps({"title": title, "subject": subject, "questions": questions}, ensure_ascii=False).replace("</", "<\\/")
    from html import escape
    title_safe = escape(title, quote=False)
    return QUIZ_TEMPLATE.replace("__QUIZ_JSON__", quiz_json).replace("__TITLE__", title_safe)


QUIZ_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<style>
:root{--p:#4f46e5;--pl:#7c73ff;--bg:#f8fafc;--card:#fff;--bd:#e2e8f0;--tx:#1e293b;--mu:#64748b;--ok:#10b981;--err:#ef4444}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--tx)}
.hd{background:linear-gradient(135deg,var(--p),var(--pl));color:#fff;padding:14px 20px}
.hd h1{font-size:18px;font-weight:700}
.hd .sub{font-size:12px;opacity:.9}
.bar{display:flex;background:var(--card);border-bottom:1px solid var(--bd);overflow-x:auto}
.bar button{flex:1;min-width:64px;padding:11px 8px;border:none;background:none;font-size:13px;color:var(--mu);cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap}
.bar button.on{color:var(--p);border-color:var(--p);font-weight:600}
.wrap{max-width:720px;margin:0 auto;padding:16px}
.pg{display:none}.pg.on{display:block}
.card{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:16px;margin-bottom:12px}
.card h3{font-size:14px;margin-bottom:8px}
.card p{font-size:14px;line-height:1.7}
.opts{margin-top:12px}
.opt{display:block;width:100%;text-align:left;background:var(--card);border:1px solid var(--bd);border-radius:8px;padding:12px;font-size:14px;margin-bottom:8px;cursor:pointer}
.opt:hover{border-color:var(--p)}
.opt.ok{border-color:var(--ok);background:#ecfdf5}
.opt.bad{border-color:var(--err);background:#fef2f2}
.expl{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:12px;font-size:13px;line-height:1.6;margin-top:10px}
.expl.err{background:#fef2f2;border-color:#fecaca}
.btn{display:inline-block;background:var(--p);color:#fff;border:none;border-radius:8px;padding:10px 18px;font-size:14px;cursor:pointer}
.btn.sec{background:var(--card);color:var(--p);border:1px solid var(--p)}
.btn.sm{padding:6px 12px;font-size:12px}
.stat{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-bottom:12px}
.st{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:14px;text-align:center}
.st .n{font-size:20px;font-weight:700;color:var(--p)}
.st .l{font-size:12px;color:var(--mu);margin-top:4px}
.prog{height:6px;background:var(--bd);border-radius:999px;margin-bottom:12px;overflow:hidden}
.prog i{display:block;height:100%;background:var(--p);transition:width .3s}
.mk{border:1px solid var(--bd);border-radius:10px;padding:12px;margin-bottom:10px;background:var(--card)}
.mk .q{font-size:13px;line-height:1.6}
.mk .meta{font-size:11px;color:var(--mu);margin-top:6px}
.empty{text-align:center;color:var(--mu);font-size:13px;padding:24px}
.foot{text-align:center;padding:16px;color:var(--mu);font-size:11px}
@media(max-width:600px){.hd{padding:12px 14px}.wrap{padding:12px}.hd h1{font-size:16px}}
</style>
</head>
<body>
<div class="hd"><h1 id="t">__TITLE__</h1><div class="sub" id="sub"></div></div>
<div class="bar">
  <button data-pg="do" class="on">刷题</button>
  <button data-pg="mk">错题</button>
  <button data-pg="st">统计</button>
</div>
<div class="wrap">
  <div class="pg on" id="pg-do">
    <div class="prog"><i id="prog" style="width:0%"></i></div>
    <div class="card">
      <h3 id="qmeta"></h3>
      <p id="qtext"></p>
      <div class="opts" id="qopts"></div>
      <div id="qexpl" style="display:none"></div>
      <div style="margin-top:12px;display:flex;gap:8px;justify-content:space-between">
        <button class="btn sec sm" id="prev">上一题</button>
        <button class="btn sm" id="next">下一题</button>
      </div>
    </div>
  </div>
  <div class="pg" id="pg-mk">
    <div class="card"><h3>错题本</h3><div id="mklist"><div class="empty">暂无错题</div></div></div>
  </div>
  <div class="pg" id="pg-st">
    <div class="stat">
      <div class="st"><div class="n" id="s-done">0</div><div class="l">已做</div></div>
      <div class="st"><div class="n" id="s-ok">0</div><div class="l">答对</div></div>
      <div class="st"><div class="n" id="s-acc">0%</div><div class="l">正确率</div></div>
      <div class="st"><div class="n" id="s-mk">0</div><div class="l">错题</div></div>
    </div>
    <div class="card"><h3>答题记录（本地保存）</h3><div id="slist"><div class="empty">暂无记录</div></div></div>
  </div>
</div>
<div class="foot">ExamBoost 离线刷题工具 · 数据保存在本机浏览器（localStorage）</div>
<script>
window.QUIZ=__QUIZ_JSON__;
const D=JSON.parse(localStorage.getItem("ebq_"+QUIZ.title)||"null")||{answers:{},wrong:{}};
let cur=0,answered=0;
const $=id=>document.getElementById(id);
function save(){localStorage.setItem("ebq_"+QUIZ.title,JSON.stringify(D));}
function norm(a){return String(a).trim().toUpperCase();}
function render(){
  const q=QUIZ.questions[cur];
  $("qmeta").textContent="第"+(cur+1)+"题/共"+QUIZ.questions.length+"题 · "+q.knowledge;
  $("qtext").textContent=q.question;
  const o=$("qopts");o.innerHTML="";
  (q.options||[]).forEach(op=>{
    const b=document.createElement("button");b.className="opt";b.textContent=op;
    const L=op.split(".")[0].trim();
    const prev=D.answers[cur];
    if(prev){b.disabled=true;if(norm(L)===norm(q.answer))b.classList.add("ok");if(norm(L)===prev&&norm(prev)!==norm(q.answer))b.classList.add("bad");}
    b.onclick=()=>choose(cur,L,op);o.appendChild(b);
  });
  const ex=$("qexpl");
  if(D.answers[cur]){const ok=norm(D.answers[cur])===norm(q.answer);ex.style.display="block";ex.innerHTML="<div class=\"expl "+(ok?"":"err")+"\">"+(ok?"✅ 回答正确":"❌ 回答错误，正确答案："+q.answer)+"<br>💡 "+(q.explanation||"")+"</div>";}
  else ex.style.display="none";
  $("prog").style.width=((cur+1)/QUIZ.questions.length*100)+"%";
  $("prev").disabled=cur===0; $("next").disabled=cur===QUIZ.questions.length-1;
  $("t").textContent=QUIZ.title; $("sub").textContent=QUIZ.subject+" · 第"+(cur+1)+"/"+QUIZ.questions.length+"题";
}
function choose(i,L,op){
  const q=QUIZ.questions[i];
  D.answers[i]=L;answered++;
  if(norm(L)!==norm(q.answer)){D.wrong[i]={q:q.question,a:q.answer,e:q.explanation,k:q.knowledge};}
  else delete D.wrong[i];
  save();render();
}
function go(i){cur=Math.max(0,Math.min(QUIZ.questions.length-1,i));render();}
$("prev").onclick=()=>go(cur-1); $("next").onclick=()=>go(cur+1);
document.querySelectorAll(".bar button").forEach(b=>{b.onclick=()=>{document.querySelectorAll(".bar button").forEach(x=>x.classList.remove("on"));document.querySelectorAll(".pg").forEach(x=>x.classList.remove("on"));b.classList.add("on");$("pg-"+b.dataset.pg).classList.add("on");if(b.dataset.pg==="mk")renderMk();if(b.dataset.pg==="st")renderSt();};});
function renderMk(){
  const w=Object.values(D.wrong);
  $("mklist").innerHTML=w.length?w.map(m=>"<div class=\"mk\"><div class=\"q\">"+m.q+"</div><div class=\"meta\">知识点:"+m.k+" · 答案:"+m.a+"</div></div>").join(""):"<div class=\"empty\">暂无错题，继续努力！</div>";
}
function renderSt(){
  const total=Object.keys(D.answers).length;
  const okc=Object.keys(D.answers).filter(i=>norm(D.answers[i])===norm(QUIZ.questions[i].answer)).length;
  const mk=Object.keys(D.wrong).length;
  $("s-done").textContent=total;$("s-ok").textContent=okc;$("s-acc").textContent=(total?Math.round(okc/total*100):0)+"%";$("s-mk").textContent=mk;
  $("slist").innerHTML=total?QUIZ.questions.map((q,i)=>{const a=D.answers[i];return "<div class=\"mk\"><div class=\"q\">"+(i+1)+". "+q.question.slice(0,50)+"</div><div class=\"meta\">"+(a?"你的答案:"+a+(norm(a)===norm(q.answer)?" ✅":" ❌"):"未作答")+"</div></div>";}).join(""):"<div class=\"empty\">暂无记录</div>";
}
render();
</script>
</body>
</html>'''


def main():
    global PORT
    parser = argparse.ArgumentParser(description="ExamBoost AI Server")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--host", type=str, default="0.0.0.0",
                        help="绑定地址，0.0.0.0 允许局域网访问，127.0.0.1 仅本机")
    args = parser.parse_args()
    PORT = args.port
    DATA_DIR.mkdir(exist_ok=True)
    server = HTTPServer((args.host, PORT), ExamBoostHandler)
    lan_ip = get_lan_ip()
    print(f"ExamBoost AI 运行中 (v0.2.1)")
    print(f"  本机访问: http://localhost:{PORT}")
    if args.host == "0.0.0.0":
        print(f"  手机/平板访问 (同一WiFi): http://{lan_ip}:{PORT}")
    print(f"  数据目录: {DATA_DIR}")
    print("按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
