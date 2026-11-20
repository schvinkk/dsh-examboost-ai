"""ExamBoost 本地存储层（纯标准库，零依赖）。

所有学习数据写在 data/ 目录，绝不上传。写操作加进程内锁，避免并发损坏。
"""
import json
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

_LOCK = threading.RLock()

F_STATS = "stats.json"
F_MISTAKES = "mistakes.json"
F_KNOWLEDGE = "knowledge.json"
F_CARDS = "cards.json"
F_PLAN = "plan.json"
F_CHECKIN = "checkin.json"
F_NOTES = "notes.json"
F_LLM = "llm_config.json"
F_SOURCES = "sources_custom.json"
F_PAN_FAV = "pan_favorites.json"
F_QCUSTOM = "questions_custom.json"
F_QAI = "questions_ai.json"
F_EXAMLOG = "exam_log.json"

ALL_DATA_FILES = [
    F_STATS, F_MISTAKES, F_KNOWLEDGE, F_CARDS, F_PLAN, F_CHECKIN, F_NOTES,
    F_SOURCES, F_PAN_FAV, F_QCUSTOM, F_QAI, F_EXAMLOG,
]

_DEFAULTS = {
    F_STATS: {"total": 0, "correct": 0, "by_subject": {}, "by_day": {}},
    F_MISTAKES: [],
    F_KNOWLEDGE: {},
    F_CARDS: [],
    F_PLAN: None,
    F_CHECKIN: [],
    F_NOTES: [],
    F_LLM: {},
    F_SOURCES: [],
    F_PAN_FAV: [],
    F_QCUSTOM: [],
    F_QAI: [],
    F_EXAMLOG: [],
}


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def uid(prefix: str = "id") -> str:
    return f"{prefix}_{int(time.time() * 1000)}_{os.getpid() % 997}"


class Store:
    """一个数据目录 = 一个 Store。"""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, name: str) -> Path:
        return self.root / name

    def load(self, name: str, default=None):
        with _LOCK:
            p = self.path(name)
            if default is None:
                default = _DEFAULTS.get(name)
            if not p.exists():
                return _clone(default)
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError, OSError):
                # 损坏时改名备份并返回默认值，不让整个应用崩掉
                try:
                    p.rename(self.path(f"{name}.broken-{int(time.time())}"))
                except OSError:
                    pass
                return _clone(default)

    def save(self, name: str, data) -> None:
        with _LOCK:
            # 目录可能在运行期间被用户手动删除（排障时会这么做），写入前重建
            self.root.mkdir(parents=True, exist_ok=True)
            p = self.path(name)
            tmp = self.path(f"{name}.tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, p)
            try:
                os.chmod(p, 0o600)
            except OSError:
                pass

    def mutate(self, name: str, fn):
        """读-改-写原子操作：fn(data) 就地修改或返回新值。"""
        with _LOCK:
            data = self.load(name)
            result = fn(data)
            self.save(name, data if result is None else result)
            return data if result is None else result

    def protected_names(self):
        return set(ALL_DATA_FILES) | {F_LLM}


def _clone(v):
    if isinstance(v, (dict, list)):
        return json.loads(json.dumps(v))
    return v


# ---------------- 算法 ----------------

def sm2_review(repetitions: int, interval: int, ease: float, quality: int):
    """SM-2 间隔重复。quality 0-5，<3 视为忘记。"""
    quality = max(0, min(5, int(quality)))
    if quality >= 3:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 3
        else:
            interval = max(1, round(interval * ease))
        repetitions += 1
    else:
        repetitions = 0
        interval = 1
    ease = ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ease = max(1.3, min(3.0, ease))
    return repetitions, interval, round(ease, 2)


def bkt_update(prob: float, correct: bool, p_learn=0.25, p_guess=0.2, p_slip=0.1) -> float:
    """BKT 掌握度更新，返回新的 P(learned)。"""
    prob = min(0.99, max(0.01, float(prob)))
    if correct:
        num = prob * (1 - p_slip)
        den = num + (1 - prob) * p_guess
    else:
        num = prob * p_slip
        den = num + (1 - prob) * (1 - p_guess)
    new_p = num / den if den else prob
    if correct:
        new_p = min(0.99, new_p + (1 - new_p) * p_learn)
    return round(max(0.01, min(0.99, new_p)), 3)


def add_days(date_str: str, n: int) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=n)
    return d.strftime("%Y-%m-%d")


def date_range(start: str, days: int):
    return [add_days(start, i) for i in range(max(0, days))]
