#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""内置题库校验工具。

用法：
    python3 tools/validate_bank.py            # 校验 app/data_bank/ 下全部题库
    python3 tools/validate_bank.py --strict   # 把警告也视为失败

检查项：JSON 合法性、字段完整性、选项数量与前缀规范、答案与解析一致性、
id 唯一性、题干自洽（不依赖缺失的图表材料）、无占位符、题干去重、分布统计。
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK_DIR = ROOT / "app" / "data_bank"

REQ_FIELDS = ["id", "stage", "subject", "type", "knowledge", "question",
              "options", "answer", "explanation", "difficulty", "source"]
ANSWER_LETTERS = "ABCD"
OPTION_PREFIX = ["A. ", "B. ", "C. ", "D. "]
BAD_WORDS = ("TODO", "占位符", "此处略", "XXX", "xxx")
# 题干若引用外部图表却没有自带材料，视为残缺
MISSING_REF = re.compile(r"如图|见图|如下表所示|如右图|见下图|参考附图")
ELLIPSIS = re.compile(r"…|\.\.\.")


def validate(path: Path):
    errs, warns = [], []
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return [f"JSON 解析失败: {e}"], [], {}

    if not isinstance(data, list):
        return ["顶层不是数组"], [], {}

    ids, stems = set(), collections.Counter()
    by_stage, by_subject, by_type, by_diff, by_answer = (collections.Counter() for _ in range(5))

    for i, it in enumerate(data):
        tag = f"{path.name} #{i} {it.get('id', '?')}"
        if not isinstance(it, dict):
            errs.append(f"{tag} 不是对象")
            continue
        missing = set(REQ_FIELDS) - set(it)
        extra = set(it) - set(REQ_FIELDS)
        if missing:
            errs.append(f"{tag} 缺字段 {sorted(missing)}")
        if extra:
            warns.append(f"{tag} 多余字段 {sorted(extra)}")

        qid = it.get("id", "")
        if not qid:
            errs.append(f"{tag} id 为空")
        elif qid in ids:
            errs.append(f"{tag} id 重复")
        ids.add(qid)

        if not it.get("stage"):
            errs.append(f"{tag} stage 为空")
        if not it.get("subject"):
            errs.append(f"{tag} subject 为空")
        if it.get("difficulty") not in (1, 2, 3):
            errs.append(f"{tag} difficulty 应为 1/2/3，实际 {it.get('difficulty')!r}")
        if it.get("source") != "模拟原创题":
            warns.append(f"{tag} source 不是「模拟原创题」：{it.get('source')!r}")

        q = str(it.get("question", "")).strip()
        if len(q) < 8:
            errs.append(f"{tag} 题干过短")
        if MISSING_REF.search(q):
            errs.append(f"{tag} 题干依赖缺失的图表")
        # 引号内的省略号属于引用原文的截断（如「However, ... 」），不算内容缺失
        outside_quotes = re.sub(r"[「『\"“][^」』\"”]*[」』\"”]", "", q)
        if ELLIPSIS.search(outside_quotes):
            warns.append(f"{tag} 题干省略号在引文之外，可能内容不全")
        for w in BAD_WORDS:
            if w in q or w in str(it.get("explanation", "")):
                errs.append(f"{tag} 含占位词 {w}")
        stems[re.sub(r"\s+", "", q)] += 1

        opts = it.get("options")
        ans = str(it.get("answer", ""))
        if not isinstance(opts, list) or len(opts) != 4:
            errs.append(f"{tag} options 需为 4 项，实际 {opts if not isinstance(opts, list) else len(opts)}")
        else:
            texts = []
            for j, s in enumerate(opts):
                if not isinstance(s, str):
                    errs.append(f"{tag} options[{j}] 不是字符串")
                    continue
                if not s.startswith(OPTION_PREFIX[j]):
                    errs.append(f"{tag} options[{j}] 前缀应为 {OPTION_PREFIX[j]!r}：{s[:6]!r}")
                body = s[3:].strip()
                if not body:
                    errs.append(f"{tag} options[{j}] 内容为空")
                for w in BAD_WORDS:
                    if w in body:
                        errs.append(f"{tag} options[{j}] 含占位词 {w}")
                texts.append(body)
            if len(set(texts)) != len(texts):
                errs.append(f"{tag} 选项内容重复，答案可能不唯一")
            if ans in ANSWER_LETTERS and len(ans) == 1:
                idx = ANSWER_LETTERS.index(ans)
                if idx < len(opts) and not str(opts[idx]).startswith(OPTION_PREFIX[idx]):
                    errs.append(f"{tag} 答案 {ans} 与选项顺序不符")

        if ans not in ANSWER_LETTERS or len(ans) != 1:
            errs.append(f"{tag} answer 应为 A/B/C/D，实际 {ans!r}")

        expl = str(it.get("explanation", "")).strip()
        if len(expl) < 15:
            errs.append(f"{tag} 解析过短")
        tail = re.findall(r"故选([A-D])", expl)
        if tail and tail[-1] != ans:
            errs.append(f"{tag} 解析结论「故选{tail[-1]}」与 answer={ans} 矛盾")

        by_stage[it.get("stage", "?")] += 1
        by_subject[f"{it.get('stage', '?')}/{it.get('subject', '?')}"] += 1
        by_type[it.get("type", "?")] += 1
        by_diff[it.get("difficulty")] += 1
        by_answer[ans] += 1

    for stem, c in stems.items():
        if c > 1:
            errs.append(f"{path.name} 题干重复 {c} 次：{stem[:24]}…")

    stats = {
        "count": len(data),
        "size": len(raw.encode()),
        "stage": dict(by_stage),
        "subject": dict(by_subject),
        "type": dict(by_type),
        "difficulty": dict(by_diff),
        "answer": dict(by_answer),
    }
    return errs, warns, stats


def main():
    ap = argparse.ArgumentParser(description="校验内置题库")
    ap.add_argument("--strict", action="store_true", help="警告也视为失败")
    ap.add_argument("files", nargs="*", help="指定文件，默认扫描 app/data_bank/*.json")
    args = ap.parse_args()

    files = [Path(f) for f in args.files] if args.files else sorted(BANK_DIR.glob("*.json"))
    if not files:
        print(f"没找到题库文件：{BANK_DIR}", file=sys.stderr)
        return 2

    total_errs = total_warns = total_count = 0
    for f in files:
        if not f.exists():
            print(f"✗ 文件不存在：{f}")
            total_errs += 1
            continue
        errs, warns, stats = validate(f)
        total_errs += len(errs)
        total_warns += len(warns)
        total_count += stats.get("count", 0)
        status = "PASS" if not errs else "FAIL"
        print(f"=== {f.name}  {stats.get('count', 0)} 题  {stats.get('size', 0)} bytes  [{status}]")
        if stats:
            print(f"    stage     : {stats['stage']}")
            print(f"    difficulty: {stats['difficulty']}")
            print(f"    answer    : {stats['answer']}")
        for e in errs[:20]:
            print(f"    [ERR]  {e}")
        if len(errs) > 20:
            print(f"    [ERR]  …另有 {len(errs) - 20} 条")
        for w in warns[:10]:
            print(f"    [WARN] {w}")
        if len(warns) > 10:
            print(f"    [WARN] …另有 {len(warns) - 10} 条")

    print(f"\n合计 {total_count} 题 | errors {total_errs} | warnings {total_warns}")
    failed = total_errs > 0 or (args.strict and total_warns > 0)
    print("RESULT:", "FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
