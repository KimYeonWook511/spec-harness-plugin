from __future__ import annotations

"""spec-harness git·gh 조작 헬퍼."""

import subprocess


def run_git(root: str, *args) -> subprocess.CompletedProcess:
    """git 명령을 실행하고 stdout/stderr를 캡처한다."""
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
    )


def run_gh(root: str, *args) -> subprocess.CompletedProcess:
    """gh CLI를 실행한다.

    hook은 Bash 도구 호출만 보므로 여기서 부르는 gh는 그 검사를 지나지 않는다. draft 해제가
    게이트를 확인하는 `ready-pr` 경로 하나로만 일어나게 하는 장치다.
    """
    return subprocess.run(
        ["gh", *args],
        cwd=root,
        capture_output=True,
        text=True,
    )
