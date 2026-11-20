"""题库层：内置题库（data_bank/）+ 用户自定义 + AI 生成，统一查询与抽题。"""
import json
import random
import threading
from pathlib import Path

import edata

# 内置题库目录（随仓库分发）
BANK_DIR_NAME = "data_bank"

# 兼容旧版：内置示例题，保证 data_bank/ 缺失时也能跑起来
SEED_QUESTIONS = [
    {
        "id": "kg_000", "stage": "考公考编", "subject": "行测", "type": "数量关系",
        "knowledge": "容斥问题",
        "question": "某班有 40 名学生，其中 25 人会游泳，18 人会打篮球，既会游泳又会打篮球的有 10 人。问既不会游泳也不会打篮球的有几人？",
        "options": ["A. 5", "B. 6", "C. 7", "D. 8"], "answer": "C",
        "explanation": "容斥原理：至少会一项的有 25 + 18 - 10 = 33 人，故两项都不会的有 40 - 33 = 7 人。选 C。",
        "difficulty": 1, "source": "模拟原创题",
    },
    {
        "id": "kg_000b", "stage": "考公考编", "subject": "行测", "type": "判断推理",
        "knowledge": "图形推理",
        "question": "从所给四个选项中，选择最合适的一个填入问号处，使之呈现一定规律：第一行 ○△□，第二行 △□○，第三行 □○？",
        "options": ["A. ○", "B. △", "C. □", "D. 无法确定"], "answer": "A",
        "explanation": "每行都是 ○△□ 三个图形的循环排列，第三行已有 □○，缺 ○。选 A。",
        "difficulty": 1, "source": "模拟原创题",
    },
    {
        "id": "ky_000", "stage": "考研", "subject": "政治", "type": "单选题",
        "knowledge": "马原·唯物论",
        "question": "马克思主义哲学认为，物质的唯一特性是？",
        "options": ["A. 运动性", "B. 客观实在性", "C. 可知性", "D. 矛盾性"], "answer": "B",
        "explanation": "列宁指出物质的唯一特性是客观实在性，它存在于人的意识之外，可以为人的意识所反映。选 B。",
        "difficulty": 1, "source": "模拟原创题",
    },
]

_lock = threading.RLock()


class QuestionBank:
    def __init__(self, app_dir: Path, store: "edata.Store"):
        self.app_dir = Path(app_dir)
        self.store = store
        self._builtin = []
        self._index = {}
        self.reload_builtin()

    # ---------- 内置题库 ----------
    def reload_builtin(self):
        items = []
        seen = set()
        bank_dir = self.app_dir / BANK_DIR_NAME
        files = sorted(bank_dir.glob("*.json")) if bank_dir.is_dir() else []
        for f in files:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError, UnicodeDecodeError):
                continue
            if not isinstance(data, list):
                continue
            for q in data:
                norm = normalize(q, f.stem)
                if norm and norm["id"] not in seen:
                    seen.add(norm["id"])
                    items.append(norm)
        for q in SEED_QUESTIONS:
            norm = normalize(q, "seed")
            if norm and norm["id"] not in seen:
                seen.add(norm["id"])
                items.append(norm)
        self._builtin = items
        self._index = _build_index(items)

    def builtin_count(self):
        return len(self._builtin)

    # ---------- 用户题库 ----------
    def user_questions(self):
        custom = self.store.load(edata.F_QCUSTOM, [])
        ai = self.store.load(edata.F_QAI, [])
        out = []
        for src, arr in (("custom", custom), ("ai", ai)):
            for q in arr:
                norm = normalize(q, src)
                if norm:
                    out.append(norm)
        return out

    def add_user_questions(self, questions, source="custom"):
        """入库一批题，返回 (新增数, 跳过数)。"""
        key = edata.F_QCUSTOM if source == "custom" else edata.F_QAI
        with _lock:
            existing = self.store.load(key, [])
            have = {q.get("id") for q in existing if isinstance(q, dict)}
            added = skipped = 0
            for q in questions:
                norm = normalize(q, source)
                if not norm or norm["id"] in have:
                    skipped += 1
                    continue
                have.add(norm["id"])
                existing.append(norm)
                added += 1
            self.store.save(key, existing)
            return added, skipped

    def delete_user_question(self, qid):
        with _lock:
            removed = 0
            for key in (edata.F_QCUSTOM, edata.F_QAI):
                arr = self.store.load(key, [])
                new = [q for q in arr if not (isinstance(q, dict) and q.get("id") == qid)]
                if len(new) != len(arr):
                    removed += len(arr) - len(new)
                    self.store.save(key, new)
            return removed

    # ---------- 查询 ----------
    def all_questions(self, include_user=True):
        items = list(self._builtin)
        if include_user:
            ids = {q["id"] for q in items}
            for q in self.user_questions():
                if q["id"] not in ids:
                    items.append(q)
        return items

    def query(self, stage="", subject="", qtype="", knowledge="", difficulty=0,
              keyword="", source_filter="", limit=0, exclude_ids=None):
        items = self.all_questions()
        if source_filter == "builtin":
            ids = {q["id"] for q in self._builtin}
            items = [q for q in items if q["id"] in ids]
        elif source_filter == "user":
            ids = {q["id"] for q in self.user_questions()}
            items = [q for q in items if q["id"] in ids]
        if stage:
            items = [q for q in items if q["stage"] == stage]
        if subject:
            items = [q for q in items if q["subject"] == subject]
        if qtype:
            items = [q for q in items if q["type"] == qtype]
        if knowledge:
            items = [q for q in items if knowledge in q["knowledge"]]
        if difficulty:
            items = [q for q in items if q["difficulty"] == difficulty]
        if keyword:
            kw = keyword.strip()
            items = [q for q in items if kw in q["question"] or kw in q["knowledge"]
                     or kw in q.get("explanation", "")]
        if exclude_ids:
            ex = set(exclude_ids)
            items = [q for q in items if q["id"] not in ex]
        if limit and limit > 0:
            items = items[:limit]
        return items

    def facets(self):
        """返回学段/科目/题型/知识点的层级统计，供前端筛选器。"""
        items = self.all_questions()
        out = {"stages": {}, "subjects": {}, "types": {}, "knowledge": {}, "total": len(items)}
        for q in items:
            out["stages"][q["stage"]] = out["stages"].get(q["stage"], 0) + 1
            key = f'{q["stage"]}/{q["subject"]}'
            out["subjects"][key] = out["subjects"].get(key, 0) + 1
            out["types"][q["type"]] = out["types"].get(q["type"], 0) + 1
            if q["knowledge"]:
                out["knowledge"][q["knowledge"]] = out["knowledge"].get(q["knowledge"], 0) + 1
        return out

    def get(self, qid):
        for q in self.all_questions():
            if q["id"] == qid:
                return q
        return None

    def pick(self, filters, count=1, exclude_ids=None, shuffle=True):
        """按条件抽题。默认不重复抽（排除已答过的），抽完自动重置。"""
        pool = self.query(**filters, exclude_ids=exclude_ids)
        if not pool:
            pool = self.query(**filters)
        if not pool:
            return []
        if shuffle:
            random.shuffle(pool)
        return pool[:max(1, count)]


def normalize(q, fallback_tag="q"):
    """把任意来源的题目规整成统一结构；无效题返回 None。"""
    if not isinstance(q, dict):
        return None
    text = str(q.get("question") or "").strip()
    if not text:
        return None
    options = q.get("options") or []
    if not isinstance(options, list):
        options = []
    options = [str(o).strip() for o in options if str(o).strip()]
    answer = str(q.get("answer") or "").strip().upper()
    if len(answer) > 1:
        answer = answer[0]
    if answer not in ("A", "B", "C", "D", "E", "F"):
        answer = ""
    try:
        diff = int(q.get("difficulty") or 1)
    except (TypeError, ValueError):
        diff = 1
    diff = max(1, min(3, diff))
    stage = str(q.get("stage") or q.get("exam") or "通用").strip() or "通用"
    subject = str(q.get("subject") or stage).strip() or "通用"
    qtype = str(q.get("type") or "选择题").strip() or "选择题"
    knowledge = str(q.get("knowledge") or "").strip()
    return {
        "id": str(q.get("id") or f"{fallback_tag}_{abs(hash(text)) % 10**9}"),
        "stage": stage,
        "subject": subject,
        "type": qtype,
        "knowledge": knowledge,
        "question": text,
        "options": options,
        "answer": answer,
        "explanation": str(q.get("explanation") or "").strip(),
        "difficulty": diff,
        "source": str(q.get("source") or "模拟原创题").strip(),
        "is_choice": bool(options) and bool(answer),
    }


def _build_index(items):
    idx = {}
    for q in items:
        idx.setdefault(q["subject"], []).append(q)
    return idx
