#!/usr/bin/env python3
from __future__ import annotations

"""spec-harness execute.py — 서브커맨드 모음 (오케스트레이터가 아님).

이 스크립트의 서브커맨드들은 workflow(JS)가 직접 못 하는 shell/git/fs 작업을 대신 수행한다. 오케스트레이션 자체는
JavaScript workflow(spec-harness:execute)로 옮겨갔고, execute.py는 **workflow 스크립트(JS)가
직접 못 하는 일(파일시스템·shell 접근)을 agent가 CLI로 호출할 수 있게 노출한 입구 모음**이 된다.

서브커맨드:
  preflight       phase index.json을 읽어 {steps, execution}을 workflow args(JSON)로 stdout 출력
  build-context   현재 step의 developer 컨텍스트(CLAUDE.md·spec문서·규칙문서·이전step summary)를 조립해 출력
  verify-ac       step의 Acceptance Criteria를 실행·판정(acceptance_check) → ac-output.json 누적 + 결과 JSON 출력
  record-step     phase index.json에 step.status/summary/completed_at과 시도 이력(runs) 기록 (recorder agent 전용)
  reset-step      blocked/error step을 pending으로 되돌림 (사람이 원인을 고친 뒤 재개용)
  init-checklist  stages.json의 단계 정의로 spec 레벨 checklist 생성 (Specify에서 한 번)
  set-stage       spec 레벨 checklist의 Stage 8/9/10 상태 갱신 (메인의 Execution 자동 흐름 + PR Review/Root Sync — preflight·finalize는 안 건드림)
  finalize        phase 닫기: 이 phase의 completed_at·spec index 동기화(워킹트리) + 선택적 push (finalizer agent 전용)
  export-history  phase index·ac-output의 실행 이력을 execution-history.json으로 모음 (Root Sync에서 _archive로 옮기기 전)
  lint-steps      step 문서의 Acceptance Criteria 파싱 계약 검사 (실행하지 않고 형식만)
  close-analyze   analysis.json의 CRITICAL 처리·step 형식을 확인하고 Analyze(7)를 닫음 + fingerprint 기록
  start-review    검사관을 띄우기 직전에 검사 대상 문서의 지문을 고정
  close-review    stages.json에 정의된 검사 단계를 확인하고 닫음 + fingerprint 기록
  freeze          기능 spec 동결 조건 확인, --tag면 버전 태그 생성
  import-feature  docs 저장소의 동결 태그에서 기능 spec을 upstream/으로 가져옴 (implement)
  set-docs-repo   docs 저장소의 로컬 경로를 메인 체크아웃의 .spec-harness/local.json에 기록 (implement)

설계 원칙:
  - 함수 기반: 셔틀 상태가 없고 각 서브커맨드가 한 번 실행되고 끝이므로 클래스가 불필요.
  - 각 서브커맨드는 결과를 stdout에 JSON으로 출력한다(agent가 그 JSON을 받아 workflow에 반환).
  - 무거운 로직은 모듈(acceptance_check/step_context/git_ops)에 있고, 여기선 입구만 얇게.
"""

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import acceptance_check
import git_ops
import instance_config
import step_context


# ─────────────────────────────────────────────────────────────────────────────
# 공통 헬퍼
# ─────────────────────────────────────────────────────────────────────────────
def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


_KST = timezone(timedelta(hours=9))


def stamp() -> str:
    return datetime.now(_KST).isoformat()


def emit(payload: dict) -> None:
    """결과를 stdout에 JSON 한 줄로 출력한다(agent가 파싱해 workflow에 반환)."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.write("\n")
    sys.stdout.flush()


# 단계 목록의 정본. checklist의 `workflow` 값으로 고른다.
# 플러그인만 이 정의를 가진다 — 저장소가 단계를 빼서 게이트를 여는 길을 막는다.
STAGES_PATH = SCRIPT_DIR.parent / "stages.json"


def load_stage_set(name) -> dict | None:
    """workflow 이름의 단계 정의. 없는 이름이면 None.

    stages: 순서대로의 단계 / execution: 실행 게이트 단계 / set_stage: `set-stage`로 갱신할 수 있는 단계
    reviews: 검사 단계별 결과 파일·판정 대상 문서(`/`로 시작하면 저장소 루트 기준)·앞 검사 이후 바뀌면 안 되는 문서
    frozen_docs: 동결 대상 문서. 바뀌면 major 버전이어야 한다
    """
    if not isinstance(name, str):
        return None
    found = read_json(STAGES_PATH).get(name)
    return found if isinstance(found, dict) else None


def validate_workflow_checklist(checklist_dir: Path) -> dict:
    """실행 전 게이트: 실행 단계 앞의 모든 단계가 completed이고 실행 단계가 pending/in_progress여야 통과한다.

    checklist는 spec 레벨에 하나다(`<spec>/workflow-checklist.json`).
    통과하면 {"ok": True}, 아니면 {"ok": False, "error": ...}를 반환한다.

    참고: "Clarify 위험마커 0 + Analyze 통과"라는 의미 게이트는 별도 코드 검사가 아니라,
    그 단계를 completed로 표시하는 행위가 조건의 충족을 뜻한다는 규약으로 강제한다
    (마커가 남았으면 Clarify를 completed로 두지 않고, Analyze가 실패하면 Analyze를 completed로 두지 않는다).
    """
    checklist_path = checklist_dir / "workflow-checklist.json"
    if not checklist_path.exists():
        return {"ok": False, "error": f"workflow-checklist.json 없음: {checklist_path}. "
                "실행 단계 앞의 단계를 마치고 실행 승인을 기록한 checklist를 만든 뒤 실행하라."}

    checklist = read_json(checklist_path)
    name = checklist.get("workflow")
    stage_set = load_stage_set(name)
    if stage_set is None:
        return {"ok": False, "error": f"workflow-checklist.json의 workflow '{name}'는 정의되지 않았다(stages.json)."}
    expected = list(enumerate((s["title"] for s in stage_set["stages"]), start=1))
    exec_title = stage_set.get("execution")
    if not exec_title:
        return {"ok": False, "error": f"'{name}' workflow에는 실행 단계가 없다."}
    exec_order = next(o for o, t in expected if t == exec_title)

    items = checklist.get("items")
    if not isinstance(items, list) or len(items) != len(expected):
        return {"ok": False, "error": f"workflow-checklist.json은 {len(expected)}개 {name} workflow 항목을 가져야 한다."}

    invalid, incomplete = [], []
    for idx, (order, title) in enumerate(expected):
        item = items[idx] if idx < len(items) else {}
        if not isinstance(item, dict) or item.get("order") != order or item.get("title") != title:
            invalid.append(f"{order}. {title}")
            continue
        status = item.get("status")
        if order < exec_order and status != "completed":
            incomplete.append(title)
        if order == exec_order and status not in {"pending", "in_progress"}:
            invalid.append(f"{order}. {title} status must be pending or in_progress")

    if invalid:
        return {"ok": False, "error": "workflow-checklist.json 항목이 올바르지 않다.", "invalid": invalid}
    observed = {it.get("order") for it in items if isinstance(it, dict)}
    if {o for o, _ in expected} != observed:
        return {"ok": False, "error": "workflow-checklist.json에 누락/중복된 order가 있다."}
    if incomplete:
        return {"ok": False, "error": f"{name} workflow가 실행 승인되지 않았다({exec_title} 직전 단계 미완).", "incomplete": incomplete}
    return {"ok": True}


def update_workflow_item(checklist_dir: Path, title: str, status: str) -> bool:
    """workflow-checklist.json의 단일 항목 상태를 갱신한다. 파일/항목 없으면 False.

    누가 어느 Stage를 갱신하는지는 cmd_set_stage를 본다.
    """
    checklist_path = checklist_dir / "workflow-checklist.json"
    if not checklist_path.exists():
        return False
    checklist = read_json(checklist_path)
    ts = stamp()
    matched = False
    for item in checklist.get("items", []):
        if item.get("title") == title:
            item["status"] = status
            if status == "completed":
                item["completed_at"] = ts
            elif status == "in_progress":
                item.setdefault("started_at", ts)
                item.pop("completed_at", None)
            matched = True
            break
    write_json(checklist_path, checklist)
    return matched


def analysis_review(spec_dir: Path) -> tuple[dict, dict]:
    """(단계 정의, Analyze 검사 정의). checklist의 workflow를 따르고, 없으면 run의 것이다."""
    checklist = spec_dir / "workflow-checklist.json"
    stage_set = load_stage_set(read_json(checklist).get("workflow")) if checklist.exists() else None
    if not stage_set or "Analyze" not in stage_set.get("reviews", {}):
        stage_set = load_stage_set("harness")
    return stage_set, stage_set["reviews"]["Analyze"]


def analyzed_fingerprint(spec_dir: Path) -> dict:
    """Analyze가 본 문서들의 내용 해시(판정 대상은 stages.json). 닫은 뒤 문서가 바뀌면 그 분석은 낡은 것이다."""
    return doc_fingerprint(spec_dir, git_toplevel(spec_dir) or spec_dir, analysis_review(spec_dir)[1]["docs"])


def lint_step_docs(spec_dir: Path) -> list[dict]:
    """step 문서가 AC 파싱 계약을 지키는지 본다. 명령을 실행하지는 않는다.

    여기서 걸러내지 못하면 Execution에서 step마다 같은 실패를 반복한다.
    """
    problems: list[dict] = []
    steps = sorted((spec_dir / "phases").glob("*/step*.md"))
    if not steps:
        return [{"step": "(없음)", "problems": ["step 문서를 하나도 찾지 못했다"]}]

    for path in steps:
        text = path.read_text(encoding="utf-8")
        found: list[str] = []
        if not re.search(r"^## Acceptance Criteria\s*$", text, re.MULTILINE):
            found.append("`## Acceptance Criteria` 헤더가 없다 — 이 문자열이 정확해야 AC가 파싱된다")
        elif not acceptance_check.extract_acceptance_commands(text):
            found.append("Acceptance Criteria 안에 실행할 명령이 없다 — ```bash 블록을 찾지 못했다")
        for line in acceptance_check.malformed_expect_lines(text):
            found.append(f"`expect:` 값이 정수가 아니라 무시된다: {line}")
        if not re.search(r"^## 검증 대상\s*$", text, re.MULTILINE):
            found.append("`## 검증 대상` 절이 없다 — 이 step이 무엇을 확인하는지 대조할 근거가 없다")
        if found:
            problems.append({"step": path.relative_to(spec_dir).as_posix(), "problems": found})
    return problems


def resolve_paths(phase_dir_arg: str) -> dict:
    """phase 디렉터리 경로로부터 자주 쓰는 경로들을 계산한다.

    레이아웃: <spec 루트>/<spec>/phases/<phase>/  (spec 루트 위치는 저장소 설정이 정한다)
      phase_dir            = .../phases/<phase>
      phase index.json     = phase_dir/index.json
      spec phases dir      = .../phases
      spec phases index    = .../phases/index.json
      spec dir            = .../<spec>   (spec 문서 spec/architecture/... 위치)
      root                 = git worktree 루트 (cwd 기준)
    """
    phase_dir = Path(phase_dir_arg).resolve()
    spec_phases_dir = phase_dir.parent           # .../phases
    spec_dir = spec_phases_dir.parent            # .../<spec>
    # root: cwd의 git 최상위 (worktree 루트). 실패 시 cwd.
    top = git_ops.run_git(str(Path.cwd()), "rev-parse", "--show-toplevel")
    root = top.stdout.strip() if top.returncode == 0 and top.stdout.strip() else str(Path.cwd())
    root_path = Path(root)
    return {
        "phase_dir": phase_dir,
        "phase_index": phase_dir / "index.json",
        "spec_phases_dir": spec_phases_dir,
        "spec_index": spec_phases_dir / "index.json",
        "spec_dir": spec_dir,
        "root": root,
        "root_path": root_path,
        "phase_name": phase_dir.name,
        "phase_relpath": phase_dir.relative_to(root_path).as_posix() if str(phase_dir).startswith(root) else str(phase_dir),
        "spec_phases_relpath": spec_phases_dir.relative_to(root_path).as_posix() if str(spec_phases_dir).startswith(root) else str(spec_phases_dir),
    }


def step_file_path(phase_dir: Path, n: int) -> Path:
    return phase_dir / f"step{n}.md"


# ─────────────────────────────────────────────────────────────────────────────
# preflight — index.json → workflow args
# ─────────────────────────────────────────────────────────────────────────────
def stale_analysis(p: dict) -> dict | None:
    """Analyze를 닫은 뒤 문서가 바뀌었으면 그 사실을 낸다. 문제가 없으면 None.

    첫 진입(모든 phase가 pending)일 때만 본다. 실행이 시작된 뒤에는 설계 문서를 as-built로
    갱신하므로 달라지는 것이 정상이고, phase가 여러 개면 두 번째 preflight가 잘못 막힌다.
    """
    if p["spec_index"].exists():
        phases = read_json(p["spec_index"]).get("phases", [])
        if any(ph.get("status") not in (None, "pending") for ph in phases if isinstance(ph, dict)):
            return None

    analysis_path = p["spec_dir"] / "analysis.json"
    if not analysis_path.exists():
        return {"ok": False, "error": f"analysis.json이 없다: {analysis_path}. "
                "Analyze(7)를 `close-analyze`로 닫은 뒤 실행하라."}
    recorded = read_json(analysis_path).get("fingerprint")
    if not isinstance(recorded, dict) or not recorded:
        return {"ok": False, "error": "analysis.json에 fingerprint가 없다. "
                "`close-analyze`로 Analyze를 닫아야 기록된다."}

    current = analyzed_fingerprint(p["spec_dir"])
    changed = sorted(
        (set(recorded) ^ set(current))
        | {k for k in set(recorded) & set(current) if recorded[k] != current[k]}
    )
    if changed:
        return {"ok": False, "error": "Analyze를 닫은 뒤 문서가 바뀌어 그 분석은 낡았다. "
                "다시 분석하고 `close-analyze`로 닫아라.", "changed": changed}
    return None


def cmd_preflight(args) -> int:
    """phase index.json을 읽어 workflow에 넘길 args(steps + execution)를 stdout JSON으로 출력.

    workflow(JS)는 파일을 못 읽으므로, 세션이 이 출력을 받아 /spec-harness:execute <args>로 넘긴다.
    """
    p = resolve_paths(args.phase_dir)
    if not p["phase_index"].exists():
        emit({"ok": False, "error": f"phase index 없음: {p['phase_index']}"})
        return 1
    index = read_json(p["phase_index"])

    # phase가 현재 작업 트리 밖이면 거부한다. 그대로 두면 구현·검증·커밋이 의도하지 않은 트리에서 일어난다.
    if not str(p["phase_dir"]).startswith(p["root"]):
        emit({"ok": False, "error": f"phase 디렉터리가 현재 작업 트리 밖이다. "
              f"phase_dir={p['phase_dir']} / 작업 트리={p['root']}. 의도한 worktree 안에서 실행하라."})
        return 1

    # 실행 전 게이트: Execution 직전 단계(1~7) 완료 + 실행 승인을 강제한다. 통과 못하면 여기서 멈춘다.
    gate = validate_workflow_checklist(p["spec_dir"])
    if not gate["ok"]:
        emit(gate)
        return 1

    # checklist의 Execution(8)은 여기서 갱신하지 않는다 — spec 레벨이라 phase마다 도는 preflight가
    # 건드리면 phase가 여러 개일 때 어긋난다.

    stale = stale_analysis(p)
    if stale:
        emit(stale)
        return 1

    bad = upstream_problem(p["spec_dir"])
    blocked, upstream_notes = upstream_freshness(p["spec_dir"], p["root_path"])
    if bad or blocked:
        emit(bad or blocked)
        return 1

    # finalize가 origin으로 push한다. 없으면 모든 step을 끝낸 뒤에야 실패한다.
    if index.get("execution", {}).get("push", True) and git_ops.run_git(p["root"], "remote", "get-url", "origin").returncode != 0:
        emit({"ok": False, "error": "원격 origin이 없는데 phase index의 execution.push가 true다. "
              "원격을 연결하거나 execution.push를 false로 둔다."})
        return 1

    # hook이 phase별 로그 디렉터리(<phase>/logs)를 찾도록 active-phase 마커를 남긴다.
    # (preflight가 이 마커를 쓰고, hook이 읽는다.)
    try:
        marker_dir = p["root_path"] / instance_config.RUNTIME_RELPATH
        marker_dir.mkdir(parents=True, exist_ok=True)
        (marker_dir / "active-phase").write_text(p["phase_relpath"], encoding="utf-8")
        # 남은 logstate가 있으면 그 agent의 로그가 조용히 비어 버린다.
        for stale in marker_dir.glob("logstate-*.json"):
            stale.unlink(missing_ok=True)
    except OSError:
        pass  # 마커 실패는 치명적이지 않다(로그가 fallback 위치로 갈 뿐)

    steps = [
        {"step": s["step"], "name": s.get("name", ""), "status": s.get("status", "pending")}
        for s in index.get("steps", [])
    ]
    execution = index.get("execution", {})


    emit({
        "ok": True,
        "execute": str(Path(__file__).resolve()),
        "phase_dir": str(p["phase_dir"]),
        "phase_relpath": p["phase_relpath"],
        "phase": index.get("phase", p["phase_name"]),
        "steps": steps,
        "execution": {
            "developer_model": execution.get("developer_model", "sonnet"),
            "reviewer_model": execution.get("reviewer_model", "opus"),
            "committer_model": execution.get("committer_model", "haiku"),
            "push": execution.get("push", True),
        },
        **({"upstream_notes": upstream_notes} if upstream_notes else {}),
    })
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# build-context — developer 컨텍스트 조립
# ─────────────────────────────────────────────────────────────────────────────
def cmd_build_context(args) -> int:
    """현재 step의 developer 컨텍스트를 조립해 출력한다.

    이전 step summary는 실행 중에 생기므로(preflight 시점엔 없음) developer 턴에 호출한다.
    """
    p = resolve_paths(args.phase_dir)
    n = args.step
    sf = step_file_path(p["phase_dir"], n)
    if not sf.exists():
        emit({"ok": False, "error": f"step 문서 없음: {sf}"})
        return 1
    step_text = sf.read_text(encoding="utf-8")

    # 정적 컨텍스트(CLAUDE.md·spec문서·컨벤션요약·step이 참조한 문서)
    doc_context = step_context.load_step_documents(p["root_path"], p["spec_dir"], step_text)

    # 이전 완료 step들의 summary (phase index에서)
    prev = ""
    if p["phase_index"].exists():
        index = read_json(p["phase_index"])
        prev = step_context.build_previous_step_context(index)

    emit({
        "ok": True,
        "step": n,
        "context": doc_context,
        "previous_steps": prev,
        "step_text": step_text,
    })
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# verify-ac — Acceptance Criteria 실행·판정
# ─────────────────────────────────────────────────────────────────────────────
def cmd_verify_ac(args) -> int:
    """step의 AC를 실행·판정(acceptance_check)하고 ac-output.json에 누적. 결과 JSON 출력.

    developer agent가 구현 끝에 호출한다. AC가 없으면 passed=true(검사할 게 없음).
    """
    p = resolve_paths(args.phase_dir)
    n = args.step
    sf = step_file_path(p["phase_dir"], n)
    if not sf.exists():
        emit({"ok": False, "error": f"step 문서 없음: {sf}"})
        return 1
    step_text = sf.read_text(encoding="utf-8")

    result = acceptance_check.check(
        root=p["root"],
        phase_dir=p["phase_dir"],
        write_json=write_json,
        step={"step": n},
        step_text=step_text,
        attempt=args.attempt,
    )
    if result is None:
        # 못 뽑은 것을 통과로 처리하면 헤더 오타 하나로 검증이 사라진다.
        emit({
            "ok": False,
            "step": n,
            "error": "AC 명령을 하나도 뽑지 못했다. 검증 없이 통과시키지 않는다.",
            "hint": "step 문서에 `## Acceptance Criteria` 헤더(정확히 이 문자열)와 ```bash 또는 ```sh "
                    "코드블록이 있는지 확인하라. 정말 검증할 것이 없는 step이면 명령을 한 줄 명시하라.",
        })
        return 1

    emit({
        "ok": True,
        "step": n,
        "attempt": args.attempt,
        "passed": result["passed"],
        "results": result["results"],
    })
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# record-step — phase index.json에 step 완료 기록 (recorder 전용)
# ─────────────────────────────────────────────────────────────────────────────
def cmd_record_step(args) -> int:
    """phase index.json의 step status/summary/completed_at을 기록한다.

    recorder agent가 step 완료 시 호출한다. 매 step 영속 기록이라 재실행 시
    완료된 step을 건너뛸 수 있다(JS 변수/런타임 저널은 실행 경계를 못 넘으므로 필요).
    """
    p = resolve_paths(args.phase_dir)
    if not p["phase_index"].exists():
        emit({"ok": False, "error": f"phase index 없음: {p['phase_index']}"})
        return 1
    index = read_json(p["phase_index"])

    target = next((s for s in index.get("steps", []) if s.get("step") == args.step), None)
    if target is None:
        emit({"ok": False, "error": f"step {args.step} not found in index"})
        return 1

    target["status"] = args.status
    if args.summary:
        target["summary"] = args.summary
    ts = stamp()

    # 실행 한 번 = run 한 칸. reset-step 뒤 재실행하면 칸이 늘어 중단 이력이 남는다.
    # 이력은 회고 재료라 깨져도 상태 기록은 막지 않는다.
    attempts_warning = None
    if args.status in ("completed", "blocked", "error"):
        attempts = []
        if args.attempts:
            try:
                parsed = json.loads(args.attempts)
                if isinstance(parsed, list):
                    attempts = parsed
                else:
                    attempts_warning = "attempts가 목록이 아니라 비워 기록했다"
            except json.JSONDecodeError as e:
                attempts_warning = f"attempts JSON 파싱 실패로 비워 기록했다: {e}"
        run = {"status": args.status, "recorded_at": ts, "attempts": attempts}
        if args.status != "completed" and args.reason:
            run["reason"] = args.reason
        if attempts_warning:
            run["attempts_error"] = attempts_warning
        target.setdefault("runs", []).append(run)
    if args.status == "completed":
        target["completed_at"] = ts
        for stale in ("error_message", "blocked_reason"):
            target.pop(stale, None)
    elif args.status == "blocked":
        target["blocked_at"] = ts
        if args.reason:
            target["blocked_reason"] = args.reason
    elif args.status == "error":
        target["failed_at"] = ts
        if args.reason:
            target["error_message"] = args.reason

    write_json(p["phase_index"], index)
    result = {"ok": True, "step": args.step, "status": args.status}
    if attempts_warning:
        result["warning"] = attempts_warning
    emit(result)
    return 0


def cmd_reset_step(args) -> int:
    """blocked/error로 멈춘 step을 pending으로 되돌린다(사람이 원인을 고친 뒤 호출).

    재시도/재개의 명시적 신호다. blocked/error 관련 잔여 필드를 모두 제거해 정본을
    깨끗한 pending 상태로 만든다. 이렇게 해야 workflow 재실행 시 그 step이 다시 잡힌다.
    (status를 바꾸지 않은 채 재실행하면 workflow가 자동 재개하지 않으므로, 안 고친 채
    같은 실패를 반복하며 토큰을 낭비하는 일이 없다.)
    """
    p = resolve_paths(args.phase_dir)
    if not p["phase_index"].exists():
        emit({"ok": False, "error": f"phase index 없음: {p['phase_index']}"})
        return 1
    index = read_json(p["phase_index"])

    target = next((s for s in index.get("steps", []) if s.get("step") == args.step), None)
    if target is None:
        emit({"ok": False, "error": f"step {args.step} not found in index"})
        return 1

    prev = target.get("status", "pending")
    target["status"] = "pending"
    for stale in ("summary", "error_message", "blocked_reason",
                  "completed_at", "failed_at", "blocked_at"):
        target.pop(stale, None)

    write_json(p["phase_index"], index)
    emit({"ok": True, "step": args.step, "status": "pending", "previous_status": prev})
    return 0


def cmd_init_checklist(args) -> int:
    """spec 레벨 checklist를 stages.json의 단계 정의로 만든다. 이미 있으면 그대로 두고, --reset이면 끝난 checklist를 새로 만든다."""
    spec_dir = Path(args.spec_dir).resolve()
    path = spec_dir / "workflow-checklist.json"
    if path.exists() and not args.reset:
        emit({"ok": True, "path": str(path), "created": False})
        return 0
    if path.exists():
        # 끝난 작업의 진행 상태만 지운다. 진행 중인 작업을 날리지 않는다.
        old = read_json(path)
        unfinished = [it.get("title") for it in old.get("items", []) if it.get("status") != "completed"]
        if unfinished:
            emit({"ok": False, "error": "끝나지 않은 작업의 checklist라 초기화하지 않는다.", "incomplete": unfinished})
            return 1
    stage_set = load_stage_set(args.workflow)
    if stage_set is None:
        emit({"ok": False, "error": f"workflow '{args.workflow}'는 정의되지 않았다(stages.json)."})
        return 1
    items = [
        {"order": i, "group": s.get("group", ""), "title": s["title"], "status": "pending"}
        for i, s in enumerate(stage_set["stages"], start=1)
    ]
    spec_dir.mkdir(parents=True, exist_ok=True)
    write_json(path, {"workflow": args.workflow, "status": "drafting", "items": items})
    notes = instance_config.load_config(git_toplevel(spec_dir) or Path.cwd())["_notes"]
    emit({"ok": True, "path": str(path), "created": True, "stages": len(items),
          **({"config_notes": notes} if notes else {})})
    return 0


def cmd_set_stage(args) -> int:
    """spec 레벨 checklist의 한 Stage 상태를 갱신한다.

    checklist는 spec 레벨 하나이고 Stage 8/9/10은 spec 전체의 진행이므로, phase 단위로 도는
    preflight·finalize가 아니라 이 명령으로 spec 단위에 한 번씩 갱신한다.
      - Stage 8(Execution): 메인이 자동 흐름에서 호출한다 — 진입 시 in_progress, phase 루프를 다 돈 뒤 completed.
          set-stage <spec> Execution in_progress
          set-stage <spec> Execution completed
      - Stage 9/10(PR Review/Root Sync): 리뷰·승격 등 사람 판단 시점에 같은 방식으로 갱신한다.
    """
    checklist_dir = Path(args.checklist_dir).resolve()
    not_found = {"ok": False, "error": f"checklist에서 '{args.stage}' 항목을 찾지 못했다(경로: {checklist_dir}). "
                 "checklist_dir는 spec 디렉터리(workflow-checklist.json이 있는 spec 루트)여야 하고 stage는 정확한 Stage 제목이어야 한다."}
    checklist_path = checklist_dir / "workflow-checklist.json"
    if not checklist_path.exists():
        emit(not_found)
        return 1
    name = read_json(checklist_path).get("workflow")
    stage_set = load_stage_set(name)
    if stage_set is None:
        emit({"ok": False, "error": f"workflow-checklist.json의 workflow '{name}'는 정의되지 않았다(stages.json)."})
        return 1
    # 실행 단계 앞을 이 명령으로 찍으면 그 앞 게이트가 근거 없이 열린다.
    allowed = set(stage_set.get("set_stage", []))
    if args.stage not in allowed:
        emit({"ok": False, "error": f"set-stage로 갱신할 수 있는 Stage는 {sorted(allowed)}뿐이다. "
              f"'{args.stage}'는 진행하며 작성·갱신하는 단계다."})
        return 1
    if not update_workflow_item(checklist_dir, args.stage, args.status):
        emit(not_found)
        return 1
    emit({"ok": True, "stage": args.stage, "status": args.status})
    return 0


def cmd_finalize(args) -> int:
    """phase 닫기: 이 phase의 completed_at 기록·spec index 동기화(워킹트리) + 선택적 push.

    finalizer agent가 phase 끝에 호출한다 — workflow 한 번 기동 = phase 하나 완주.
    진행 상태 파일(phase index 포함)은 .gitignore 대상이라 커밋하지 않는다 — 여기서는
    워킹트리 상태만 갱신하고, committer가 만든 코드 커밋을 원격으로 push한다.

    checklist의 Execution(Stage 8) 상태는 건드리지 않는다. checklist는 spec 레벨 하나이고
    Stage 진행은 spec 전체의 것이므로, phase 하나가 끝났다고 Execution(8)을 completed로 만들면 안 된다
    (다른 phase가 남아 있을 수 있다). Execution completed는 모든 phase를 마친 뒤 메인이 자동 흐름에서 set-stage로 찍는다.
    push 의도는 index.execution.push에서 읽는다(인자 --no-push로도 강제 비활성 가능).
    """
    p = resolve_paths(args.phase_dir)
    root = p["root"]
    index = read_json(p["phase_index"]) if p["phase_index"].exists() else {}

    # 이 phase의 completed_at 기록 (워킹트리 상태 — 커밋하지 않음)
    index["completed_at"] = stamp()
    write_json(p["phase_index"], index)

    # spec index의 이 phase status=completed 동기화 (워킹트리 상태)
    _update_spec_index(p, "completed")

    # push 의도: index.execution.push AND not --no-push
    recorded_push = index.get("execution", {}).get("push", True)
    auto_push = bool(recorded_push) and (not args.no_push)

    # 선택적 push (committer가 만든 코드 커밋을 원격으로 올린다)
    pushed = False
    branch = ""
    if auto_push:
        b = git_ops.run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
        branch = b.stdout.strip()
        if not branch:
            emit({"ok": False, "error": "push할 브랜치명을 확인할 수 없습니다(빈 refspec 방지)."})
            return 1
        r = git_ops.run_git(root, "push", "-u", "origin", branch)
        if r.returncode != 0:
            emit({"ok": False, "error": f"git push 실패: {r.stderr.strip()}"})
            return 1
        pushed = True

    emit({
        "ok": True,
        "phase": p["phase_name"],
        "pushed": pushed,
        "branch": branch,
        "push_skipped": (not auto_push),
    })
    return 0


def _update_spec_index(p: dict, status: str) -> None:
    """spec phases index.json의 현재 phase status를 동기화한다(존재할 때만)."""
    if not p["spec_index"].exists():
        return
    spec_data = read_json(p["spec_index"])
    ts = stamp()
    key = {"completed": "completed_at", "error": "failed_at", "blocked": "blocked_at"}.get(status)
    for phase in spec_data.get("phases", []):
        if phase.get("phase") == p["phase_name"]:
            phase["status"] = status
            for stale in ("completed_at", "failed_at", "blocked_at"):
                if stale != key:
                    phase.pop(stale, None)
            if key:
                phase[key] = ts
            break
    write_json(p["spec_index"], spec_data)


# ─────────────────────────────────────────────────────────────────────────────
# lint-steps · close-analyze — Analyze(7) 게이트
# ─────────────────────────────────────────────────────────────────────────────
def _ac_attempts(ac_path: Path) -> list:
    """ac-output.json을 시도별 통과 여부와 실패 명령만으로 줄인다."""
    if not ac_path.exists():
        return []
    try:
        data = read_json(ac_path)
    except (json.JSONDecodeError, OSError):
        return [{"error": f"{ac_path.name}을 읽지 못했다"}]
    out = []
    for at in data.get("attempts", []) if isinstance(data, dict) else []:
        if not isinstance(at, dict):
            continue
        failed = [
            {k: r.get(k) for k in ("command", "expectExit", "actualExit")}
            for r in at.get("results", []) if isinstance(r, dict) and not r.get("ok")
        ]
        out.append({"attempt": at.get("attempt"), "passed": at.get("passed"), "failed": failed})
    return out


def cmd_export_history(args) -> int:
    """실행 이력을 `<spec>/execution-history.json`으로 모은다.

    phase index와 ac-output은 진행 상태·실행 부산물이라 추적되지 않아 작업 폴더와 함께 사라진다.
    Root Sync가 `_archive`로 옮기기 전에 이 파일을 만들어 함께 커밋해야 회고가 나중에 읽을 수 있다.
    """
    spec_dir = Path(args.spec_dir).resolve()
    phases_dir = spec_dir / "phases"
    if not phases_dir.is_dir():
        emit({"ok": False, "error": f"phases 디렉터리가 없다: {phases_dir}"})
        return 1

    phase_names = []
    spec_index = phases_dir / "index.json"
    if spec_index.exists():
        phase_names = [ph.get("phase") for ph in read_json(spec_index).get("phases", []) if ph.get("phase")]
    if not phase_names:
        phase_names = sorted(d.name for d in phases_dir.iterdir() if (d / "index.json").exists())

    phases, steps_total = [], 0
    for name in phase_names:
        phase_index = phases_dir / name / "index.json"
        if not phase_index.exists():
            phases.append({"phase": name, "error": "phase index 없음"})
            continue
        index = read_json(phase_index)
        steps = []
        for s in index.get("steps", []):
            n = s.get("step")
            steps.append({
                "step": n,
                "name": s.get("name"),
                "status": s.get("status"),
                "summary": s.get("summary"),
                "runs": s.get("runs", []),
                "ac_attempts": _ac_attempts(phases_dir / name / f"step{n}-ac-output.json"),
            })
        steps_total += len(steps)
        phases.append({
            "phase": name,
            "completed_at": index.get("completed_at"),
            "execution": index.get("execution", {}),
            "steps": steps,
        })

    out_path = spec_dir / "execution-history.json"
    write_json(out_path, {"spec": spec_dir.name, "exported_at": stamp(), "phases": phases})
    emit({"ok": True, "path": str(out_path), "phases": len(phases), "steps": steps_total})
    return 0


def cmd_lint_steps(args) -> int:
    """step 문서의 AC 파싱 계약을 실행 없이 검사한다."""
    spec_dir = Path(args.spec_dir).resolve()
    problems = lint_step_docs(spec_dir)
    if problems:
        emit({"ok": False, "error": "step 문서 형식이 어긋나 Execution에서 AC가 파싱되지 않는다.",
              "problems": problems})
        return 1
    emit({"ok": True, "steps": len(sorted((spec_dir / "phases").glob("*/step*.md")))})
    return 0


def unresolved_critical(findings: list) -> list[dict]:
    """근거를 적은 반려가 아닌 CRITICAL. `fixed`는 의사일 뿐이라 해소로 치지 않는다."""
    unresolved = []
    for finding in findings:
        if not isinstance(finding, dict) or finding.get("severity") != "CRITICAL":
            continue
        disposition = finding.get("disposition")
        kind = disposition.get("kind") if isinstance(disposition, dict) else None
        reason = str(disposition.get("reason") or "").strip() if isinstance(disposition, dict) else ""
        if kind != "rejected" or not reason:
            unresolved.append({"id": finding.get("id"), "summary": finding.get("summary"),
                               "disposition": kind})
    return unresolved


def cmd_start_review(args) -> int:
    """검사관을 띄우기 직전에 검사 대상 문서의 지문을 checklist에 고정한다.

    닫을 때 이 지문과 대조해, 검사가 본 문서와 닫는 문서가 같은지 확인한다.
    """
    spec_dir = Path(args.spec_dir).resolve()
    checklist, stage_set, err = load_spec_checklist(spec_dir)
    if err:
        emit({"ok": False, "error": err})
        return 1
    review = stage_set.get("reviews", {}).get(args.stage)
    if review is None:
        emit({"ok": False, "error": f"'{args.stage}'는 이 workflow의 검사 단계가 아니다.",
              "reviews": sorted(stage_set.get("reviews", {}))})
        return 1
    pending = incomplete_before(checklist, stage_set, args.stage)
    if pending:
        emit({"ok": False, "error": f"'{args.stage}' 앞 단계가 끝나지 않았다.", "incomplete": pending})
        return 1
    fingerprint = doc_fingerprint(spec_dir, git_toplevel(spec_dir) or spec_dir, review["docs"])
    ts = stamp()
    for item in checklist["items"]:
        if item.get("title") == args.stage:
            item["status"] = "in_progress"
            item.setdefault("started_at", ts)
            item.pop("completed_at", None)
            item["inspected_at"] = ts
            item["inspected_fingerprint"] = fingerprint
    write_json(spec_dir / "workflow-checklist.json", checklist)
    emit({"ok": True, "stage": args.stage, "inspected_files": len(fingerprint)})
    return 0


def inspection_check(spec_dir: Path, checklist: dict, stage: str, result_path: Path,
                     current: dict, edited: str) -> tuple[dict | None, dict | None]:
    """(오류, 검사 뒤 수정 기록). 검사가 본 문서와 지금 문서가 같은지, 결과가 고정 뒤에 쓰였는지 본다."""
    item = next((it for it in checklist.get("items", []) if it.get("title") == stage), {})
    inspected = item.get("inspected_fingerprint")
    if not inspected:
        return {"ok": False, "error": f"'{stage}' 검사 대상이 고정되지 않았다.",
                "hint": f"검사관을 띄우기 전에 start-review --stage \"{stage}\"를 실행하고 검사를 다시 돌려라."}, None
    # 문서를 고친 뒤 고정을 다시 하는 길을 막는다. 결과는 고정 뒤에 쓰여야 한다.
    if result_path.stat().st_mtime < datetime.fromisoformat(item["inspected_at"]).timestamp():
        return {"ok": False, "error": f"{result_path.name}이 검사 대상을 고정하기 전에 쓰였다. 검사를 다시 돌려라."}, None
    changed = changed_keys(inspected, current)
    if not changed:
        return None, None
    if not edited.strip():
        return {"ok": False, "error": "검사한 뒤 바뀐 문서가 있다. 다시 검사하거나, 바뀐 내용을 사용자에게 알리고 "
                "확인받은 뒤 --edited \"<이유>\"로 닫아라.", "changed": changed}, None
    return None, {"files": changed, "reason": edited.strip(), "at": stamp()}


def cmd_close_analyze(args) -> int:
    """Analyze(7)를 닫는다.

    CRITICAL은 **근거를 적은 반려만** 통과한다. `fixed`(고치기로 했다)는 의사일 뿐이라 막는다 —
    실제로 해소됐는지는 다시 분석해 그 발견이 사라지는 것으로만 확인된다.
    닫으면서 그 시점 문서의 fingerprint를 남겨, 이후 문서가 바뀌면 preflight가 낡은 분석을 잡는다.
    """
    spec_dir = Path(args.spec_dir).resolve()
    if not (spec_dir / "workflow-checklist.json").exists():
        emit({"ok": False, "error": f"workflow-checklist.json 없음: {spec_dir}. "
              "spec_dir는 workflow-checklist.json이 있는 spec 루트여야 한다."})
        return 1

    analysis_path = spec_dir / "analysis.json"
    if not analysis_path.exists():
        emit({"ok": False, "error": f"analysis.json이 없다: {analysis_path}",
              "hint": "검사관 리포트의 JSON 블록을 모아 analysis.json으로 저장한 뒤 다시 실행하라."})
        return 1

    analysis = read_json(analysis_path)
    findings = analysis.get("findings")
    if not isinstance(findings, list):
        emit({"ok": False, "error": "analysis.json의 findings가 목록이 아니다."})
        return 1

    current = analyzed_fingerprint(spec_dir)
    bad, edited = inspection_check(spec_dir, read_json(spec_dir / "workflow-checklist.json"), "Analyze",
                                   analysis_path, current, args.edited)
    if bad:
        emit(bad)
        return 1

    unresolved = unresolved_critical(findings)
    if unresolved:
        emit({"ok": False, "error": "CRITICAL이 남아 Analyze를 닫을 수 없다. 근거를 적은 반려만 통과한다.",
              "hint": "고쳤다면 다시 분석해 그 발견이 사라진 것을 확인하라.",
              "unresolved": unresolved})
        return 1

    stage_set, review = analysis_review(spec_dir)
    bad = unchanged_since_problem(spec_dir, git_toplevel(spec_dir) or spec_dir, stage_set, review) or upstream_problem(spec_dir)
    if bad:
        emit(bad)
        return 1

    problems = lint_step_docs(spec_dir)
    if problems:
        emit({"ok": False, "error": "step 문서 형식이 어긋나 Analyze를 닫을 수 없다.",
              "problems": problems})
        return 1

    analysis["closed_at"] = stamp()
    analysis["fingerprint"] = current
    if edited:
        analysis["edited_after_review"] = edited
    write_json(analysis_path, analysis)

    if not update_workflow_item(spec_dir, "Analyze", "completed"):
        emit({"ok": False, "error": f"checklist에서 'Analyze' 항목을 찾지 못했다(경로: {spec_dir})."})
        return 1
    emit({"ok": True, "stage": "Analyze", "status": "completed",
          "fingerprint_files": len(analysis["fingerprint"])})
    return 0


def git_toplevel(start: Path) -> Path | None:
    r = git_ops.run_git(str(start), "rev-parse", "--show-toplevel")
    return Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None


def doc_fingerprint(base: Path, root: Path, patterns: list[str]) -> dict:
    """패턴에 걸리는 문서들의 내용 해시. `/`로 시작하는 패턴은 저장소 루트 기준, 나머지는 base 기준이다."""
    digest = {}
    for pat in patterns:
        anchor, rel = (root, pat[1:]) if pat.startswith("/") else (base, pat)
        for path in sorted(anchor.glob(rel)):
            if path.is_file():
                key = ("/" + path.relative_to(root).as_posix()) if pat.startswith("/") else path.relative_to(base).as_posix()
                digest[key] = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    return digest


def matches_any(key: str, patterns: list[str]) -> bool:
    """지문 키가 패턴 중 하나에 걸리나. `**`는 그 앞 경로 아래 전부다."""
    for pat in patterns:
        if "**" in pat:
            if key.startswith(pat.split("**")[0]):
                return True
        elif fnmatch.fnmatchcase(key, pat):
            return True
    return False


def unchanged_since_problem(spec_dir: Path, root: Path, stage_set: dict, review: dict) -> dict | None:
    """앞 검사가 본 문서가 그 뒤 바뀌었으면 앞 검사부터 다시 돌아야 한다."""
    for prev, docs in review.get("unchanged_since", {}).items():
        prev_path = spec_dir / stage_set["reviews"][prev]["file"]
        recorded = read_json(prev_path).get("fingerprint", {}) if prev_path.exists() else {}
        changed = changed_keys({k: v for k, v in recorded.items() if matches_any(k, docs)},
                               doc_fingerprint(spec_dir, root, docs))
        if changed:
            return {"ok": False, "error": f"'{prev}'를 닫은 뒤 바뀐 문서가 있다. 바뀐 문서로 '{prev}'를 다시 돌려 닫아라.",
                    "changed": changed}
    return None


def upstream_problem(spec_dir: Path) -> dict | None:
    """가져온 기능 spec 사본이 가져올 때와 같은가. 사본은 읽기 전용이고, 바꾸려면 docs 저장소에서 버전을 올린다."""
    meta_path = spec_dir / "upstream.json"
    if not meta_path.exists():
        return None
    recorded = read_json(meta_path).get("files", {})
    current = doc_fingerprint(spec_dir / "upstream", spec_dir / "upstream", ["**/*"])
    changed = changed_keys(recorded, current)
    if changed:
        return {"ok": False, "error": "가져온 기능 spec 사본(upstream/)이 바뀌었다. 사본은 고치지 않는다. "
                "요구를 바꿔야 하면 docs 저장소에서 기능 변경으로 버전을 올리고 다시 가져온다.", "changed": changed}
    return None


def changed_keys(recorded: dict, current: dict) -> list[str]:
    return sorted((set(recorded) ^ set(current)) | {k for k in set(recorded) & set(current) if recorded[k] != current[k]})


def load_spec_checklist(spec_dir: Path) -> tuple[dict | None, dict | None, str | None]:
    """(checklist, 단계 정의, 오류). 오류가 있으면 앞의 둘은 None이다."""
    path = spec_dir / "workflow-checklist.json"
    if not path.exists():
        return None, None, f"workflow-checklist.json 없음: {spec_dir}"
    checklist = read_json(path)
    stage_set = load_stage_set(checklist.get("workflow"))
    if stage_set is None:
        return None, None, f"workflow '{checklist.get('workflow')}'는 정의되지 않았다(stages.json)."
    return checklist, stage_set, None


def incomplete_before(checklist: dict, stage_set: dict, title: str) -> list[str]:
    titles = [s["title"] for s in stage_set["stages"]]
    status = {it.get("title"): it.get("status") for it in checklist.get("items", []) if isinstance(it, dict)}
    return [t for t in titles[:titles.index(title)] if status.get(t) != "completed"]


def cmd_close_review(args) -> int:
    """검사 단계를 닫는다. 검사 정의(결과 파일·판정 대상 문서·앞 검사 이후 바뀌면 안 되는 문서)는 stages.json에 있다.

    CRITICAL은 근거를 적은 반려만 통과한다. 닫으면서 판정 대상 문서의 지문을 결과 파일에 남긴다.
    """
    spec_dir = Path(args.spec_dir).resolve()
    checklist, stage_set, err = load_spec_checklist(spec_dir)
    if err:
        emit({"ok": False, "error": err})
        return 1
    review = stage_set.get("reviews", {}).get(args.stage)
    if review is None:
        emit({"ok": False, "error": f"'{args.stage}'는 이 workflow의 검사 단계가 아니다.",
              "reviews": sorted(stage_set.get("reviews", {}))})
        return 1
    pending = incomplete_before(checklist, stage_set, args.stage)
    if pending:
        emit({"ok": False, "error": f"'{args.stage}' 앞 단계가 끝나지 않았다.", "incomplete": pending})
        return 1
    root = git_toplevel(spec_dir) or spec_dir

    result_path = spec_dir / review["file"]
    if not result_path.exists():
        emit({"ok": False, "error": f"{review['file']}이 없다.",
              "hint": "검사관 리포트의 JSON 블록을 모아 저장한 뒤 다시 실행하라."})
        return 1
    result = read_json(result_path)
    findings = result.get("findings")
    if not isinstance(findings, list):
        emit({"ok": False, "error": f"{review['file']}의 findings가 목록이 아니다."})
        return 1
    current = doc_fingerprint(spec_dir, root, review["docs"])
    bad, edited = inspection_check(spec_dir, checklist, args.stage, result_path, current, args.edited)
    if bad:
        emit(bad)
        return 1
    unresolved = unresolved_critical(findings)
    if unresolved:
        emit({"ok": False, "error": f"CRITICAL이 남아 '{args.stage}'를 닫을 수 없다. 근거를 적은 반려만 통과한다.",
              "hint": "고쳤다면 다시 검사해 그 발견이 사라진 것을 확인하라.", "unresolved": unresolved})
        return 1

    bad = unchanged_since_problem(spec_dir, root, stage_set, review) or upstream_problem(spec_dir)
    if bad:
        emit(bad)
        return 1

    result["closed_at"] = stamp()
    result["fingerprint"] = current
    if edited:
        result["edited_after_review"] = edited
    write_json(result_path, result)
    if not update_workflow_item(spec_dir, args.stage, "completed"):
        emit({"ok": False, "error": f"checklist에서 '{args.stage}' 항목을 찾지 못했다."})
        return 1
    emit({"ok": True, "stage": args.stage, "status": "completed", "fingerprint_files": len(result["fingerprint"])})
    return 0


_VERSION_RE = re.compile(r"^(F\d+)-v(\d+)(?:\.(\d+))?$")


def _parse_version(tag: str):
    m = _VERSION_RE.match(tag)
    return (m.group(1), int(m.group(2)), int(m.group(3) or 0)) if m else None


def invariant_rows(text: str) -> list[str]:
    """표에서 `불변`으로 표시한 행만 모은다. 순서는 뜻이 아니므로 정렬한다."""
    rows = []
    for line in text.splitlines():
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if any(c == "불변" or c.startswith("불변(") for c in cells):
                rows.append(" | ".join(cells))
    return sorted(rows)


def frozen_changes(spec_dir: Path, root: Path, frozen_docs: list[str], tag: str) -> list[str]:
    """태그 이후 바뀐 동결 대상. `파일#불변`은 그 파일의 불변 행만 비교한다."""
    changed = []
    for entry in frozen_docs:
        name, _, part = entry.partition("#")
        rel = (spec_dir / name).relative_to(root).as_posix()
        if part == "불변":
            old = git_ops.run_git(str(root), "show", f"{tag}:{rel}")
            path = root / rel
            new_text = path.read_text(encoding="utf-8") if path.exists() else ""
            if invariant_rows(old.stdout if old.returncode == 0 else "") != invariant_rows(new_text):
                changed.append(f"{name}의 불변 시나리오")
        elif git_ops.run_git(str(root), "diff", "--quiet", tag, "--", rel).returncode != 0:
            changed.append(name)
    return changed


def freeze_problems(spec_dir: Path, root: Path, stage_set: dict, version: str) -> list[str]:
    """동결해도 되는지. 문제가 없으면 빈 목록."""
    problems = []
    parsed = _parse_version(version)
    if parsed is None:
        return [f"버전 형식이 아니다: {version} (예: F01-v1, F01-v1.1)"]
    fid, major, minor = parsed
    if not spec_dir.name.startswith(fid + "-"):
        problems.append(f"버전의 기능 번호({fid})가 폴더 이름({spec_dir.name})과 다르다.")

    reviews = stage_set.get("reviews", {})
    for title, review in reviews.items():
        path = spec_dir / review["file"]
        recorded = read_json(path).get("fingerprint") if path.exists() else None
        if not recorded:
            problems.append(f"'{title}'가 닫히지 않았다({review['file']}에 fingerprint 없음).")
            continue
        # 뒤 검사가 이어받은 검사는 뒤 검사가 지정한 문서만 본다. 나머지는 그 사이 단계가 바꾸는 게 정상이다.
        inherited = [d for r in reviews.values() for d in r.get("unchanged_since", {}).get(title, [])]
        docs = inherited or review["docs"]
        if inherited:
            recorded = {k: v for k, v in recorded.items() if matches_any(k, inherited)}
        changed = changed_keys(recorded, doc_fingerprint(spec_dir, root, docs))
        if changed:
            problems.append(f"'{title}'를 닫은 뒤 바뀐 문서가 있다: {', '.join(changed)}")

    changelog = root / "CHANGELOG.md"
    if not changelog.exists() or not re.search(rf"^## {re.escape(version)}\b", changelog.read_text(encoding="utf-8"), re.M):
        problems.append(f"CHANGELOG.md에 '## {version}' 항목이 없다.")
    index = spec_dir.parent / "index.md"
    if not index.exists() or not re.search(rf"^\|\s*{fid}\s*\|", index.read_text(encoding="utf-8"), re.M):
        problems.append(f"기능 목록({index.relative_to(root) if index.is_relative_to(root) else index})에 {fid} 행이 없다.")

    # 의존 기능은 먼저 동결돼 있어야 이 기능이 그 버전을 기준으로 삼을 수 있다.
    spec_md = spec_dir / "spec.md"
    dep_line = re.search(r"^- 의존:(.*)$", spec_md.read_text(encoding="utf-8"), re.M) if spec_md.exists() else None
    for dep in re.findall(r"F\d+-v\d+(?:\.\d+)?", dep_line.group(1) if dep_line else ""):
        if git_ops.run_git(str(root), "rev-parse", "-q", "--verify", f"refs/tags/{dep}").returncode != 0:
            problems.append(f"의존 기능 {dep}의 태그가 없다. 그 기능을 먼저 동결한다.")

    # 버전 규칙: 동결 문서의 뜻이 바뀌면 major, 그대로면 minor.
    tags = [t for t in git_ops.run_git(str(root), "tag", "-l", f"{fid}-v*").stdout.split() if _parse_version(t)]
    if git_ops.run_git(str(root), "rev-parse", "-q", "--verify", f"refs/tags/{version}").returncode == 0:
        problems.append(f"태그 {version}가 이미 있다.")
    if not tags:
        if (major, minor) != (1, 0):
            problems.append(f"첫 동결은 {fid}-v1이어야 한다.")
    else:
        latest = max(tags, key=lambda t: _parse_version(t)[1:])
        lmaj, lmin = _parse_version(latest)[1:]
        changed_docs = frozen_changes(spec_dir, root, stage_set.get("frozen_docs", []), latest)
        if (major, minor) == (lmaj + 1, 0):
            pass
        elif major == lmaj and minor == lmin + 1:
            if changed_docs:
                problems.append(f"{latest} 이후 동결 대상이 바뀌어({', '.join(changed_docs)}) {fid}-v{lmaj + 1}이어야 한다.")
        else:
            problems.append(f"{latest} 다음 버전은 {fid}-v{lmaj}.{lmin + 1}(동결 문서 그대로) 또는 {fid}-v{lmaj + 1}이다.")
    return problems


def main_checkout(start: Path) -> Path | None:
    """메인 체크아웃 루트. worktree 안에서 불러도 같은 곳을 가리킨다."""
    r = git_ops.run_git(str(start), "rev-parse", "--git-common-dir")
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return (start / r.stdout.strip()).resolve().parent


SET_DOCS_REPO_HINT = "사용자에게 docs 저장소의 로컬 경로를 묻고 `execute.py set-docs-repo <경로>`로 기록한다."


def upstream_repo(root: Path) -> tuple[Path | None, dict, str | None]:
    """(docs 저장소 경로, upstream 설정, 오류)."""
    up = instance_config.load_config(root).get("upstream")
    up = up if isinstance(up, dict) else {}
    main = main_checkout(root) or root
    local_path = main / instance_config.LOCAL_RELPATH
    try:
        path = json.loads(local_path.read_text(encoding="utf-8")).get("docs_repo")
    except (OSError, json.JSONDecodeError, AttributeError):
        path = None
    if not isinstance(path, str) or not path:
        return None, up, f"{local_path}에 docs_repo가 없다. " + SET_DOCS_REPO_HINT
    docs = Path(path).expanduser().resolve()
    if git_toplevel(docs) is None:
        return None, up, f"docs_repo가 git 저장소가 아니다: {docs}. " + SET_DOCS_REPO_HINT
    return docs, up, None


def cmd_set_docs_repo(args) -> int:
    """docs 저장소의 절대경로를 메인 체크아웃의 로컬 설정에 기록한다."""
    main = main_checkout(Path.cwd())
    if main is None:
        emit({"ok": False, "error": "git 저장소 안에서 실행한다."})
        return 1
    docs = Path(args.path).expanduser().resolve()
    if git_toplevel(docs) is None:
        emit({"ok": False, "error": f"git 저장소가 아니다: {docs}"})
        return 1
    local_path = main / instance_config.LOCAL_RELPATH
    data = read_json(local_path) if local_path.exists() else {}
    data["docs_repo"] = str(docs)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(local_path, data)
    out = {"ok": True, "file": str(local_path), "docs_repo": data["docs_repo"]}
    if git_ops.run_git(str(main), "check-ignore", "-q", instance_config.LOCAL_RELPATH).returncode != 0:
        out["warning"] = f"{instance_config.LOCAL_RELPATH}이 .gitignore에 없다. 개인 경로가 커밋되지 않게 `/{instance_config.LOCAL_RELPATH}`를 더한다."
    emit(out)
    return 0


def feature_tags(docs: Path, fid: str) -> list[str]:
    tags = [t for t in git_ops.run_git(str(docs), "tag", "-l", f"{fid}-v*").stdout.split() if _parse_version(t)]
    return sorted(tags, key=lambda t: _parse_version(t)[1:])


def cmd_import_feature(args) -> int:
    """docs 저장소의 동결 태그에서 기능 spec을 가져와 <spec>/upstream/에 읽기 전용으로 둔다.

    가져오는 것은 기능 폴더의 spec·시나리오·계약과, 같은 커밋의 용어집·domain·openapi다.
    파일마다 해시를 upstream.json에 남겨 검사 닫기와 preflight가 사본이 바뀌지 않았는지 본다.
    """
    spec_dir = Path(args.spec_dir).resolve()
    root = git_toplevel(spec_dir.parent if not spec_dir.exists() else spec_dir) or Path.cwd()
    docs, _, err = upstream_repo(root)
    if err:
        emit({"ok": False, "error": err})
        return 1
    parsed = _parse_version(args.version)
    if parsed is None:
        emit({"ok": False, "error": f"버전 형식이 아니다: {args.version} (예: F01-v1)"})
        return 1
    fid = parsed[0]
    if args.version not in feature_tags(docs, fid):
        emit({"ok": False, "error": f"docs 저장소에 태그 {args.version}가 없다. 동결된 버전만 가져온다.",
              "available": feature_tags(docs, fid)})
        return 1

    feature_root = instance_config.load_config(docs).get("feature_root") or "features"
    listed = git_ops.run_git(str(docs), "ls-tree", "-r", "--name-only", args.version).stdout.split("\n")
    folders = sorted({n.split("/")[1] for n in listed if n.startswith(f"{feature_root}/{fid}-") and n.count("/") >= 2})
    if len(folders) != 1:
        emit({"ok": False, "error": f"{args.version}에서 {fid} 기능 폴더를 하나로 찾지 못했다.", "found": folders})
        return 1
    folder = f"{feature_root}/{folders[0]}"
    wanted = {f"{folder}/{n}": n for n in ("spec.md", "scenarios.md", "contract.md")}
    wanted.update({n: n for n in listed if n == "glossary.md" or (n.startswith("domain/") and n.endswith(".md"))})
    wanted.update({n: "openapi.yaml" for n in listed if n == "api/openapi.yaml"})

    dest = spec_dir / "upstream"
    meta_path = spec_dir / "upstream.json"
    previous = read_json(meta_path).get("version") if meta_path.exists() else None
    if dest.exists():
        for f in dest.rglob("*"):
            if f.is_file():
                f.chmod(0o644)
        for f in sorted(dest.rglob("*"), reverse=True):
            f.unlink() if f.is_file() else f.rmdir()
    files = {}
    for src, rel in wanted.items():
        if src not in listed:
            continue
        shown = subprocess.run(["git", "show", f"{args.version}:{src}"], cwd=docs, capture_output=True)
        if shown.returncode != 0:
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(shown.stdout)
        out.chmod(0o444)
        files[rel] = hashlib.sha256(shown.stdout).hexdigest()[:12]
    commit = git_ops.run_git(str(docs), "rev-parse", f"{args.version}^{{commit}}").stdout.strip()
    source = {"commit": commit}
    remote = git_ops.run_git(str(docs), "remote", "get-url", "origin").stdout.strip()
    if remote:
        source["remote"] = remote
    meta = {"feature": fid, "version": args.version, "folder": folder,
            "source": source, "files": dict(sorted(files.items())),
            "imported_at": stamp()}
    if previous and previous != args.version:
        meta["previous_version"] = previous
    spec_dir.mkdir(parents=True, exist_ok=True)
    write_json(meta_path, meta)
    emit({"ok": True, "version": args.version, "files": sorted(files), "previous_version": meta.get("previous_version")})
    return 0


def upstream_freshness(spec_dir: Path, root: Path) -> tuple[dict | None, list[str]]:
    """(막을 오류, 알림). docs 저장소에 가져온 것보다 새 버전이 있는지 본다."""
    meta_path = spec_dir / "upstream.json"
    if not meta_path.exists():
        return None, []
    version = read_json(meta_path).get("version", "")
    parsed = _parse_version(version)
    docs, up, err = upstream_repo(root)
    if err or parsed is None:
        return None, [f"docs 저장소에서 새 버전을 확인하지 못했다: {err or version}"]
    fid, major, minor = parsed
    newer = [t for t in feature_tags(docs, fid) if _parse_version(t)[1:] > (major, minor)]
    if not newer:
        return None, []
    latest = newer[-1]
    if _parse_version(latest)[1] > major:
        return {"ok": False, "error": f"docs 저장소에 major 새 버전 {latest}가 있다(가져온 것은 {version}). 구현을 다시 확인해야 한다. "
                "CHANGELOG에서 바뀐 것을 확인하고 import-feature로 다시 가져온 뒤 Scope부터 다시 본다."}, []
    note = f"docs 저장소에 minor 새 버전 {latest}가 있다(가져온 것은 {version})."
    if up.get("on_newer_compatible") == "block":
        return {"ok": False, "error": note + " 설정이 block이라 막는다. 다시 가져온 뒤 실행한다."}, []
    return None, [note]


def cmd_freeze(args) -> int:
    """기능 spec을 동결한다. --tag 없이는 확인만 하고, 머지한 뒤 --tag로 태그를 찍는다.

    태그는 이 명령으로만 찍는다 — 검사가 닫혔고 그 뒤 문서가 바뀌지 않았을 때만 찍기 위해서다.
    """
    spec_dir = Path(args.spec_dir).resolve()
    root = git_toplevel(spec_dir)
    if root is None:
        emit({"ok": False, "error": f"git 저장소 안이 아니다: {spec_dir}"})
        return 1
    checklist, stage_set, err = load_spec_checklist(spec_dir)
    if stage_set is None:
        # 머지한 뒤의 체크아웃에는 진행 상태 파일이 없다. 태그를 찍을 때는 기능 정의만 있으면 된다.
        if not args.tag:
            emit({"ok": False, "error": err})
            return 1
        stage_set = load_stage_set("feature")
    if checklist is not None and not args.tag:
        pending = incomplete_before(checklist, stage_set, "Freeze")
        if pending:
            emit({"ok": False, "error": "Freeze 앞 단계가 끝나지 않았다.", "incomplete": pending})
            return 1

    problems = freeze_problems(spec_dir, root, stage_set, args.version)
    if args.tag:
        dirty = git_ops.run_git(str(root), "status", "--porcelain").stdout.strip()
        if dirty:
            problems.append("작업 트리에 커밋되지 않은 변경이 있다. 머지된 커밋에 태그를 찍어야 한다.")
    if problems:
        emit({"ok": False, "error": "동결할 수 없다.", "problems": problems})
        return 1

    if not args.tag:
        update_workflow_item(spec_dir, "Freeze", "in_progress")
        emit({"ok": True, "version": args.version, "tagged": False,
              "next": "PR을 올려 머지한 뒤, 머지된 체크아웃에서 --tag로 다시 실행한다."})
        return 0

    r = git_ops.run_git(str(root), "tag", "-a", args.version, "-m", args.version)
    if r.returncode != 0:
        emit({"ok": False, "error": f"태그를 만들지 못했다: {r.stderr.strip()}"})
        return 1
    if checklist is not None:
        update_workflow_item(spec_dir, "Freeze", "completed")
    head = git_ops.run_git(str(root), "rev-parse", "--short", "HEAD").stdout.strip()
    branch = git_ops.run_git(str(root), "branch", "--show-current").stdout.strip()
    emit({"ok": True, "version": args.version, "tagged": True, "commit": head, "branch": branch,
          "next": f"원격에 올리려면 git push origin {args.version}"})
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="execute.py", description="spec-harness subcommands")
    sub = parser.add_subparsers(dest="command", required=True)

    p_pre = sub.add_parser("preflight", help="phase index.json → workflow args(JSON)")
    p_pre.add_argument("phase_dir")
    p_pre.set_defaults(func=cmd_preflight)

    p_ctx = sub.add_parser("build-context", help="developer 컨텍스트 조립")
    p_ctx.add_argument("phase_dir")
    p_ctx.add_argument("--step", type=int, required=True)
    p_ctx.set_defaults(func=cmd_build_context)

    p_ac = sub.add_parser("verify-ac", help="Acceptance Criteria 실행·판정")
    p_ac.add_argument("phase_dir")
    p_ac.add_argument("--step", type=int, required=True)
    p_ac.add_argument("--attempt", type=int, default=1)
    p_ac.set_defaults(func=cmd_verify_ac)

    p_rec = sub.add_parser("record-step", help="phase index에 step 완료 기록")
    p_rec.add_argument("phase_dir")
    p_rec.add_argument("--step", type=int, required=True)
    p_rec.add_argument("--status", required=True, choices=["completed", "blocked", "error", "pending", "in_progress"])
    p_rec.add_argument("--summary", default="")
    p_rec.add_argument("--reason", default="")
    p_rec.add_argument("--attempts", default="", help="workflow가 모은 시도 이력(JSON 배열)")
    p_rec.set_defaults(func=cmd_record_step)

    p_reset = sub.add_parser("reset-step", help="blocked/error step을 pending으로 되돌림(사람이 고친 뒤)")
    p_reset.add_argument("phase_dir")
    p_reset.add_argument("--step", type=int, required=True)
    p_reset.set_defaults(func=cmd_reset_step)

    p_init = sub.add_parser("init-checklist", help="stages.json의 단계 정의로 spec 레벨 checklist 생성")
    p_init.add_argument("spec_dir", help="spec 디렉터리")
    p_init.add_argument("--workflow", default="harness", help="stages.json의 workflow 이름")
    p_init.add_argument("--reset", action="store_true", help="모든 단계가 끝난 checklist를 새로 만든다(기능 변경 시작)")
    p_init.set_defaults(func=cmd_init_checklist)

    p_stage = sub.add_parser("set-stage", help="spec 레벨 checklist의 Stage 상태 갱신(메인의 Execution 자동 흐름 + PR Review/Root Sync)")
    p_stage.add_argument("checklist_dir", help="spec 디렉터리(workflow-checklist.json이 있는 spec 루트)")
    p_stage.add_argument("stage", help="Stage 제목 (예: Execution, PR Review, Root Sync)")
    p_stage.add_argument("status", choices=["pending", "in_progress", "completed"])
    p_stage.set_defaults(func=cmd_set_stage)

    p_fin = sub.add_parser("finalize", help="phase 닫기(이 phase 상태 동기화·push)")
    p_fin.add_argument("phase_dir")
    p_fin.add_argument("--no-push", action="store_true")
    p_fin.set_defaults(func=cmd_finalize)

    p_hist = sub.add_parser("export-history", help="실행 이력을 execution-history.json으로 모음(Root Sync 전)")
    p_hist.add_argument("spec_dir", help="spec 디렉터리(phases/가 있는 spec 루트)")
    p_hist.set_defaults(func=cmd_export_history)

    p_lint = sub.add_parser("lint-steps", help="step 문서의 AC 파싱 계약 검사(실행하지 않음)")
    p_lint.add_argument("spec_dir", help="spec 디렉터리(phases/가 있는 spec 루트)")
    p_lint.set_defaults(func=cmd_lint_steps)

    p_start = sub.add_parser("start-review", help="검사관을 띄우기 직전에 검사 대상 문서를 고정")
    p_start.add_argument("spec_dir", help="checklist가 있는 디렉터리")
    p_start.add_argument("--stage", required=True, help="검사 단계 제목")
    p_start.set_defaults(func=cmd_start_review)

    p_review = sub.add_parser("close-review", help="검사 단계를 확인하고 닫음(stages.json의 reviews)")
    p_review.add_argument("spec_dir", help="checklist가 있는 디렉터리")
    p_review.add_argument("--stage", required=True, help="검사 단계 제목")
    p_review.add_argument("--edited", default="", help="검사 뒤 문서를 고쳤고 사용자가 확인한 경우 그 이유")
    p_review.set_defaults(func=cmd_close_review)

    p_import = sub.add_parser("import-feature", help="docs 저장소의 동결 태그에서 기능 spec을 upstream/으로 가져옴")
    p_import.add_argument("spec_dir", help="구현 spec 디렉터리")
    p_import.add_argument("--version", required=True, help="예: F01-v1.1")
    p_import.set_defaults(func=cmd_import_feature)

    p_setrepo = sub.add_parser("set-docs-repo", help="docs 저장소의 로컬 경로를 .spec-harness/local.json에 기록")
    p_setrepo.add_argument("path", help="docs 저장소의 로컬 체크아웃 경로")
    p_setrepo.set_defaults(func=cmd_set_docs_repo)

    p_freeze = sub.add_parser("freeze", help="기능 spec 동결 확인, --tag면 태그 생성")
    p_freeze.add_argument("spec_dir", help="기능 spec 디렉터리")
    p_freeze.add_argument("--version", required=True, help="예: F01-v1, F01-v1.1")
    p_freeze.add_argument("--tag", action="store_true", help="머지된 체크아웃에서 태그를 찍는다")
    p_freeze.set_defaults(func=cmd_freeze)

    p_close = sub.add_parser("close-analyze", help="analysis.json을 확인하고 Analyze(7)를 completed로 닫음")
    p_close.add_argument("spec_dir", help="spec 디렉터리(workflow-checklist.json이 있는 spec 루트)")
    p_close.add_argument("--edited", default="", help="검사 뒤 문서를 고쳤고 사용자가 확인한 경우 그 이유")
    p_close.set_defaults(func=cmd_close_analyze)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
