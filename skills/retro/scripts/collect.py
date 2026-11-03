#!/usr/bin/env python3
"""spec 실행 기록을 회고용으로 집계한다.

각 spec 폴더의 execution-history.json·analysis.json을 읽어 반복을 셀 수 있는 형태로 출력한다.
무엇이 같은 원인인지 묶는 일은 하지 않는다 — 문장 판단이라 메인 에이전트가 한다.

  collect.py --archive-root <SPEC_ROOT> [--last N]   # _archive/pr-<N>-<spec>/ 를 PR 번호 내림차순으로
  collect.py <spec-dir> [<spec-dir> ...]             # 폴더를 직접 지정
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def pr_number(d: Path) -> int:
    m = re.match(r"pr-(\d+)-", d.name)
    return int(m.group(1)) if m else -1


def summarize_history(history: dict, outcome_total: Counter) -> dict:
    steps_total = first_try = 0
    retried, stopped, review_retry, struggles, ac_failed = [], [], [], [], Counter()
    for ph in history.get("phases", []):
        phase = ph.get("phase")
        for s in ph.get("steps", []):
            steps_total += 1
            runs = s.get("runs", [])
            attempts = [a for r in runs for a in r.get("attempts", [])]
            outcomes = [a.get("outcome") for a in attempts]
            outcome_total.update(outcomes)
            if len(runs) == 1 and outcomes == ["approved"]:
                first_try += 1
            elif runs:
                retried.append({"phase": phase, "step": s.get("step"), "name": s.get("name"),
                                "runs": len(runs), "outcomes": outcomes})
            for r in runs:
                if r.get("status") in ("blocked", "error"):
                    stopped.append({"phase": phase, "step": s.get("step"),
                                    "status": r.get("status"), "reason": r.get("reason")})
            for a in attempts:
                if a.get("outcome") == "review_retry":
                    review_retry.append({"phase": phase, "step": s.get("step"),
                                         "attempt": a.get("attempt"), "detail": a.get("detail")})
                if a.get("struggles"):
                    struggles.append({"phase": phase, "step": s.get("step"),
                                      "attempt": a.get("attempt"), "text": a.get("struggles")})
            for at in s.get("ac_attempts", []):
                for f in at.get("failed", []):
                    ac_failed[f.get("command")] += 1
    return {
        "steps_total": steps_total,
        "steps_first_try": first_try,
        "retried_steps": retried,
        "stopped_runs": stopped,
        "review_retry": review_retry,
        "struggles": struggles,
        "ac_failed_commands": dict(ac_failed.most_common()),
    }


def summarize_analysis(analysis: dict, category_total: Counter, rejected_total: Counter) -> dict:
    by_inspector: dict[str, Counter] = {}
    rejected, disagreements, carried = [], [], []
    for f in analysis.get("findings", []):
        if not isinstance(f, dict):
            continue
        reported = f.get("reported_by") or []
        for r in reported:
            by_inspector.setdefault(r.get("inspector"), Counter())[r.get("severity")] += 1
        category_total[f.get("category")] += 1
        disp = f.get("disposition") or {}
        if disp.get("kind") == "rejected":
            rejected_total[f.get("category")] += 1
            rejected.append({"id": f.get("id"), "category": f.get("category"), "severity": f.get("severity"),
                             "inspectors": [r.get("inspector") for r in reported],
                             "summary": f.get("summary"), "reason": disp.get("reason")})
        if len({r.get("severity") for r in reported}) > 1:
            disagreements.append({"id": f.get("id"), "reported_by": reported})
        if f.get("carried_disposition"):
            carried.append({"id": f.get("id"), "carried": f.get("carried_disposition")})
    return {
        "findings_total": len(analysis.get("findings", [])),
        "by_inspector": {k: dict(v) for k, v in by_inspector.items()},
        "rejected": rejected,
        "disagreements": disagreements,
        "carried": carried,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="spec 실행 기록 회고 집계")
    ap.add_argument("spec_dirs", nargs="*")
    ap.add_argument("--archive-root", help="<SPEC_ROOT>. 그 아래 _archive/를 읽는다")
    ap.add_argument("--last", type=int, default=0, help="PR 번호가 큰 순으로 N개만")
    args = ap.parse_args()

    dirs = [Path(d).resolve() for d in args.spec_dirs]
    if args.archive_root:
        archive = Path(args.archive_root).resolve() / "_archive"
        found = sorted((d for d in archive.iterdir() if d.is_dir()), key=pr_number, reverse=True) \
            if archive.is_dir() else []
        dirs += found[:args.last] if args.last else found
    if not dirs:
        print(json.dumps({"ok": False, "error": "읽을 spec 폴더가 없다"}, ensure_ascii=False))
        return 1

    outcome_total, category_total, rejected_total = Counter(), Counter(), Counter()
    specs, missing = [], []
    for d in dirs:
        history = read_json(d / "execution-history.json")
        analysis = read_json(d / "analysis.json")
        entry = {"dir": str(d), "pr": pr_number(d) if pr_number(d) >= 0 else None}
        if history:
            entry["execution"] = summarize_history(history, outcome_total)
        if analysis:
            entry["analysis"] = summarize_analysis(analysis, category_total, rejected_total)
        if not history or not analysis:
            missing.append({"dir": str(d), "execution_history": bool(history), "analysis": bool(analysis)})
        specs.append(entry)

    print(json.dumps({
        "ok": True,
        "specs": specs,
        "totals": {
            "outcomes": dict(outcome_total.most_common()),
            "finding_categories": dict(category_total.most_common()),
            "rejected_categories": dict(rejected_total.most_common()),
        },
        "missing": missing,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
