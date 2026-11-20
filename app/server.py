#!/usr/bin/env python3
"""ExamBoost AI — 综合备考学习引擎（本地服务）

启动后提供 Web 界面与 REST API，浏览器/手机直接访问。
学习数据全部写在本地 data/ 目录，不上传任何内容。

设计要点：
- 纯 Python 标准库，零第三方依赖，装了 Python 就能跑
- ThreadingHTTPServer，多人/多标签并发不阻塞
- AI 能力零配置：自动探测本机免费模型 → 匿名免费池，开箱即用
"""
import argparse
import json
import os
import random
import re
import socket
import sys
import threading
import urllib.parse
from datetime import datetime, timedelta
from html import escape
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import edata
import ellm
import eqbank
import eqiz
import core
import fsrs

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
VERSION = "2.0.0"
DEFAULT_PORT = 3000

STORE = edata.Store(DATA_DIR)
BANK = eqbank.QuestionBank(APP_DIR, STORE)

REASONS = ["概念不清", "公式记错", "审题失误", "计算粗心", "方法选错", "时间不够", "蒙错", "未分类"]

# 抽题防重复：记住近期出过的题
_asked = {"ids": [], "lock": threading.Lock()}


# ------------------------------------------------------------------
#  LLM 配置与调用
# ------------------------------------------------------------------
def llm_config():
    return STORE.load(edata.F_LLM, {})


def provider_chain():
    """按优先级给出可用模型链（含缓存，避免每次请求都探测）。"""
    global _prov_cache
    with _prov_lock:
        now = datetime.now().timestamp()
        if _prov_cache and now - _prov_cache["at"] < 60:
            return _prov_cache["providers"]
        cfg = llm_config()
        custom = None
        if cfg.get("base_url"):
            custom = {"base_url": cfg["base_url"], "api_key": cfg.get("api_key", ""),
                      "model": cfg.get("model", ""),
                      "ofm_standalone_key": cfg.get("ofm_standalone_key", "")}
        providers = ellm.discover(custom)
        chosen = cfg.get("preferred")
        if chosen:
            providers.sort(key=lambda p: 0 if p["id"] == chosen else 1)
        _prov_cache = {"at": now, "providers": providers}
        return providers


_prov_cache = None
_prov_lock = threading.RLock()


def invalidate_provider_cache():
    global _prov_cache
    with _prov_lock:
        _prov_cache = None


def active_provider():
    """当前实际会用的那一个。"""
    chain = provider_chain()
    pref = llm_config().get("preferred")
    if pref:
        for p in chain:
            if p["id"] == pref:
                return p
    return ellm.pick_default(chain)


# ------------------------------------------------------------------
#  业务逻辑
# ------------------------------------------------------------------
def build_stats():
    stats = STORE.load(edata.F_STATS)
    knowledge = STORE.load(edata.F_KNOWLEDGE)
    mistakes = STORE.load(edata.F_MISTAKES)
    cards = STORE.load(edata.F_CARDS)
    total = stats.get("total", 0)
    correct = stats.get("correct", 0)
    acc = round(correct / total * 100, 1) if total else 0.0
    pending = [m for m in mistakes if m.get("status") != "已消灭"]
    today = edata.today()
    due = [c for c in cards if c.get("due", today) <= today]
    weakest = None
    if knowledge:
        items = [(k, v) for k, v in knowledge.items() if isinstance(v, dict) and "prob" in v]
        if items:
            k, v = min(items, key=lambda x: x[1]["prob"])
            weakest = {"subject": k, "prob": v["prob"]}
    return {
        "total_answered": total,
        "correct": correct,
        "accuracy": acc,
        "mistakes": len(mistakes),
        "mistakes_pending": len(pending),
        "cards": len(cards),
        "due_today": len(due),
        "weakest": weakest,
        "knowledge": knowledge,
        "by_subject": stats.get("by_subject", {}),
        "by_day": stats.get("by_day", {}),
        "streak": calc_streak(),
    }


def calc_streak():
    """连续打卡天数（今天或昨天有答题即算连续）。"""
    stats = STORE.load(edata.F_STATS)
    days = sorted((stats.get("by_day") or {}).keys(), reverse=True)
    if not days:
        return 0
    today = datetime.strptime(edata.today(), "%Y-%m-%d")
    streak = 0
    cursor = today
    last = datetime.strptime(days[0], "%Y-%m-%d")
    if (cursor - last).days > 1:
        return 0
    for d in days:
        dd = datetime.strptime(d, "%Y-%m-%d")
        if (cursor - dd).days == 0:
            streak += 1
            cursor = cursor - timedelta(days=1)
        elif (cursor - dd).days == 1:
            streak += 1
            cursor = dd
        else:
            break
    return streak


def record_answer(subject, knowledge, is_correct, stage=""):
    def mutate(stats):
        stats["total"] = stats.get("total", 0) + 1
        if is_correct:
            stats["correct"] = stats.get("correct", 0) + 1
        key = subject or "未分类"
        bs = stats.setdefault("by_subject", {})
        rec = bs.setdefault(key, {"total": 0, "correct": 0, "stage": stage})
        rec["total"] += 1
        if is_correct:
            rec["correct"] += 1
        day = edata.today()
        bd = stats.setdefault("by_day", {})
        drec = bd.setdefault(day, {"total": 0, "correct": 0})
        drec["total"] += 1
        if is_correct:
            drec["correct"] += 1
        return stats
    STORE.mutate(edata.F_STATS, mutate)

    if subject:
        def mut_k(knowledge_map):
            entry = knowledge_map.setdefault(subject, {"prob": 0.2, "mastered": False})
            entry["prob"] = edata.bkt_update(entry.get("prob", 0.2), is_correct)
            entry["mastered"] = entry["prob"] >= 0.8
            entry["last"] = edata.now_iso()
            return knowledge_map
        STORE.mutate(edata.F_KNOWLEDGE, mut_k)


def record_mistake(q, chosen, reason):
    def mutate(items):
        qid = q.get("id")
        for m in items:
            if m.get("qid") == qid and m.get("status") != "已消灭":
                m["count"] = m.get("count", 1) + 1
                m["last_wrong"] = edata.now_iso()
                m["reason"] = reason or m.get("reason", "未分类")
                m["answer"] = chosen
                return items
        items.append({
            "id": edata.uid("m"),
            "qid": qid,
            "stage": q.get("stage", ""),
            "subject": q.get("subject", ""),
            "knowledge": q.get("knowledge", ""),
            "question": q.get("question", ""),
            "options": q.get("options", []),
            "answer": chosen,
            "correct_answer": q.get("answer", ""),
            "explanation": q.get("explanation", ""),
            "reason": reason or "未分类",
            "status": "待复习",
            "count": 1,
            "created": edata.now_iso(),
            "last_wrong": edata.now_iso(),
        })
        return items
    STORE.mutate(edata.F_MISTAKES, mutate)


def enqueue_card(q):
    """答错 → 进入 FSRS 复习队列（新卡首评时初始化 stability/difficulty）。"""
    if not q.get("id"):
        return
    def mutate(cards):
        for c in cards:
            if c.get("qid") == q["id"]:
                c["due"] = edata.today()
                c["reps"] = 0
                return cards
        cards.append({
            "id": edata.uid("c"),
            "qid": q["id"],
            "subject": q.get("subject", ""),
            "knowledge": q.get("knowledge", ""),
            "question": q.get("question", ""),
            "answer": q.get("answer", ""),
            "explanation": q.get("explanation", ""),
            "provenance": q.get("provenance", ""),
            "source_material": q.get("source_material", ""),
            "reps": 0,
            "lapses": 0,
            "due": edata.today(),
            "created": edata.now_iso(),
        })
        return cards
    STORE.mutate(edata.F_CARDS, mutate)


def due_cards():
    today = edata.today()
    cards = STORE.load(edata.F_CARDS, [])
    return [c for c in cards if c.get("due", today) <= today]


def generate_plan(payload):
    exam_date = str(payload.get("exam_date") or "").strip()
    try:
        daily = float(payload.get("daily_hours") or 2)
    except (TypeError, ValueError):
        daily = 2.0
    daily = max(0.25, min(16.0, daily))
    subject = str(payload.get("subject") or "综合").strip()
    focus = str(payload.get("focus") or "").strip()
    try:
        target = datetime.strptime(exam_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None, "考试日期格式应为 YYYY-MM-DD"
    today = datetime.now().date()
    days_left = (target - today).days
    if days_left <= 0:
        return None, "考试日期已过，请把日期改成未来某天"
    if days_left > 1500:
        return None, "距考试超过 4 年，计划价值不大，建议填更近的目标日期"

    n1 = max(1, days_left // 3)
    n2 = max(1, days_left * 2 // 3 - n1)
    n3 = max(1, days_left - n1 - n2)
    s1 = today
    s2 = today + timedelta(days=n1)
    s3 = today + timedelta(days=n1 + n2)
    phases = [
        {"name": "基础阶段", "start": s1.isoformat(), "end": (s2 - timedelta(days=1)).isoformat(),
         "days": n1, "hours": round(daily * n1),
         "focus": "过一遍考纲与教材，建立知识框架，配套基础题",
         "tasks": ["梳理考纲章节，列出知识点清单", "每个知识点做 5-10 道基础题",
                   "错题当天录入错题本并写错因", "每周日做一次本周复盘"]},
        {"name": "强化阶段", "start": s2.isoformat(), "end": (s3 - timedelta(days=1)).isoformat(),
         "days": n2, "hours": round(daily * n2),
         "focus": "专项突破薄弱模块，刷题提速，错题二刷",
         "tasks": ["按薄弱点排专项训练（优先掌握度 < 60% 的科目）", "限时刷题，训练答题节奏",
                   "错题二刷，三次答错的题重点标记", "整理高频考点速记卡"]},
        {"name": "冲刺阶段", "start": s3.isoformat(), "end": target.isoformat(),
         "days": n3, "hours": round(daily * n3),
         "focus": "整卷模拟，查漏补缺，调整状态",
         "tasks": ["按真实考试时间做整卷模拟", "只复习错题本与标记题，不刷新题",
                   "考前 3 天回归基础与考纲，停止熬夜", "准备好证件、文具与考试路线"]},
    ]
    plan = {
        "subject": subject,
        "exam_date": exam_date,
        "days_left": days_left,
        "daily_hours": daily,
        "total_hours": round(daily * days_left),
        "focus": focus,
        "phases": phases,
        "weekly": build_weekly(s1, days_left, daily, subject),
        "generated": edata.now_iso(),
    }
    STORE.save(edata.F_PLAN, plan)
    return plan, ""


def build_weekly(start, days_left, daily, subject):
    """按周切分，给出每周里程碑。"""
    weeks = []
    i = 0
    week_no = 1
    while i < days_left and week_no <= 24:
        seg = min(7, days_left - i)
        ws = start + timedelta(days=i)
        we = ws + timedelta(days=seg - 1)
        phase = "基础" if i < days_left // 3 else ("强化" if i < days_left * 2 // 3 else "冲刺")
        weeks.append({
            "week": week_no,
            "start": ws.isoformat(),
            "end": we.isoformat(),
            "phase": phase,
            "hours": round(daily * seg),
            "goal": f"{phase}阶段第 {week_no} 周：{subject} 按计划推进，错题当天清零",
        })
        i += seg
        week_no += 1
    return weeks


# ------------------------------------------------------------------
#  HTTP Handler
# ------------------------------------------------------------------
class Handler(SimpleHTTPRequestHandler):
    server_version = f"ExamBoost/{VERSION}"
    protocol_version = "HTTP/1.1"

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(APP_DIR), **kw)

    # ---------- 基础 ----------
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_html(self, html, filename=None, status=200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if filename:
            self.send_header("Content-Disposition",
                             f'attachment; filename="{urllib.parse.quote(filename)}"')
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def read_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        if length > 4_000_000:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def query(self):
        try:
            path = self.path.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            path = self.path
        parsed = urllib.parse.urlparse(path)
        return {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}

    def route_path(self):
        p = self.path.split("?", 1)[0]
        try:
            p = urllib.parse.unquote(p)
        except Exception:
            pass
        return p

    # ---------- 静态文件（保护 data/） ----------
    def do_GET(self):
        p = self.route_path()
        if p.startswith("/data/") or p.startswith("/data%2F"):
            self.send_json({"error": "学习数据不允许通过网页直接访问"}, 403)
            return
        if p.startswith("/api/"):
            self.handle_api_get(p)
            return
        # 导航请求走网络，禁用缓存，改了立刻生效
        if p in ("/", "/index.html") or not Path(p).suffix or Path(p).suffix in (".html", ".htm"):
            file_path = APP_DIR / (p.lstrip("/") or "index.html")
            if file_path.is_file():
                self.serve_file(file_path, no_cache=True)
                return
        super().do_GET()

    def serve_file(self, file_path: Path, no_cache=False):
        try:
            data = file_path.read_bytes()
        except OSError:
            self.send_error(404)
            return
        ext = file_path.suffix.lower()
        ctype = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                 ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
                 ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon",
                 ".webmanifest": "application/manifest+json"}.get(ext, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store" if no_cache or ext == ".html" else "no-cache")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        p = self.route_path()
        if not p.startswith("/api/"):
            self.send_json({"error": "not found"}, 404)
            return
        self.handle_api_post(p)

    def do_DELETE(self):
        p = self.route_path()
        if p.startswith("/api/"):
            self.handle_api_delete(p)
        else:
            self.send_json({"error": "not found"}, 404)

    # ---------- GET 路由 ----------
    def handle_api_get(self, p):
        q = self.query()
        try:
            if p == "/api/health":
                self.send_json({"ok": True, "app": "ExamBoost", "version": VERSION,
                                "time": edata.now_iso()})
            elif p == "/api/status":
                self.handle_status()
            elif p == "/api/facets":
                self.send_json(BANK.facets())
            elif p == "/api/questions":
                self.handle_questions(q)
            elif p == "/api/question":
                self.send_json({"error": "请用 /api/question/<题目id>"}, 400)
            elif p.startswith("/api/question/"):
                qid = p.rsplit("/", 1)[-1]
                item = BANK.get(qid)
                self.send_json(item or {"error": "题目不存在"}, 200 if item else 404)
            elif p == "/api/mistakes":
                items = STORE.load(edata.F_MISTAKES, [])
                status = q.get("status", "")
                if status:
                    items = [m for m in items if m.get("status") == status]
                self.send_json({"mistakes": items, "total": len(items)})
            elif p == "/api/review":
                due = due_cards()
                self.send_json({"due": due, "total_due": len(due),
                                "total_cards": len(STORE.load(edata.F_CARDS, []))})
            elif p == "/api/knowledge":
                k = STORE.load(edata.F_KNOWLEDGE, {})
                self.send_json({"knowledge": k, "total": len(k)})
            elif p == "/api/plan":
                self.send_json({"plan": STORE.load(edata.F_PLAN, None)})
            elif p == "/api/stats":
                self.send_json(build_stats())
            elif p == "/api/checkin":
                self.send_json({"days": STORE.load(edata.F_CHECKIN, []),
                                "streak": calc_streak()})
            elif p == "/api/notes":
                self.send_json({"notes": STORE.load(edata.F_NOTES, [])})
            elif p == "/api/ai/providers":
                self.handle_providers()
            elif p == "/api/ai/config":
                cfg = llm_config()
                key = cfg.get("api_key", "")
                masked = (key[:4] + "…" + key[-4:]) if len(key) > 8 else ("已设置" if key else "")
                active = active_provider()
                self.send_json({
                    "base_url": cfg.get("base_url", ""),
                    "model": cfg.get("model", ""),
                    "has_key": bool(key),
                    "key_fingerprint": masked,
                    "preferred": cfg.get("preferred", ""),
                    "auto": bool(cfg.get("auto", True)),
                    "active": {"id": active["id"], "label": active["label"],
                               "model": active.get("model", ""), "anon": active.get("anon", False)}
                    if active else None,
                })
            elif p == "/api/ai/test":
                self.handle_ai_test(q)
            elif p == "/api/sources":
                builtin = _read_json(APP_DIR / "sources.json", [])
                custom = STORE.load(edata.F_SOURCES, [])
                self.send_json({"sources": builtin + custom, "total": len(builtin) + len(custom),
                                "builtin": len(builtin), "custom": len(custom)})
            elif p == "/api/pan-search":
                services = _read_json(APP_DIR / "pan_search.json", [])
                favs = STORE.load(edata.F_PAN_FAV, [])
                self.send_json({"services": services, "favorites": favs,
                                "service_count": len(services), "total_favorites": len(favs)})
            elif p == "/api/export":
                self.handle_export()
            elif p == "/api/bank/stats":
                self.send_json({"builtin": BANK.builtin_count(),
                                "user": len(BANK.user_questions()),
                                "total": len(BANK.all_questions())})
            elif p == "/api/profile":
                prof = STORE.load(edata.F_PROFILE, {})
                self.send_json({"profile": prof, "stages": core.STAGES,
                                "goals": core.EXAM_GOALS,
                                "greeting": core.profile_greeting(prof)})
            elif p == "/api/materials":
                mats = STORE.load(edata.F_MATERIALS, [])
                # 列表不返回全文，只返回摘要
                brief = [{k: m[k] for k in ("id", "name", "exam", "source_url",
                                            "char_count", "created") if k in m}
                         for m in mats]
                self.send_json({"materials": brief, "total": len(brief)})
            elif p.startswith("/api/material/"):
                mid = p.rsplit("/", 1)[-1]
                mats = STORE.load(edata.F_MATERIALS, [])
                m = next((x for x in mats if x.get("id") == mid), None)
                self.send_json(m or {"error": "资料不存在"}, 200 if m else 404)
            elif p == "/api/sources/hub":
                prof = STORE.load(edata.F_PROFILE, {})
                self.send_json({"official": core.OFFICIAL_SOURCES,
                                "search": core.RESOURCE_SEARCH,
                                "recommended": core.profile_recommend_sources(prof),
                                "provenance": core.PROVENANCE})
            elif p == "/api/fsrs/status":
                cards = STORE.load(edata.F_CARDS, [])
                self.send_json({"total": len(cards), "due": fsrs.due_count(cards),
                                "algorithm": "FSRS-5 (py-fsrs 官方公式)"})
            else:
                self.send_json({"error": "未知接口", "path": p}, 404)
        except Exception as e:
            self.send_json({"error": f"服务端异常：{type(e).__name__}: {e}"}, 500)

    # ---------- POST 路由 ----------
    def handle_api_post(self, p):
        body = self.read_body()
        try:
            if p == "/api/answer":
                self.handle_answer(body)
            elif p == "/api/answer-batch":
                self.handle_answer_batch(body)
            elif p == "/api/mistakes":
                self.handle_add_mistake(body)
            elif p == "/api/mistakes/clear":
                self.handle_clear_mistake(body)
            elif p == "/api/mistakes/delete":
                mid = body.get("id", "")
                items = [m for m in STORE.load(edata.F_MISTAKES, []) if m.get("id") != mid]
                STORE.save(edata.F_MISTAKES, items)
                self.send_json({"ok": True})
            elif p == "/api/review/submit":
                self.handle_submit_review(body)
            elif p == "/api/knowledge":
                self.handle_add_knowledge(body)
            elif p == "/api/plan":
                self.handle_generate_plan(body)
            elif p == "/api/checkin":
                self.handle_checkin(body)
            elif p == "/api/notes":
                self.handle_add_note(body)
            elif p == "/api/notes/delete":
                nid = body.get("id", "")
                notes = [n for n in STORE.load(edata.F_NOTES, []) if n.get("id") != nid]
                STORE.save(edata.F_NOTES, notes)
                self.send_json({"ok": True})
            elif p == "/api/ai/chat":
                self.handle_ai_chat(body)
            elif p == "/api/ai/config":
                self.handle_save_llm_config(body)
            elif p == "/api/ai/generate":
                self.handle_generate_from_text(body)
            elif p == "/api/ai/explain":
                self.handle_ai_explain(body)
            elif p == "/api/ai/analyze-material":
                self.handle_analyze_material(body)
            elif p == "/api/sources":
                self.handle_add_source(body)
            elif p == "/api/sources/delete":
                sid = body.get("id", "")
                items = [s for s in STORE.load(edata.F_SOURCES, []) if s.get("id") != sid]
                STORE.save(edata.F_SOURCES, items)
                self.send_json({"ok": True})
            elif p == "/api/pan-search":
                self.handle_pan_favorite(body)
            elif p == "/api/generate-tool":
                self.handle_generate_tool(body)
            elif p == "/api/questions/import":
                self.handle_import_questions(body)
            elif p == "/api/profile":
                self.handle_save_profile(body)
            elif p == "/api/analyze-file":
                # 前端已提取好文本，这里做分段预览与字数统计（不落库，供校对页显示）
                text = str(body.get("text") or "").strip()
                mat = core.make_material(str(body.get("filename") or "文件"), text)
                self.send_json({"ok": True, "char_count": mat["char_count"],
                                "passages": len(mat["passages"]),
                                "preview": [p["text"][:60] for p in mat["passages"][:5]]})
            elif p == "/api/materials":
                self.handle_add_material(body)
            elif p.endswith("/generate") and p.startswith("/api/material/"):
                mid = p[len("/api/material/"):-len("/generate")]
                self.handle_material_generate(mid, body)
            elif p == "/api/reset":
                self.handle_reset(body)
            else:
                self.send_json({"error": "未知接口", "path": p}, 404)
        except Exception as e:
            self.send_json({"error": f"服务端异常：{type(e).__name__}: {e}"}, 500)

    def handle_api_delete(self, p):
        try:
            if p.startswith("/api/question/"):
                qid = p.rsplit("/", 1)[-1]
                n = BANK.delete_user_question(qid)
                self.send_json({"ok": True, "deleted": n}, 200 if n else 404)
            elif p.startswith("/api/notes/"):
                nid = p.rsplit("/", 1)[-1]
                notes = [n for n in STORE.load(edata.F_NOTES, []) if n.get("id") != nid]
                STORE.save(edata.F_NOTES, notes)
                self.send_json({"ok": True})
            elif p.startswith("/api/material/"):
                mid = p.rsplit("/", 1)[-1]
                mats = STORE.load(edata.F_MATERIALS, [])
                left = [m for m in mats if m.get("id") != mid]
                STORE.save(edata.F_MATERIALS, left)
                self.send_json({"ok": True, "deleted": len(mats) - len(left)})
            else:
                self.send_json({"error": "未知接口"}, 404)
        except Exception as e:
            self.send_json({"error": f"服务端异常：{e}"}, 500)

    # ---------- 各接口实现 ----------
    def handle_status(self):
        self.send_json({
            "initialized": True,
            "version": VERSION,
            "total_questions": len(BANK.all_questions()),
            "builtin_questions": BANK.builtin_count(),
            "user_questions": len(BANK.user_questions()),
            "total_mistakes": len(STORE.load(edata.F_MISTAKES, [])),
            "total_knowledge": len(STORE.load(edata.F_KNOWLEDGE, {})),
            "due_today": len(due_cards()),
            "stats": STORE.load(edata.F_STATS),
            "ai_ready": active_provider() is not None,
        })

    def handle_questions(self, q):
        count = _int(q.get("count"), 1, 1, 200)
        filters = {
            "stage": q.get("stage", ""),
            "subject": q.get("subject", ""),
            "qtype": q.get("type", ""),
            "knowledge": q.get("knowledge", ""),
            "difficulty": _int(q.get("difficulty"), 0, 0, 3),
            "keyword": q.get("keyword", ""),
            "source_filter": q.get("source", ""),
        }
        mode = q.get("mode", "random")
        if mode == "mistakes":
            items = [m for m in STORE.load(edata.F_MISTAKES, []) if m.get("status") != "已消灭"]
            out = []
            for m in items:
                full = BANK.get(m.get("qid", ""))
                if full:
                    out.append(full)
                else:
                    out.append(eqbank.normalize(m, "mistake"))
            out = [o for o in out if o]
            self.send_json({"questions": out[:count], "total": len(out), "mode": "mistakes"})
            return
        if mode == "weak":
            k = STORE.load(edata.F_KNOWLEDGE, {})
            weak = [s for s, v in k.items() if isinstance(v, dict) and v.get("prob", 0) < 0.6]
            pool = []
            for s in weak:
                pool.extend(BANK.query(subject=s, **{k2: v2 for k2, v2 in filters.items()
                                                     if k2 not in ("subject",) and v2}))
            if not pool:
                pool = BANK.query(**filters)
            random.shuffle(pool)
            self.send_json({"questions": pool[:count], "total": len(pool), "mode": "weak",
                            "weak_subjects": weak})
            return

        pool = BANK.query(**filters)
        if not pool:
            self.send_json({"questions": [], "total": 0, "matched": 0,
                             "hint": "没有符合条件的题目，试试放宽筛选或导入自己的题目"})
            return
        picked = _pick_without_repeat(pool, count)
        self.send_json({"questions": picked, "total": len(picked), "matched": len(pool)})

    def handle_answer(self, body):
        qid = str(body.get("id") or body.get("qid") or "").strip()
        q = BANK.get(qid) if qid else None
        if q is None:
            # 允许前端直接带完整题目（例如 AI 生成的临时题）
            q = eqbank.normalize({
                "id": qid or edata.uid("tmp"),
                "question": body.get("question", ""),
                "options": body.get("options", []),
                "answer": body.get("correct_answer", ""),
                "explanation": body.get("explanation", ""),
                "subject": body.get("subject", ""),
                "knowledge": body.get("knowledge", ""),
                "stage": body.get("stage", ""),
            }, "tmp")
        if not q or not q.get("question"):
            self.send_json({"error": "题目不存在或已删除"}, 404)
            return
        chosen = str(body.get("answer") or "").strip().upper()[:1]
        correct_answer = str(q.get("answer") or "").strip().upper()
        if not correct_answer:
            self.send_json({"error": "本题未设置标准答案，请自评后手动记入错题本",
                            "self_grade": True}, 200)
            return
        is_correct = chosen == correct_answer
        reason = str(body.get("reason") or "").strip()
        record_answer(q.get("subject", ""), q.get("knowledge", ""), is_correct, q.get("stage", ""))
        if not is_correct:
            record_mistake(q, chosen, reason)
            enqueue_card(q)
        stats = build_stats()
        self.send_json({"ok": True, "correct": is_correct, "answer": correct_answer,
                        "explanation": q.get("explanation", ""),
                        "knowledge": q.get("knowledge", ""), "stats": stats})

    def handle_answer_batch(self, body):
        """离线刷题工具回传整卷成绩。"""
        items = body.get("answers") or []
        if not isinstance(items, list) or not items:
            self.send_json({"error": "answers 为空"}, 400)
            return
        right = 0
        for it in items:
            if not isinstance(it, dict):
                continue
            qid = str(it.get("id") or "").strip()
            q = BANK.get(qid)
            if not q:
                continue
            chosen = str(it.get("answer") or "").strip().upper()[:1]
            ok = bool(chosen) and chosen == str(q.get("answer", "")).upper()
            if ok:
                right += 1
            else:
                record_mistake(q, chosen, str(it.get("reason") or "未分类"))
                enqueue_card(q)
            record_answer(q.get("subject", ""), q.get("knowledge", ""), ok, q.get("stage", ""))
        self.send_json({"ok": True, "recorded": len(items), "correct": right,
                        "stats": build_stats()})

    def handle_add_mistake(self, body):
        item = {
            "id": edata.uid("m"),
            "qid": body.get("id", ""),
            "stage": body.get("stage", ""),
            "subject": body.get("subject", ""),
            "knowledge": body.get("knowledge", ""),
            "question": body.get("question", ""),
            "options": body.get("options", []),
            "answer": body.get("answer", ""),
            "correct_answer": body.get("correct_answer", ""),
            "explanation": body.get("explanation", ""),
            "reason": body.get("reason", "未分类"),
            "status": "待复习",
            "count": 1,
            "created": edata.now_iso(),
        }
        if not item["question"]:
            self.send_json({"error": "question 必填"}, 400)
            return
        items = STORE.load(edata.F_MISTAKES, [])
        items.append(item)
        STORE.save(edata.F_MISTAKES, items)
        self.send_json({"ok": True, "id": item["id"]})

    def handle_clear_mistake(self, body):
        mid = body.get("id", "")
        qid = body.get("qid", "")
        def mutate(items):
            for m in items:
                if (mid and m.get("id") == mid) or (qid and m.get("qid") == qid):
                    m["status"] = "已消灭"
                    m["cleared_at"] = edata.now_iso()
            return items
        STORE.mutate(edata.F_MISTAKES, mutate)
        self.send_json({"ok": True, "stats": build_stats()})

    def handle_submit_review(self, body):
        """复习提交：FSRS-5 调度（旧 quality 0-5 兼容映射到 1-4 评级）。"""
        cid = body.get("id", "")
        try:
            quality = max(0, min(5, int(body.get("quality", 3))))
        except (TypeError, ValueError):
            quality = 3
        rating = body.get("rating")
        if rating is not None:
            try:
                rating = max(1, min(4, int(rating)))
            except (TypeError, ValueError):
                rating = fsrs.GOOD
        else:
            # quality 0-1→忘记, 2→吃力, 3→良好, 4-5→轻松
            rating = fsrs.AGAIN if quality <= 1 else fsrs.HARD if quality == 2 \
                else fsrs.EASY if quality >= 4 else fsrs.GOOD
        cards = STORE.load(edata.F_CARDS, [])
        idx = next((i for i, c in enumerate(cards) if c.get("id") == cid), None)
        if idx is None:
            self.send_json({"error": "卡片不存在"}, 404)
            return
        cards[idx] = fsrs.review(cards[idx], rating)
        cards[idx]["mastered"] = cards[idx]["reps"] >= 4 and cards[idx].get("stability", 0) >= 21
        STORE.save(edata.F_CARDS, cards)
        self.send_json({"ok": True, "card": cards[idx], "algorithm": "FSRS-5"})

    def handle_add_knowledge(self, body):
        subject = str(body.get("subject") or "").strip()
        if not subject:
            self.send_json({"error": "subject 必填"}, 400)
            return
        def mutate(k):
            entry = k.setdefault(subject, {"prob": 0.2, "mastered": False})
            if body.get("notes"):
                entry["notes"] = body["notes"]
            if body.get("prob") is not None:
                try:
                    entry["prob"] = max(0.0, min(1.0, float(body["prob"])))
                    entry["mastered"] = entry["prob"] >= 0.8
                except (TypeError, ValueError):
                    pass
            return k
        STORE.mutate(edata.F_KNOWLEDGE, mutate)
        self.send_json({"ok": True, "knowledge": STORE.load(edata.F_KNOWLEDGE, {})})

    def handle_generate_plan(self, body):
        plan, err = generate_plan(body)
        if err:
            self.send_json({"error": err}, 400)
            return
        self.send_json({"ok": True, "plan": plan})

    def handle_checkin(self, body):
        day = edata.today()
        note = str(body.get("note") or "").strip()[:200]
        minutes = _int(body.get("minutes"), 0, 0, 1440)
        def mutate(items):
            for it in items:
                if it.get("date") == day:
                    it["note"] = note or it.get("note", "")
                    it["minutes"] = it.get("minutes", 0) + minutes
                    return items
            items.append({"date": day, "note": note, "minutes": minutes,
                          "answered": STORE.load(edata.F_STATS, {}).get("total", 0),
                          "created": edata.now_iso()})
            return items
        STORE.mutate(edata.F_CHECKIN, mutate)
        self.send_json({"ok": True, "days": STORE.load(edata.F_CHECKIN, []),
                        "streak": calc_streak()})

    def handle_add_note(self, body):
        text = str(body.get("text") or "").strip()
        if not text:
            self.send_json({"error": "text 必填"}, 400)
            return
        item = {"id": edata.uid("n"), "text": text[:4000],
                "subject": str(body.get("subject") or "").strip(),
                "created": edata.now_iso()}
        notes = STORE.load(edata.F_NOTES, [])
        notes.append(item)
        STORE.save(edata.F_NOTES, notes)
        self.send_json({"ok": True, "note": item})

    def handle_providers(self):
        providers = provider_chain()
        active = active_provider()
        self.send_json({
            "providers": [{k: v for k, v in p.items() if k != "key"} for p in providers],
            "active": active["id"] if active else None,
            "ready": active is not None,
            "hint": ("已找到可用模型，AI 功能开箱即用" if active
                     else "未检测到可用模型，请检查网络或在设置中填写自定义服务"),
        })

    def handle_ai_test(self, q):
        pid = q.get("provider", "")
        chain = provider_chain()
        target = next((p for p in chain if p["id"] == pid), None) if pid else active_provider()
        if not target:
            self.send_json({"ok": False, "error": "没有可测试的模型，请先选择一路"})
            return
        ok, models, err = ellm.probe_models(target["base_url"], target.get("key", ""))
        self.send_json({"ok": ok, "provider": target["id"], "label": target["label"],
                        "models": models[:40], "count": len(models), "error": err})

    def handle_save_llm_config(self, body):
        cfg = llm_config()
        for k in ("base_url", "model", "preferred"):
            if k in body:
                cfg[k] = str(body[k]).strip()
        if body.get("api_key"):
            cfg["api_key"] = str(body["api_key"]).strip()
        if "auto" in body:
            cfg["auto"] = bool(body["auto"])
        cfg["updated"] = edata.now_iso()
        STORE.save(edata.F_LLM, cfg)
        invalidate_provider_cache()
        active = active_provider()
        self.send_json({"ok": True, "saved": True,
                        "active": active["id"] if active else None,
                        "label": active["label"] if active else ""})

    def handle_ai_chat(self, body):
        messages = body.get("messages") or []
        if not isinstance(messages, list) or not messages:
            self.send_json({"error": "消息为空"}, 400)
            return
        clean = [{"role": m.get("role", "user"), "content": str(m.get("content", ""))[:8000]}
                 for m in messages if isinstance(m, dict) and m.get("content")]
        if not clean:
            self.send_json({"error": "消息内容为空"}, 400)
            return
        system = {"role": "system", "content": SYSTEM_PROMPT}
        chain = provider_chain()
        pid = body.get("provider")
        if pid:
            chain = sorted(chain, key=lambda p: 0 if p["id"] == pid else 1)
        ok, text, used, errs = ellm.chat_chain(chain, [system] + clean[-12:],
                                               temperature=float(body.get("temperature", 0.7)))
        if not ok:
            self.send_json({"error": "所有模型都调用失败：" + "；".join(errs[-3:])
                            if errs else "未找到可用模型，请在设置中添加服务",
                            "detail": errs}, 502)
            return
        self.send_json({"ok": True, "content": text, "provider": used,
                        "fallbacks": len(errs)})

    def handle_ai_explain(self, body):
        q = body.get("question") or ""
        if not str(q).strip():
            self.send_json({"error": "question 必填"}, 400)
            return
        msgs = [{"role": "user", "content":
                 "请用中文简明讲解下面这道题的解题思路（不超过 300 字，分点说清关键步骤，"
                 "不要直接只给答案）：\n\n" + str(q)[:3000]}]
        ok, text, used, errs = ellm.chat_chain(provider_chain(), msgs, temperature=0.5)
        if not ok:
            self.send_json({"error": "讲解失败：" + "；".join(errs[-2:])}, 502)
            return
        self.send_json({"ok": True, "content": text, "provider": used})

    def handle_analyze_material(self, body):
        text = str(body.get("text") or "").strip()
        if len(text) < 20:
            self.send_json({"error": "资料太短（至少 20 字）"}, 400)
            return
        prompt = (
            "你是备考辅导老师。请把下面资料拆解成结构化知识点清单，输出 JSON 数组，"
            "每个元素形如 {\"knowledge\":\"知识点名称\",\"points\":[\"要点1\",\"要点2\"],"
            "\"exam\":\"可能考法\"}。只输出 JSON，不要额外文字。控制在 12 个知识点以内。\n\n资料：\n"
            + text[:9000]
        )
        ok, raw, used, errs = ellm.chat_chain(provider_chain(),
                                              [{"role": "user", "content": prompt}],
                                              temperature=0.3, timeout=180)
        if not ok:
            self.send_json({"error": "解析失败：" + "；".join(errs[-2:])}, 502)
            return
        points = _parse_json_array(raw)
        self.send_json({"ok": True, "points": points, "raw": raw if not points else "",
                        "provider": used})

    def handle_generate_from_text(self, body):
        text = str(body.get("text") or "").strip()
        if len(text) < 10:
            self.send_json({"error": "资料文本太短，请粘贴知识点、考纲或真题内容"}, 400)
            return
        count = _int(body.get("count"), 10, 1, 50)
        subject = str(body.get("subject") or "综合").strip()
        title = str(body.get("title") or f"{subject}模拟卷").strip()
        qtype = str(body.get("type") or "单选题").strip()
        prompt = (
            f"你是出题老师。根据以下学习资料，生成 {count} 道「{subject}」{qtype}。"
            "要求：题干完整自洽，不依赖外部图表；每题 4 个选项，分别以 \"A. \" \"B. \" \"C. \" \"D. \" 开头；"
            "答案唯一且正确，解析要写清推导。"
            "严格输出 JSON 数组，每个元素含 question/options(字符串数组)/answer(单个字母)/"
            "explanation/knowledge，不要任何额外文字或代码块标记。\n\n"
            "学习资料：\n" + text[:9000]
        )
        ok, raw, used, errs = ellm.chat_chain(
            provider_chain(), [{"role": "user", "content": prompt}],
            temperature=0.4, timeout=240, max_tokens=8000)
        if not ok:
            self.send_json({"error": "出题失败：" + "；".join(errs[-3:])}, 502)
            return
        questions = _parse_questions(raw)
        if not questions:
            self.send_json({"error": "模型返回的内容无法解析成题目，请减少资料长度或降低题量后重试",
                            "raw": raw[:1500]}, 502)
            return
        for i, q in enumerate(questions):
            q.setdefault("id", f"ai_{abs(hash((title, i, q['question']))) % 10**8}")
            q["subject"] = q.get("subject") or subject
            q["stage"] = body.get("stage") or subject
        html = eqiz.make_quiz_html(title, subject, questions)
        self.send_json({"ok": True, "title": title, "subject": subject,
                        "count": len(questions), "questions": questions,
                        "html": html, "provider": used})

    def handle_generate_tool(self, body):
        title = str(body.get("title") or "模拟试卷").strip()
        subject = str(body.get("subject") or "综合").strip()
        questions = body.get("questions") or []
        if not isinstance(questions, list) or not questions:
            self.send_json({"error": "题目列表为空"}, 400)
            return
        clean = []
        for q in questions:
            n = eqbank.normalize(q, "manual")
            if n and n["is_choice"]:
                clean.append(n)
        if not clean:
            self.send_json({"error": "没有有效题目：每题都需要题干、4 个选项和正确选项字母"}, 400)
            return
        html = eqiz.make_quiz_html(title, subject, clean)
        self.send_json({"ok": True, "title": title, "subject": subject,
                        "count": len(clean), "html": html})

    def handle_import_questions(self, body):
        items = body.get("questions") or []
        source = "ai" if body.get("source") == "ai" else "custom"
        if not isinstance(items, list) or not items:
            self.send_json({"error": "questions 为空"}, 400)
            return
        added, skipped = BANK.add_user_questions(items, source)
        self.send_json({"ok": True, "added": added, "skipped": skipped,
                        "total": len(BANK.all_questions())})

    # ---------- v2 统一内核：画像 / 资料 / 溯源出题 ----------
    def handle_save_profile(self, body):
        prof = core.normalize_profile(body)
        STORE.save(edata.F_PROFILE, prof)
        self.send_json({"ok": True, "profile": prof,
                        "greeting": core.profile_greeting(prof)})

    def handle_add_material(self, body):
        """导入资料：文本 → 分段 → 带稳定 id 存库。支持去重。"""
        name = str(body.get("name") or "").strip()
        text = str(body.get("text") or "").strip()
        source_url = str(body.get("source_url") or "").strip()
        exam = str(body.get("exam") or "").strip()
        if len(text) < 20:
            self.send_json({"error": "资料太短（至少 20 字），请粘贴或上传后确认内容"}, 400)
            return
        mat = core.make_material(name or "未命名资料", text, source_url, exam)
        mats = STORE.load(edata.F_MATERIALS, [])
        dup = next((i for i, m in enumerate(mats) if m.get("id") == mat["id"]), None)
        if dup is not None:
            # 重复导入：更新而非新增
            mats[dup] = {**mat, "created": mats[dup].get("created", mat["created"])}
            action = "updated"
        else:
            mats.append(mat)
            action = "added"
        STORE.save(edata.F_MATERIALS, mats)
        self.send_json({"ok": True, "action": action, "id": mat["id"],
                        "name": mat["name"], "passages": len(mat["passages"]),
                        "char_count": mat["char_count"], "total": len(mats)})

    def handle_material_generate(self, mid, body):
        """从溯源资料出题：强制逐句标注来源，写回题库。"""
        mats = STORE.load(edata.F_MATERIALS, [])
        mat = next((m for m in mats if m.get("id") == mid), None)
        if not mat:
            self.send_json({"error": "资料不存在，请先导入"}, 404)
            return
        count = _int(body.get("count"), 5, 1, 20)
        subject = str(body.get("subject") or mat.get("exam") or "综合").strip()
        qtype = str(body.get("type") or "单选题").strip()
        prompt = core.build_grounded_generate_prompt(mat, count, subject, qtype)
        # token 按题量动态给，避免固定 8000 拖慢生成
        max_tok = min(4096, 320 + count * 220)
        ok, raw, used, errs = ellm.chat_chain(
            provider_chain(),
            [{"role": "system", "content": core.grounded_system_prompt()},
             {"role": "user", "content": prompt}],
            temperature=0.3, timeout=120, max_tokens=max_tok)
        if not ok:
            self.send_json({"error": "出题失败：" + "；".join(errs[-3:])}, 502)
            return
        questions = _parse_questions(raw)
        if not questions:
            self.send_json({"error": "模型返回无法解析成题目，请缩短资料或降低题量",
                            "raw": raw[:1500]}, 502)
            return
        # 补全溯源字段 + 来源资料 id + 写回题库
        # 容错：模型常把溯源写进 explanation 文本而非结构化字段，这里反解回来
        prof = STORE.load(edata.F_PROFILE, {})
        for i, q in enumerate(questions):
            expl = str(q.get("explanation") or "")
            # 文本证据优先：解析里明确标了标签就以文本为准，
            # 因为模型常把溯源写进 explanation 而没有填结构化字段。
            if "🟢" in expl or "来自资料" in expl or "来自你的资料" in expl:
                prov = "material"
            elif "🟡" in expl or "AI补充" in expl or "AI 补充" in expl:
                prov = "ai"
            elif "⚠️" in expl or "AI生成" in expl or "AI 生成" in expl:
                prov = "generated"
            else:
                # 文本没标，再看结构化字段
                field = str(q.get("provenance") or "").strip().lower()
                prov = field if field in ("material", "ai", "generated") else "generated"
            q["provenance"] = prov
            para = str(q.get("source_para") or "").strip()
            if not para:
                m = re.search(r"资料\s*\[?(\d+)\]?\s*(段|原文|指出|列举)", expl)
                if m:
                    para = f"[{m.group(1)}]"
            if not para and prov == "material":
                # 反查：题目/解析与哪个资料段落最相似，用共同字符覆盖率定位
                para = _match_paragraph(mat, q.get("question", "") + " " + expl)
            q["source_para"] = para[:20]
            q["source_material"] = mid
            q["id"] = q.get("id") or f"g_{abs(hash((mid, i, q['question']))) % 10**8}"
            q.setdefault("subject", subject)
            q.setdefault("stage", prof.get("goal") or subject)
        added, skipped = BANK.add_user_questions(questions, "grounded")
        prov_count = {k: sum(1 for q in questions if q["provenance"] == k)
                      for k in ("material", "ai", "generated")}
        html = eqiz.make_quiz_html(f"{mat['name']}·溯源练习", subject, questions)
        self.send_json({"ok": True, "material_id": mid, "subject": subject,
                        "count": len(questions), "questions": questions,
                        "provenance": prov_count, "added": added, "skipped": skipped,
                        "html": html, "provider": used})

    def handle_submit_review_fsrs(self, body):
        """FSRS 复习提交：用评级 1-4 更新卡片调度。"""
        cards = STORE.load(edata.F_CARDS, [])
        cid = str(body.get("id") or "")
        rating = _int(body.get("rating"), fsrs.GOOD, 1, 4)
        idx = next((i for i, c in enumerate(cards) if c.get("id") == cid), None)
        if idx is None:
            self.send_json({"error": "卡片不存在"}, 404)
            return
        cards[idx] = fsrs.review(cards[idx], rating)
        STORE.save(edata.F_CARDS, cards)
        self.send_json({"ok": True, "card": cards[idx]})

    def handle_add_source(self, body):
        name = str(body.get("name") or "").strip()
        url = str(body.get("url") or "").strip()
        if not name or not url:
            self.send_json({"error": "名称和网址必填"}, 400)
            return
        if not url.startswith(("http://", "https://")):
            self.send_json({"error": "网址需以 http:// 或 https:// 开头"}, 400)
            return
        items = STORE.load(edata.F_SOURCES, [])
        item = {"id": edata.uid("c"), "name": name[:60], "url": url[:500],
                "category": str(body.get("category") or "自定义")[:20],
                "exam": str(body.get("exam") or "")[:40],
                "desc": str(body.get("desc") or "")[:200],
                "custom": True}
        items.append(item)
        STORE.save(edata.F_SOURCES, items)
        self.send_json({"ok": True, "id": item["id"]})

    def handle_pan_favorite(self, body):
        action = body.get("action", "add")
        items = STORE.load(edata.F_PAN_FAV, [])
        if action == "add":
            title = str(body.get("title") or "").strip()
            url = str(body.get("url") or "").strip()
            if not title or not url:
                self.send_json({"error": "标题和链接必填"}, 400)
                return
            item = {"id": edata.uid("p"), "title": title[:120], "url": url[:600],
                    "desc": str(body.get("desc") or "")[:200], "created": edata.now_iso()}
            items.append(item)
            STORE.save(edata.F_PAN_FAV, items)
            self.send_json({"ok": True, "id": item["id"]})
        elif action == "delete":
            fid = body.get("id", "")
            STORE.save(edata.F_PAN_FAV, [f for f in items if f.get("id") != fid])
            self.send_json({"ok": True})
        else:
            self.send_json({"error": "未知操作"}, 400)

    def handle_export(self):
        payload = {
            "app": "ExamBoost",
            "version": VERSION,
            "exported": edata.now_iso(),
            "stats": STORE.load(edata.F_STATS),
            "mistakes": STORE.load(edata.F_MISTAKES, []),
            "knowledge": STORE.load(edata.F_KNOWLEDGE, {}),
            "cards": STORE.load(edata.F_CARDS, []),
            "plan": STORE.load(edata.F_PLAN),
            "checkin": STORE.load(edata.F_CHECKIN, []),
            "notes": STORE.load(edata.F_NOTES, []),
            "questions_custom": STORE.load(edata.F_QCUSTOM, []),
        }
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Disposition",
                        f'attachment; filename="examboost-backup-{edata.today()}.json"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def handle_reset(self, body):
        if body.get("confirm") != "YES":
            self.send_json({"error": "危险操作：需要传 confirm=YES 才会清空学习数据"}, 400)
            return
        keep_llm = body.get("keep_llm", True)
        removed = []
        for name in edata.ALL_DATA_FILES:
            if keep_llm and name == edata.F_LLM:
                continue
            p = STORE.path(name)
            if p.exists():
                p.unlink()
                removed.append(name)
        invalidate_provider_cache()
        self.send_json({"ok": True, "removed": removed})

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {fmt % args}\n")


SYSTEM_PROMPT = (
    "你是 ExamBoost 综合备考导师，服务考公考编、考研、四六级、K12、职业资格等各学段学习者。"
    "规则：1) 中文回答，简洁分点，先给结论再讲思路；2) 不编造真题、政策原文、分数线和官方数据，"
    "不确定就直说不确定；3) 出题类请求必须给唯一正确答案和可核验的推导；"
    "4) 讲解题时先点出考查知识点，再给解题步骤，最后给易错提醒；"
    "5) 不承诺上岸或提分幅度。"
)


# ------------------------------------------------------------------
#  工具函数
# ------------------------------------------------------------------
def _bigrams(text):
    s = re.sub(r"[\s，。、；：（）()\[\]《》“”\"']", "", str(text or ""))
    return {s[i:i + 2] for i in range(len(s) - 1)}


def _match_paragraph(material, text):
    """把一段文本反查到资料里最相似的段落，返回 [N]。用于补全 AI 漏标的溯源定位。"""
    target = _bigrams(text)
    if not target:
        return ""
    best_i, best_score = 0, 0.0
    for i, p in enumerate(material.get("passages", []), 1):
        grams = _bigrams(p.get("text", ""))
        if not grams:
            continue
        score = len(target & grams) / len(grams)  # 覆盖段落的比例
        if score > best_score:
            best_i, best_score = i, score
    return f"[{best_i}]" if best_score > 0.08 else ""


def _read_json(path: Path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _int(v, default, lo, hi):
    try:
        n = int(v)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _pick_without_repeat(pool, count):
    """抽题尽量不与近期重复；池子太小时自动放开。"""
    with _asked["lock"]:
        recent = set(_asked["ids"][-max(20, len(pool) // 2):])
        fresh = [q for q in pool if q["id"] not in recent]
        picked = random.sample(fresh, min(count, len(fresh))) if fresh else \
            random.sample(pool, min(count, len(pool)))
        for q in picked:
            _asked["ids"].append(q["id"])
        if len(_asked["ids"]) > 2000:
            _asked["ids"] = _asked["ids"][-1000:]
        return picked


def _parse_json_array(text):
    s = str(text or "").strip()
    if "```" in s:
        import re
        blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", s)
        if blocks:
            s = blocks[0].strip()
    try:
        data = json.loads(s)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        pass
    import re
    m = re.search(r"\[[\s\S]*\]", s)
    if m:
        for cand in (m.group(0),):
            try:
                data = json.loads(cand)
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                continue
    return []


def _parse_questions(content):
    arr = _parse_json_array(content)
    out = []
    for q in arr:
        n = eqbank.normalize(q, "ai")
        if n and n["question"] and n["options"] and n["answer"]:
            out.append(n)
    return out


def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def port_in_use(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.6)
        return s.connect_ex((host, port)) == 0


def find_free_port(host, start, tries=20):
    for p in range(start, start + tries):
        if not port_in_use(host if host != "0.0.0.0" else "127.0.0.1", p):
            return p
    return start


def main():
    parser = argparse.ArgumentParser(description="ExamBoost AI Server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default="0.0.0.0",
                        help="绑定地址：0.0.0.0 允许局域网访问，127.0.0.1 仅本机")
    parser.add_argument("--data-dir", default=str(DATA_DIR), help="学习数据目录")
    parser.add_argument("--no-auto-port", action="store_true", help="端口被占用时直接报错")
    args = parser.parse_args()

    global STORE, BANK
    data_dir = Path(args.data_dir)
    STORE = edata.Store(data_dir)
    BANK = eqbank.QuestionBank(APP_DIR, STORE)

    host = args.host
    port = args.port
    probe_host = "127.0.0.1" if host in ("0.0.0.0", "") else host
    if port_in_use(probe_host, port) and not args.no_auto_port:
        new_port = find_free_port(probe_host, port + 1)
        print(f"⚠️  端口 {port} 已被占用，自动改用 {new_port}")
        port = new_port

    try:
        server = ThreadingHTTPServer((host, port), Handler)
    except OSError as e:
        print(f"❌ 启动失败：{e}\n   请换个端口重试：python3 server.py --port 3001")
        sys.exit(1)
    server.daemon_threads = True

    lan = get_lan_ip()
    print(f"ExamBoost AI v{VERSION} 已启动")
    print(f"  本机访问   : http://localhost:{port}")
    if host == "0.0.0.0":
        print(f"  手机/平板  : http://{lan}:{port}  （需同一 WiFi）")
    print(f"  数据目录   : {data_dir}")
    print(f"  内置题库   : {BANK.builtin_count()} 题，用户题库 {len(BANK.user_questions())} 题")
    active = active_provider()
    print(f"  AI 模型    : {active['label'] if active else '未检测到（可在设置页填自定义服务）'}")
    print("  按 Ctrl+C 停止")
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n正在关闭…")
        server.shutdown()


if __name__ == "__main__":
    main()
