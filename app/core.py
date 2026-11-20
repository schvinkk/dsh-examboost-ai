"""ExamBoost 统一内核 —— 三种形态共用（独立网页 / dsh-go 插件 / Agent Skill）。

提供：
1. 学习者画像 onboarding（谁/考什么/专业/有无资料）—— 先问清楚，不上来塞题
2. 溯源资料库 sources（每段资料带稳定 id + 出处定位，AI 出题逐句标注）
3. 溯源出题提示词（🟢来自材料 / 🟡AI补充 / ⚠️AI生成，材料外拒答）
4. 资料中枢目录（官方考试源 + 资源检索入口，均带可核验出处）

纯 Python 标准库，零依赖。所有数据落 data/ 目录，不上传。
"""
import json
import re
import hashlib
from datetime import datetime

# ============ 1. 学习者画像 ============

STAGES = [
    {"id": "primary", "label": "小学生", "icon": "🧒", "desc": "小学阶段课内学习"},
    {"id": "middle", "label": "中学生", "icon": "🧑‍🎓", "desc": "初中 / 中考"},
    {"id": "high", "label": "高中生", "icon": "🎓", "desc": "高中 / 高考"},
    {"id": "college", "label": "大学生", "icon": "📖", "desc": "大学课程 / 期末"},
    {"id": "kaoyan", "label": "考研", "icon": "🏛️", "desc": "研究生入学考试"},
    {"id": "kaogong", "label": "考公考编", "icon": "🏢", "desc": "公务员 / 事业单位"},
    {"id": "cert", "label": "考证", "icon": "📜", "desc": "职业资格 / 技能证书"},
    {"id": "adult", "label": "在职/自學", "icon": "💼", "desc": "在职提升 / 终身学习"},
]

# 每个阶段预设的常见考试方向（引导用，不强制）
EXAM_GOALS = {
    "primary": ["语文", "数学", "英语", "科学"],
    "middle": ["中考语文", "中考数学", "中考英语", "中考物理", "中考化学"],
    "high": ["高考语文", "高考数学", "高考英语", "高考物理", "高考历史"],
    "college": ["高数", "线性代数", "专业课", "大学英语", "期末考"],
    "kaoyan": ["政治", "英语一", "英语二", "数学一", "数学二", "专业课"],
    "kaogong": ["行测", "申论", "公共基础", "面试", "事业单位职测"],
    "cert": ["教师资格", "法律职业", "会计", "医师/药士", "计算机等级", "四六级"],
    "adult": ["学历提升", "职业培训", "语言能力", "兴趣学习"],
}

PROFILE_FIELDS = ("stage", "goal", "major", "has_material", "target_date", "daily_minutes")


def empty_profile():
    return {
        "stage": "",        # STAGES 里的 id
        "goal": "",         # 考试/学习目标
        "major": "",        # 专业/方向
        "has_material": None,  # True/False/None —— 手上是否有资料
        "target_date": "",  # 目标考试日期 YYYY-MM-DD
        "daily_minutes": 30,
        "onboarded": False,
        "updated": "",
    }


def normalize_profile(raw):
    """清洗画像输入，只保留合法字段。"""
    p = empty_profile()
    if not isinstance(raw, dict):
        return p
    for k in PROFILE_FIELDS:
        if k in raw:
            p[k] = raw[k]
    # 校验 stage
    if p["stage"] not in {s["id"] for s in STAGES}:
        p["stage"] = ""
    p["has_material"] = (True if p["has_material"] in (True, "true", "yes", 1, "1")
                         else False if p["has_material"] in (False, "false", "no", 0, "0")
                         else None)
    try:
        p["daily_minutes"] = max(5, min(480, int(p["daily_minutes"])))
    except (ValueError, TypeError):
        p["daily_minutes"] = 30
    p["onboarded"] = bool(raw.get("onboarded")) and bool(p["stage"]) and bool(p["goal"])
    p["updated"] = datetime.now().isoformat(timespec="seconds")
    return p


def stage_label(stage_id):
    for s in STAGES:
        if s["id"] == stage_id:
            return s["label"]
    return "学习者"


def profile_greeting(p):
    """根据画像生成首屏个性化问候与推荐路径。"""
    if not p.get("onboarded"):
        return "先花 30 秒告诉我你的情况，我再给你合适的学习方法。"
    who = stage_label(p["stage"])
    goal = p["goal"] or "学习目标"
    parts = [f"{who} · 目标「{goal}」"]
    if p.get("major"):
        parts.append(f"专业/方向：{p['major']}")
    if p.get("target_date"):
        parts.append(f"目标日期：{p['target_date']}")
    if p.get("has_material"):
        parts.append("你已有资料 → 建议从「导入资料」开始，我按你的资料出题")
    elif p.get("has_material") is False:
        parts.append("你还没有资料 → 建议从「找资料」开始，我帮你找带出处的来源")
    return " ｜ ".join(parts)


# ============ 2. 溯源资料库 ============

def material_id(text, name=""):
    """资料稳定 id：内容 hash + 名称，重复导入可去重。"""
    h = hashlib.sha256((str(name) + "\n" + str(text)).encode("utf-8")).hexdigest()[:12]
    return "mat_" + h


def split_passages(text, max_chars=600):
    """把长资料切成带定位的段落，每段可作为溯源单位。"""
    text = re.sub(r"\r\n?", "\n", str(text or "")).strip()
    if not text:
        return []
    # 优先按空行分段，其次按句子
    blocks = [b.strip() for b in re.split(r"\n\s*\n+", text) if b.strip()]
    passages = []
    cursor = 1
    for b in blocks:
        if len(b) <= max_chars:
            passages.append({"loc": f"第{cursor}段", "text": b})
            cursor += 1
        else:
            # 长块按句子切
            sents = re.split(r"(?<=[。！？.!?；;])\s*", b)
            buf = ""
            for s in sents:
                if len(buf) + len(s) > max_chars and buf:
                    passages.append({"loc": f"第{cursor}段", "text": buf.strip()})
                    cursor += 1
                    buf = ""
                buf += s
            if buf.strip():
                passages.append({"loc": f"第{cursor}段", "text": buf.strip()})
                cursor += 1
    return passages


def make_material(name, text, source_url="", exam=""):
    """构造一份带溯源的资料对象。"""
    passages = split_passages(text)
    return {
        "id": material_id(text, name),
        "name": str(name or "未命名资料")[:80],
        "source_url": str(source_url or "")[:500],
        "exam": str(exam or "")[:60],
        "text": str(text),
        "passages": passages,
        "char_count": len(str(text)),
        "created": datetime.now().isoformat(timespec="seconds"),
    }


# 溯源标签含义（前端/提示词统一使用）
PROVENANCE = {
    "material": {"tag": "🟢", "label": "来自你的资料", "desc": "可追溯到资料和段落，能核对"},
    "ai": {"tag": "🟡", "label": "AI 补充", "desc": "AI 加的背景知识，可能和老师讲的不一样"},
    "generated": {"tag": "⚠️", "label": "AI 生成", "desc": "资料里没有，AI 自己编的，务必自己核对"},
}


def grounded_system_prompt():
    """出题/讲解的统一系统提示词：强制逐句溯源、材料外拒答。

    借鉴 ZeKaiNie/universal-examprep-skill 的 100% Grounded 反幻觉设计
    与 lynote-ai/ai-tutor 的「知识不能跑得比原文快」。
    """
    return (
        "你是 ExamBoost 备考教练。铁律：知识不能跑得比学员提供的资料快。\n"
        "1) 每个知识点、每道题的解析，都必须标注来源标签：\n"
        "   🟢【来自资料·段落定位】——内容能在给定资料里逐字找到，必须写出是哪一段；\n"
        "   🟡【AI补充】——资料里没有但属于公认背景，明确标注，可能与老师讲法不同；\n"
        "   ⚠️【AI生成】——资料里完全没有、AI 自己推的，明确标注并提醒学员核对。\n"
        "2) 出题优先用资料里确凿出现的内容。资料外的题必须标 ⚠️，且一页里 ⚠️ 题不超过 20%。\n"
        "3) 资料里没有答案的问题，不要编造标准答案，直接说『你的资料里没有这部分，建议补充资料』。\n"
        "4) 解析里凡引用资料原话，用引号原样摘录，不得改写后当成原文。\n"
        "宁可少出，不可编造。用户把你的输出当复习依据，编造会害人。"
    )


def build_grounded_generate_prompt(material, count, subject, qtype):
    """构造带资料段落编号的出题提示词。"""
    blocks = []
    for i, p in enumerate(material.get("passages", []), 1):
        blocks.append(f"[{i}] {p['text']}")
    corpus = "\n".join(blocks)[:12000]
    return (
        grounded_system_prompt() + "\n\n"
        f"任务：根据资料生成 {count} 道「{subject}」{qtype}。\n"
        "严格输出 JSON 数组，每个元素字段：\n"
        "  question, options(4个字符串，A./B./C./D. 开头), answer(A/B/C/D),\n"
        "  explanation(解析，开头带来源标签), provenance(material/ai/generated),\n"
        "  source_para(资料段落编号，如 [3]；provenance=material 时必填),\n"
        "  knowledge(知识点)\n"
        "provenance=material 时，题干和答案必须能在 source_para 指明的段落里找到依据。\n\n"
        f"资料（每段前有编号）：\n{corpus}"
    )


# ============ 3. 资料中枢目录 ============

# 官方考试源：逐个 URL Verified（2026-11-20 实测可达性见 verified 字段）
OFFICIAL_SOURCES = [
    {"name": "研招网", "exam": "考研", "url": "https://yz.chsi.com.cn/", "verified": True, "checked": "2026-11-21", "provides": "考研报名/考纲/调剂"},
    {"name": "中国教育考试网", "exam": "四六级", "url": "https://cet.neea.edu.cn/", "verified": True, "checked": "2026-11-21", "provides": "四六级报名/成绩"},
    {"name": "中国教育考试网(总站)", "exam": "综合", "url": "https://www.neea.edu.cn/", "verified": True, "checked": "2026-11-21", "provides": "各类教育考试公告"},
    {"name": "中小学教师资格考试", "exam": "教资", "url": "https://ntce.neea.edu.cn/", "verified": True, "checked": "2026-11-21", "provides": "教资报名/考纲"},
    {"name": "中国人事考试网", "exam": "职业资格", "url": "http://www.cpta.com.cn/", "verified": True, "checked": "2026-11-21", "provides": "职业资格报名/考纲"},
    {"name": "国家公务员局", "exam": "考公", "url": "http://www.scs.gov.cn/", "verified": True, "checked": "2026-11-21", "provides": "国考公告/大纲"},
    {"name": "阳光高考信息平台", "exam": "高考", "url": "https://gaokao.chsi.com.cn/", "verified": False, "checked": "2026-11-21", "provides": "高考招生信息"},
    {"name": "各省人事考试网", "exam": "考公考编", "url": "http://www.mohrss.gov.cn/", "verified": True, "checked": "2026-11-21", "provides": "省考/事业单位公告"},
]

# 资源检索入口：不是编造结果，而是给出可核验的检索式与平台
RESOURCE_SEARCH = [
    {"name": "GitHub 题库/资料", "kind": "code", "base": "https://github.com/search?q=",
     "tpl": "{kw} 题库", "desc": "搜开源题库与学习资料", "verified": True},
    {"name": "网盘资源聚合", "kind": "pan", "base": "",
     "tpl": "{kw}", "desc": "聚合检索网盘分享（跳转第三方）", "verified": None},
    {"name": "Bing 学习资料", "kind": "web", "base": "https://www.bing.com/search?q=",
     "tpl": "{kw} 考纲 PDF", "desc": "全网搜考纲/真题 PDF", "verified": True},
]


def search_url(entry, keyword):
    from urllib.parse import quote
    kw = str(keyword or "").strip()
    if not kw:
        return ""
    q = entry["tpl"].format(kw=kw)
    if entry.get("base"):
        return entry["base"] + quote(q)
    return ""  # 网盘聚合需要具体服务，留空由前端提示


def profile_recommend_sources(profile):
    """按画像推荐资料中枢入口：stage 优先，goal 关键词补充。"""
    goal = (profile.get("goal") or "").lower()
    stage = profile.get("stage", "")
    # stage → 关键词映射，覆盖用户目标只写科目名（如"行测"）的情况
    stage_map = {
        "kaoyan": {"考研"},
        "kaogong": {"考公", "考公考编"},
        "high": {"高考"},
        "middle": {"中考"},
        "cert": {"职业资格", "教资", "四六级"},
    }
    targets = set(stage_map.get(stage, set()))
    # goal 里直接出现的考试名
    for exam in ("考研", "考公", "四六级", "高考", "中考", "教资", "职业资格"):
        if exam.lower() in goal:
            targets.add(exam)
    rec = [s for s in OFFICIAL_SOURCES if s["exam"] in targets]
    if not rec:
        rec = [s for s in OFFICIAL_SOURCES if s["exam"] == "综合"]
    return rec
