#!/usr/bin/env python3
from __future__ import annotations

"""PreToolUse — Root Sync(10)가 끝나기 전의 PR 머지·draft 해제를 막는다.

Stage 8이 PR을 draft로 열고, Root Sync가 끝난 뒤 `execute.py ready-pr`가 draft를 벗긴다.
그 순서를 Bash에서 건너뛰는 경로를 이 hook이 닫는다. `ready-pr`는 스크립트 안에서 gh를 부르므로
이 hook에 보이지 않아, 게이트를 확인하는 경로만 남는다.

Root Sync가 안 끝난 spec이 없으면 통과한다 — 하네스와 무관한 세션의 `gh pr merge`를 막지 않는다.
"""

import json
import sys
from pathlib import Path

CONFIG_RELPATH = ".spec-harness/config.json"
DEFAULT_SPEC_ROOT = "docs/specs"
EXECUTION_TITLE = "Execution"
ROOT_SYNC_TITLE = "Root Sync"


def targets_merge(command: str) -> bool:
    """공백을 정리한 명령이 PR 머지·draft 해제를 시도하는가."""
    if "gh pr merge" in command or "gh pr ready" in command:
        return True
    # gh api로 머지 엔드포인트를 직접 PUT하는 우회 경로.
    return "gh api" in command and "/merge" in command and (
        "-X PUT" in command or "--method PUT" in command or "-XPUT" in command
    )


def git_root(start: Path) -> Path | None:
    """worktree의 .git은 디렉터리가 아니라 파일이므로 exists()로 함께 잡는다."""
    for d in [start, *start.parents]:
        if (d / ".git").exists():
            return d
    return None


def spec_root(root: Path) -> Path:
    cfg = root / CONFIG_RELPATH
    if cfg.exists():
        try:
            value = json.loads(cfg.read_text(encoding="utf-8")).get("spec_root")
        except (OSError, json.JSONDecodeError):
            value = None
        if isinstance(value, str) and value:
            return root / value
    return root / DEFAULT_SPEC_ROOT


def pending_specs(specs_dir: Path) -> list[str]:
    """Execution이 시작됐고 Root Sync가 안 끝난 spec 이름 목록."""
    pending = []
    for checklist in sorted(specs_dir.glob("*/workflow-checklist.json")):
        try:
            items = json.loads(checklist.read_text(encoding="utf-8")).get("items", [])
        except (OSError, json.JSONDecodeError):
            continue
        status = {it.get("title"): it.get("status") for it in items if isinstance(it, dict)}
        if (status.get(EXECUTION_TITLE) in {"in_progress", "completed"}
                and status.get(ROOT_SYNC_TITLE) != "completed"):
            pending.append(checklist.parent.name)
    return pending


def emit_block(reason: str) -> int:
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.flush()
    return 0


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if not isinstance(payload, dict) or payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return 0

    # 검사 대상이 아니면 파일을 하나도 읽지 않고 통과한다.
    if not targets_merge(" ".join(command.split())):
        return 0

    root = git_root(Path(payload.get("cwd") or Path.cwd()).resolve())
    if root is None:
        return 0
    pending = pending_specs(spec_root(root))
    if not pending:
        return 0

    return emit_block(
        "Root Sync(10)가 끝나지 않은 spec이 있어 머지·draft 해제를 막았다: "
        + ", ".join(pending)
        + ". 루트 문서 동기화와 `_archive` 승격을 커밋한 뒤 "
        "`execute.py ready-pr <spec 디렉터리>`로 draft를 벗겨라 — 그 스크립트가 승격본이 "
        "커밋됐는지 확인한다."
    )


if __name__ == "__main__":
    raise SystemExit(main())
