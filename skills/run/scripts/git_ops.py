from __future__ import annotations

"""spec-harness git 조작 헬퍼."""

import subprocess


def run_git(root: str, *args) -> subprocess.CompletedProcess:
    """git 명령을 실행하고 stdout/stderr를 캡처한다."""
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
    )
