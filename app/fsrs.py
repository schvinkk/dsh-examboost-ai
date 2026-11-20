"""FSRS (Free Spaced Repetition Scheduler) 间隔重复调度 —— ExamBoost 统一内核。

严格移植 open-spaced-repetition/py-fsrs (MIT) 的 FSRS-5 核心公式，零第三方依赖。
三种形态（独立网页 / dsh-go 插件 / Agent Skill）共用本模块。

评级：1=忘记(Again) 2=吃力(Hard) 3=良好(Good) 4=轻松(Easy)
"""
import math
from datetime import datetime, timedelta

AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4

# py-fsrs v4 DEFAULT_PARAMETERS（21 个，最后一个是 decay）
DEFAULT_PARAMS = (
    0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001,
    1.8722, 0.1666, 0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014,
    1.8729, 0.5425, 0.0912, 0.0658, 0.1542,  # w20 = decay
)
STABILITY_MIN = 0.001
MIN_DIFFICULTY, MAX_DIFFICULTY = 1.0, 10.0
DEFAULT_DESIRED_RETENTION = 0.9
MAX_INTERVAL = 36500

DECAY = -DEFAULT_PARAMS[20]                      # -0.1542
FACTOR = 0.9 ** (1 / DECAY) - 1                  # 使 R(interval)=desired_retention


def _clamp(d, lo, hi):
    return max(lo, min(hi, d))


def initial_stability(rating, w=DEFAULT_PARAMS):
    return max(STABILITY_MIN, w[rating - 1])


def initial_difficulty(rating, w=DEFAULT_PARAMS):
    d = w[4] - (math.e ** (w[5] * (rating - 1))) + 1
    return _clamp(d, MIN_DIFFICULTY, MAX_DIFFICULTY)


def retrievability(elapsed_days, stability):
    """R(t,S) = (1 + FACTOR·t/S)^DECAY"""
    if not stability or stability <= 0:
        return 0.0
    return (1 + FACTOR * max(0.0, elapsed_days) / stability) ** DECAY


def next_interval(stability, desired_retention=DEFAULT_DESIRED_RETENTION):
    """I = (S/FACTOR)·(R^(1/DECAY) - 1)，天。"""
    iv = (stability / FACTOR) * ((desired_retention ** (1 / DECAY)) - 1)
    return max(1, min(MAX_INTERVAL, round(iv)))


def _next_difficulty(difficulty, rating, w=DEFAULT_PARAMS):
    arg1 = w[4] - (math.e ** (w[5] * (EASY - 1))) + 1
    delta_d = -(w[6] * (rating - 3))
    arg2 = difficulty + (10.0 - difficulty) * delta_d / 9.0
    return _clamp(w[7] * arg1 + (1 - w[7]) * arg2, MIN_DIFFICULTY, MAX_DIFFICULTY)


def _next_forget_stability(difficulty, stability, r, w=DEFAULT_PARAMS):
    long_term = (w[11] * (difficulty ** -w[12])
                 * (((stability + 1) ** w[13]) - 1)
                 * (math.e ** ((1 - r) * w[14])))
    short_term = stability / (math.e ** (w[17] * w[18]))
    return min(long_term, short_term)


def _next_recall_stability(difficulty, stability, r, rating, w=DEFAULT_PARAMS):
    hard_penalty = w[15] if rating == HARD else 1
    easy_bonus = w[16] if rating == EASY else 1
    return stability * (
        1
        + (math.e ** w[8])
        * (11 - difficulty)
        * (stability ** -w[9])
        * ((math.e ** ((1 - r) * w[10])) - 1)
        * hard_penalty
        * easy_bonus
    )


def _short_term_stability(stability, rating, w=DEFAULT_PARAMS):
    inc = (math.e ** (w[17] * (rating - 3 + w[18]))) * (stability ** -w[19])
    if rating in (HARD, GOOD, EASY):
        inc = max(inc, 1.0)
    return max(STABILITY_MIN, stability * inc)


def review(card, rating, now=None, desired_retention=DEFAULT_DESIRED_RETENTION,
           w=DEFAULT_PARAMS):
    """复习一张卡，返回更新后的 dict。

    card: {id, stability?, difficulty?, reps?, lapses?, due?, last_review?}
    """
    now = now or datetime.now()
    if isinstance(now, str):
        now = datetime.fromisoformat(now)
    rating = int(rating)
    if rating not in (AGAIN, HARD, GOOD, EASY):
        rating = GOOD

    reps = int(card.get("reps", 0))
    lapses = int(card.get("lapses", 0))
    stability = card.get("stability")
    difficulty = card.get("difficulty")
    last = card.get("last_review")

    days = None
    if last:
        try:
            days = (now - datetime.fromisoformat(last)).days
        except (ValueError, TypeError):
            days = None

    # 首 reviewing：初始化 S/D
    if not stability or not difficulty:
        stability = initial_stability(rating, w)
        difficulty = initial_difficulty(rating, w)
    elif days is not None and days < 1:
        # 同日短期复习（学习步）
        stability = _short_term_stability(stability, rating, w)
        difficulty = _next_difficulty(difficulty, rating, w)
    else:
        r = retrievability(days or 0, stability)
        if rating == AGAIN:
            stability = _next_forget_stability(difficulty, stability, r, w)
        else:
            stability = _next_recall_stability(difficulty, stability, r, rating, w)
        stability = max(STABILITY_MIN, stability)
        difficulty = _next_difficulty(difficulty, rating, w)

    if rating == AGAIN:
        lapses += 1
        interval = 1  # 遗忘进入次日重学
    elif reps == 0:
        interval = 1  # 首张新卡次日复现
    else:
        interval = next_interval(stability, desired_retention)

    return {
        **card,
        "stability": round(stability, 4),
        "difficulty": round(difficulty, 4),
        "reps": reps + 1,
        "lapses": lapses,
        "last_review": now.isoformat(timespec="seconds"),
        "due": (now + timedelta(days=interval)).date().isoformat(),
        "interval": interval,
        "retrievability": round(retrievability(interval, stability), 4),
    }


def due_count(cards, today=None):
    today = today or datetime.now().date().isoformat()
    return sum(1 for c in cards if str(c.get("due", "9999-12-31")) <= today)


def fsrs_to_legacy(card):
    """兼容旧前端的 SM-2 字段显示。"""
    interval = int(card.get("interval", 1))
    return {
        "repetitions": int(card.get("reps", 0)),
        "interval": interval,
        "ease": round(1.0 + (10.0 - float(card.get("difficulty", 5.0))) * 0.2, 2),
    }
