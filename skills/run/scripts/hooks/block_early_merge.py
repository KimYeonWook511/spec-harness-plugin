#!/usr/bin/env python3
from __future__ import annotations

"""PreToolUse — agent가 내는 PR 머지 명령을 Root Sync(10) 기준으로 판정한다.

루트 문서 갱신과 `_archive` 승격이 커밋되기 전에 머지되면
명세 기록이 통째로 사라진다. 그래서 checklist의 Root Sync 상태와 `_archive` 승격본의 실제 커밋
여부를 함께 본다.

무엇을 할지는 저장소가 `.spec-harness/config.json`의 `merge.agent`로 정한다. 이 설정의 소비자는
이 hook뿐이다.

  ask(기본)   Root Sync가 안 끝났으면 사용자에게 확인을 띄운다. 막지는 않는다.
  root_sync   Root Sync가 안 끝났으면 거절한다.
  deny        agent의 머지 명령을 무조건 거절한다.

`ask`·`root_sync`는 검사할 spec이 없으면 그냥 통과한다 — 하네스를 쓰지 않는 저장소에는 읽을
checklist가 없으므로 이 hook이 관여할 일이 없다.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

CONFIG_RELPATH = ".spec-harness/config.json"
DEFAULT_SPEC_ROOT = "docs/specs"
EXECUTION_TITLE = "Execution"
ROOT_SYNC_TITLE = "Root Sync"

DEFAULT_POLICY = "ask"
POLICIES = {"ask", "root_sync", "deny"}


def targets_merge(command: str) -> bool:
    """공백을 정리한 명령이 PR 머지를 시도하는가."""
    if "gh pr merge" in command:
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


def read_settings(root: Path) -> tuple[Path, str]:
    """저장소 설정에서 spec 루트와 머지 정책을 한 번에 읽는다. 없거나 깨졌으면 기본값."""
    loaded = {}
    cfg = root / CONFIG_RELPATH
    if cfg.exists():
        try:
            parsed = json.loads(cfg.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            parsed = None
        if isinstance(parsed, dict):
            loaded = parsed

    value = loaded.get("spec_root")
    specs_dir = root / value if isinstance(value, str) and value else root / DEFAULT_SPEC_ROOT

    merge = loaded.get("merge")
    policy = merge.get("agent") if isinstance(merge, dict) else None
    return specs_dir, policy if policy in POLICIES else DEFAULT_POLICY


def archived_in_head(root: Path, specs_dir: Path, spec_name: str) -> bool:
    """`_archive` 승격본이 HEAD에 커밋됐는가.

    staging이 아니라 HEAD를 본다 — 커밋되지 않은 사본은 PR에 올라가지 않는다. 승격 폴더 이름에
    들어가는 PR 번호를 hook은 모르므로 이름 패턴으로 찾는다.
    """
    try:
        rel = (specs_dir / "_archive").relative_to(root).as_posix()
    except ValueError:
        return False
    r = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD", "--", rel],
        cwd=root, capture_output=True, text=True,
    )
    if r.returncode != 0:
        return False
    pattern = re.compile(rf"(?:^|/)pr-\d+-{re.escape(spec_name)}/spec\.md$")
    return any(pattern.search(line) for line in r.stdout.splitlines())


def pending_specs(root: Path, specs_dir: Path) -> list[str]:
    """Root Sync가 남은 spec 목록.

    checklist의 Root Sync 상태는 메인 에이전트가 찍는 값이라, 승격을 건너뛴 채 `completed`로
    찍힐 수 있다. 그래서 상태가 찍힌 spec은 승격본이 실제로 커밋됐는지 git으로 한 번 더 본다.
    """
    pending = []
    for checklist in sorted(specs_dir.glob("*/workflow-checklist.json")):
        try:
            items = json.loads(checklist.read_text(encoding="utf-8")).get("items", [])
        except (OSError, json.JSONDecodeError):
            continue
        status = {it.get("title"): it.get("status") for it in items if isinstance(it, dict)}
        if status.get(EXECUTION_TITLE) not in {"in_progress", "completed"}:
            continue
        name = checklist.parent.name
        if status.get(ROOT_SYNC_TITLE) != "completed":
            pending.append(name)
        elif not archived_in_head(root, specs_dir, name):
            pending.append(f"{name}(`_archive` 승격본이 커밋되지 않았다)")
    return pending


def emit(decision: str, reason: str) -> int:
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
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
    specs_dir, policy = read_settings(root)

    if policy == "deny":
        return emit("deny", "이 저장소는 agent의 PR 머지를 허용하지 않는다"
                            "(`.spec-harness/config.json`의 `merge.agent`가 `deny`). 사람이 직접 머지한다.")

    pending = pending_specs(root, specs_dir)
    if not pending:
        return 0

    found = "Root Sync(10)가 끝나지 않은 spec이 있다: " + ", ".join(pending) + "."
    if policy == "root_sync":
        return emit("deny", found + " 루트 문서 동기화와 `_archive` 승격을 커밋한 뒤 다시 시도하라.")
    return emit("ask", found + " 지금 머지하면 루트 문서 갱신과 `_archive` 승격이 사라진다. 그래도 진행할까?")


if __name__ == "__main__":
    raise SystemExit(main())
