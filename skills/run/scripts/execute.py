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
  record-step     phase index.json에 step.status/summary/completed_at 기록 (recorder agent 전용)
  reset-step      blocked/error step을 pending으로 되돌림 (사람이 원인을 고친 뒤 재개용)
  set-stage       spec 레벨 checklist의 Stage 8/9/10 상태 갱신 (메인의 Execution 자동 흐름 + PR Review/Root Sync — preflight·finalize는 안 건드림)
  finalize        phase 닫기: 이 phase의 completed_at·spec index 동기화(워킹트리) + 선택적 push (finalizer agent 전용)
  lint-steps      step 문서의 Acceptance Criteria 파싱 계약 검사 (실행하지 않고 형식만)
  close-analyze   analysis.json의 CRITICAL 처리·step 형식을 확인하고 Analyze(7)를 닫음 + fingerprint 기록
  ready-pr        Root Sync 완료와 _archive 승격 커밋을 확인한 뒤 draft PR을 ready로 전환

설계 원칙:
  - 함수 기반: 셔틀 상태가 없고 각 서브커맨드가 한 번 실행되고 끝이므로 클래스가 불필요.
  - 각 서브커맨드는 결과를 stdout에 JSON으로 출력한다(agent가 그 JSON을 받아 workflow에 반환).
  - 무거운 로직은 모듈(acceptance_check/step_context/git_ops)에 있고, 여기선 입구만 얇게.
"""

import argparse
import hashlib
import json
import re
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


# 세 묶음으로 읽는다: 명세(1~5, 사람 주도·끝에서 동결) → 변환·검증(6~7, 다시 만들어도 되는 산출물)
# → 실행(8~10, 기계 구현 후 리뷰·루트 반영).
_WORKFLOW_ITEMS = [
    (1, "Interview"),
    (2, "Specify"),
    (3, "Clarify"),
    (4, "Scenarios"),
    (5, "Design"),
    (6, "Steps"),
    (7, "Analyze"),
    (8, "Execution"),
    (9, "PR Review"),
    (10, "Root Sync"),
]
# 단계 목록은 여러 곳에 동기화돼야 한다(이 리스트 / 템플릿의 workflow-checklist.json /
# SKILL.md 상태표·각 ### 헤더 / phase-files.md 예시 / 아래 게이트 경계).
# 항목 개수는 len()으로 동적 처리되지만, 게이트 경계 리터럴(EXECUTION_ORDER)은 별도이므로 함께 갱신해야 한다.

# Execution 단계의 order. 이 앞(1..EXECUTION_ORDER-1)은 모두 completed여야 실행 게이트를 통과한다.
# 명세 묶음(Interview~Design)과 변환·검증 묶음(Steps·Analyze)이 모두 끝나야 실행에 들어간다.
EXECUTION_ORDER = 8


def validate_workflow_checklist(checklist_dir: Path) -> dict:
    """실행 전 게이트: 문서 검토·실행 승인 완료 여부를 강제한다.

    checklist는 spec 레벨에 하나다(`<spec>/workflow-checklist.json`).
    Execution(8) 직전 단계(1~7: Interview·Specify·Clarify·Scenarios·Design·Steps·Analyze)가
    모두 completed이고 Execution(8)이 pending/in_progress여야 통과.
    통과하면 {"ok": True}, 아니면 {"ok": False, "error": ...}를 반환한다.
    (게이트 미통과 시 preflight는 emit으로 알리고 종료한다.)

    참고: "Clarify 위험마커 0 + Analyze 통과"라는 의미 게이트는 별도 코드 검사가 아니라,
    Clarify(3)·Analyze(7) 단계를 completed로 표시하는 행위가 그 조건의 충족을 뜻한다는 규약으로 강제한다
    (마커가 남았으면 Clarify를 completed로 두지 않고, Analyze가 실패하면 Analyze를 completed로 두지 않는다).
    """
    checklist_path = checklist_dir / "workflow-checklist.json"
    if not checklist_path.exists():
        return {"ok": False, "error": f"workflow-checklist.json 없음: {checklist_path}. "
                "Stage 1~7(Interview~Analyze)을 마치고 실행 승인을 기록한 checklist를 만든 뒤 실행하라."}

    checklist = read_json(checklist_path)
    if checklist.get("workflow") != "harness":
        return {"ok": False, "error": "workflow-checklist.json의 workflow가 'harness'가 아니다."}

    items = checklist.get("items")
    if not isinstance(items, list) or len(items) != len(_WORKFLOW_ITEMS):
        return {"ok": False, "error": f"workflow-checklist.json은 {len(_WORKFLOW_ITEMS)}개 harness workflow 항목을 가져야 한다."}

    invalid, incomplete = [], []
    for idx, (order, title) in enumerate(_WORKFLOW_ITEMS):
        item = items[idx] if idx < len(items) else {}
        if not isinstance(item, dict) or item.get("order") != order or item.get("title") != title:
            invalid.append(f"{order}. {title}")
            continue
        status = item.get("status")
        if order < EXECUTION_ORDER and status != "completed":
            incomplete.append(title)
        if order == EXECUTION_ORDER and status not in {"pending", "in_progress"}:
            invalid.append(f"{order}. {title} status must be pending or in_progress")

    if invalid:
        return {"ok": False, "error": "workflow-checklist.json 항목이 올바르지 않다.", "invalid": invalid}
    observed = {it.get("order") for it in items if isinstance(it, dict)}
    if {o for o, _ in _WORKFLOW_ITEMS} != observed:
        return {"ok": False, "error": "workflow-checklist.json에 누락/중복된 order가 있다."}
    if incomplete:
        return {"ok": False, "error": "harness workflow가 실행 승인되지 않았다(Execution 직전 단계 미완).", "incomplete": incomplete}
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


# Analyze가 판정한 문서들. 실행 상태 파일(index.json·checklist)은 넣지 않는다 — 실행 중 바뀐다.
_ANALYZED_DOCS = (
    "spec.md", "plan.md", "scenarios.md", "architecture.md",
    "data-model.md", "db-schema.md", "api-spec.md", "adr.md",
)


def analyzed_fingerprint(spec_dir: Path) -> dict:
    """Analyze가 본 문서들의 내용 해시. 닫은 뒤 문서가 바뀌면 그 분석은 낡은 것이다."""
    digest = {}
    for name in _ANALYZED_DOCS:
        path = spec_dir / name
        if path.exists():
            digest[name] = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    for step in sorted((spec_dir / "phases").glob("*/step*.md")):
        key = step.relative_to(spec_dir).as_posix()
        digest[key] = hashlib.sha256(step.read_bytes()).hexdigest()[:12]
    return digest


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
    emit({"ok": True, "step": args.step, "status": args.status})
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
    # Stage 1~7을 이 명령으로 찍으면 그 앞 게이트가 근거 없이 열린다.
    allowed = {title for order, title in _WORKFLOW_ITEMS if order >= EXECUTION_ORDER}
    if args.stage not in allowed:
        emit({"ok": False, "error": f"set-stage로 갱신할 수 있는 Stage는 {sorted(allowed)}뿐이다. "
              f"'{args.stage}'는 진행하며 작성·갱신하는 단계다."})
        return 1
    matched = update_workflow_item(checklist_dir, args.stage, args.status)
    if not matched:
        emit({"ok": False, "error": f"checklist에서 '{args.stage}' 항목을 찾지 못했다(경로: {checklist_dir}). "
              "checklist_dir는 spec 디렉터리(workflow-checklist.json이 있는 spec 루트)여야 하고 stage는 정확한 Stage 제목이어야 한다."})
        return 1
    emit({"ok": True, "stage": args.stage, "status": args.status})
    return 0


def cmd_finalize(args) -> int:
    """phase 닫기: 이 phase의 completed_at 기록·spec index 동기화(워킹트리) + 선택적 push.

    finalizer agent가 phase 끝에 호출한다 — workflow 한 번 기동 = phase 하나 완주.
    spec 폴더(phase index 포함)는 .gitignore 대상이라 커밋하지 않는다 — 여기서는
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
    if unresolved:
        emit({"ok": False, "error": "CRITICAL이 남아 Analyze를 닫을 수 없다. 근거를 적은 반려만 통과한다.",
              "hint": "고쳤다면 다시 분석해 그 발견이 사라진 것을 확인하라.",
              "unresolved": unresolved})
        return 1

    problems = lint_step_docs(spec_dir)
    if problems:
        emit({"ok": False, "error": "step 문서 형식이 어긋나 Analyze를 닫을 수 없다.",
              "problems": problems})
        return 1

    analysis["closed_at"] = stamp()
    analysis["fingerprint"] = analyzed_fingerprint(spec_dir)
    write_json(analysis_path, analysis)

    if not update_workflow_item(spec_dir, "Analyze", "completed"):
        emit({"ok": False, "error": f"checklist에서 'Analyze' 항목을 찾지 못했다(경로: {spec_dir})."})
        return 1
    emit({"ok": True, "stage": "Analyze", "status": "completed",
          "fingerprint_files": len(analysis["fingerprint"])})
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# ready-pr — Root Sync 완료를 확인한 뒤 draft 해제
# ─────────────────────────────────────────────────────────────────────────────
def _lookup_pr(root: str, pr: int | None) -> tuple[int | None, bool | None, str]:
    """PR 번호와 draft 여부를 조회한다. pr이 None이면 현재 브랜치의 PR을 찾는다."""
    target = [str(pr)] if pr else []
    r = git_ops.run_gh(root, "pr", "view", *target, "--json", "number,isDraft")
    if r.returncode != 0:
        return None, None, r.stderr.strip() or "gh pr view 실패"
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None, None, "gh pr view 출력을 파싱하지 못했다"
    return data.get("number"), data.get("isDraft"), ""


def cmd_ready_pr(args) -> int:
    """Root Sync가 끝났음을 확인한 뒤 draft PR을 ready로 바꾼다.

    draft를 벗는 유일한 경로다 — hook이 Bash의 `gh pr ready`를 막으므로 아래 확인을 지나지 않고
    draft를 벗을 방법이 없다. 그중 핵심은 `_archive` 승격본이 커밋됐는지 확인하는 것이다.
    spec 폴더는 .gitignore 대상이라, 승격을 건너뛴 채 머지되면 명세 기록이 통째로 사라진다.
    """
    spec_dir = Path(args.spec_dir).resolve()
    checklist_path = spec_dir / "workflow-checklist.json"
    if not checklist_path.exists():
        emit({"ok": False, "error": f"workflow-checklist.json 없음: {checklist_path}. "
              "spec_dir는 workflow-checklist.json이 있는 spec 루트여야 한다."})
        return 1

    items = read_json(checklist_path).get("items", [])
    done = {it.get("title") for it in items if isinstance(it, dict) and it.get("status") == "completed"}
    incomplete = [f"{order}. {title}" for order, title in _WORKFLOW_ITEMS if title not in done]
    if incomplete:
        emit({"ok": False, "error": "Root Sync(10)까지 끝나지 않아 draft를 벗길 수 없다.",
              "incomplete": incomplete})
        return 1

    top = git_ops.run_git(str(Path.cwd()), "rev-parse", "--show-toplevel")
    root = top.stdout.strip() if top.returncode == 0 and top.stdout.strip() else str(Path.cwd())

    number, is_draft, err = _lookup_pr(root, args.pr)
    if number is None:
        emit({"ok": False, "error": f"PR을 찾지 못했다: {err}", "hint": "--pr <번호>로 직접 지정할 수 있다."})
        return 1

    # spec_dir의 부모가 곧 spec 루트이므로, _archive는 그 옆에 있다.
    archived_spec = spec_dir.parent / "_archive" / f"pr-{number}-{spec_dir.name}" / "spec.md"
    if not archived_spec.exists():
        emit({"ok": False, "error": f"_archive 승격본이 없다: {archived_spec}",
              "hint": "Root Sync의 `_archive` 승격을 먼저 수행하라."})
        return 1

    # staging이 아니라 HEAD를 본다 — 커밋되지 않은 사본은 PR에 올라가지 않는다.
    try:
        relpath = archived_spec.relative_to(Path(root)).as_posix()
    except ValueError:
        emit({"ok": False, "error": f"_archive 승격본이 저장소 밖에 있다: {archived_spec}"})
        return 1
    committed = git_ops.run_git(root, "cat-file", "-e", f"HEAD:{relpath}")
    if committed.returncode != 0:
        emit({"ok": False, "error": f"_archive 승격본이 커밋되지 않았다: {relpath}",
              "hint": ".gitignore의 `_archive` 예외를 확인하고 이 사본을 커밋하라."})
        return 1

    if is_draft is False:
        emit({"ok": True, "pr": number, "already_ready": True})
        return 0

    r = git_ops.run_gh(root, "pr", "ready", str(number))
    if r.returncode != 0:
        emit({"ok": False, "error": f"gh pr ready 실패: {r.stderr.strip()}"})
        return 1
    emit({"ok": True, "pr": number, "readied": True})
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
    p_rec.set_defaults(func=cmd_record_step)

    p_reset = sub.add_parser("reset-step", help="blocked/error step을 pending으로 되돌림(사람이 고친 뒤)")
    p_reset.add_argument("phase_dir")
    p_reset.add_argument("--step", type=int, required=True)
    p_reset.set_defaults(func=cmd_reset_step)

    p_stage = sub.add_parser("set-stage", help="spec 레벨 checklist의 Stage 상태 갱신(메인의 Execution 자동 흐름 + PR Review/Root Sync)")
    p_stage.add_argument("checklist_dir", help="spec 디렉터리(workflow-checklist.json이 있는 spec 루트)")
    p_stage.add_argument("stage", help="Stage 제목 (예: Execution, PR Review, Root Sync)")
    p_stage.add_argument("status", choices=["pending", "in_progress", "completed"])
    p_stage.set_defaults(func=cmd_set_stage)

    p_fin = sub.add_parser("finalize", help="phase 닫기(이 phase 상태 동기화·push)")
    p_fin.add_argument("phase_dir")
    p_fin.add_argument("--no-push", action="store_true")
    p_fin.set_defaults(func=cmd_finalize)

    p_lint = sub.add_parser("lint-steps", help="step 문서의 AC 파싱 계약 검사(실행하지 않음)")
    p_lint.add_argument("spec_dir", help="spec 디렉터리(phases/가 있는 spec 루트)")
    p_lint.set_defaults(func=cmd_lint_steps)

    p_close = sub.add_parser("close-analyze", help="analysis.json을 확인하고 Analyze(7)를 completed로 닫음")
    p_close.add_argument("spec_dir", help="spec 디렉터리(workflow-checklist.json이 있는 spec 루트)")
    p_close.set_defaults(func=cmd_close_analyze)

    p_ready = sub.add_parser("ready-pr", help="Root Sync 완료 확인 후 draft PR을 ready로 전환")
    p_ready.add_argument("spec_dir", help="spec 디렉터리(workflow-checklist.json이 있는 spec 루트)")
    p_ready.add_argument("--pr", type=int, default=None, help="PR 번호(생략하면 현재 브랜치의 PR)")
    p_ready.set_defaults(func=cmd_ready_pr)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
