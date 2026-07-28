from __future__ import annotations

"""spec-harness Acceptance Criteria 검사·판정 모듈.

핵심 동작:
  1. expectExit 비교: step 문서가 명령별 기대 exit code를 명시(`# expect: N`)할 수 있고,
     명시가 없으면 0이 기본값이다. → "이 파일이 없어야 한다"(exit 1 기대) 같은 역조건 AC를 표현 가능.
  2. 전 명령 실행: 첫 실패에서 멈추지 않고 모든 명령을 끝까지 돌려, 어떤 명령이 왜 깨졌는지
     전부 보고한다(developer가 한 번에 다 고치도록).
  3. attempts 누적: ac-output.json을 덮어쓰지 않고 시도별로 append 한다(감사·회고 재료).
"""

import json
import re
import subprocess
from pathlib import Path

# 명령 하나의 상한. 넘기면 그 명령을 실패로 기록하고 다음으로 넘어간다.
COMMAND_TIMEOUT_SEC = 900
# ac-output.json에 남길 출력 길이 상한(명령별, stdout·stderr 각각).
OUTPUT_TAIL_CHARS = 8000


def _tail(text: str) -> str:
    """출력이 길면 뒤쪽만 남긴다 — 실패 원인은 대개 끝에 있다."""
    if not text or len(text) <= OUTPUT_TAIL_CHARS:
        return text or ""
    return f"[앞부분 {len(text) - OUTPUT_TAIL_CHARS}자 생략]\n" + text[-OUTPUT_TAIL_CHARS:]

# 명령줄 바로 앞 줄(또는 같은 줄 끝)에서 기대 exit code를 읽는 주석 형식:
#   # expect: 1
#   <검증 명령>                     (명시 없음 → 기본 0)
_EXPECT_PATTERN = re.compile(r"#\s*expect\s*:\s*(\d+)\s*$", re.IGNORECASE)

DEFAULT_EXPECT_EXIT = 0


def extract_acceptance_commands(step_text: str) -> list[dict]:
    """step 문서의 `## Acceptance Criteria` 섹션에서 (command, expect_exit) 목록을 뽑는다.

    반환: [{"command": str, "expect_exit": int}, ...]

    파싱 규칙:
      - `## Acceptance Criteria` 헤더부터 다음 `## ` 헤더(또는 문서 끝)까지가 본문.
      - 그 안의 ```bash / ```sh 코드블록의 각 줄이 명령 후보.
      - 빈 줄은 무시. `# expect: N` 형태의 주석은 "바로 다음 명령"의 기대 exit를 지정한다.
      - 그 외 `#` 주석은 무시한다.
      - 기대 exit 미지정 명령은 DEFAULT_EXPECT_EXIT(0).
    """
    match = re.search(
        r"^## Acceptance Criteria\s*$\n(?P<body>.*?)(?=^## |\Z)",
        step_text,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return []

    commands: list[dict] = []
    for block in re.findall(r"```(?:bash|sh)\n(.*?)```", match.group("body"), re.DOTALL):
        pending_expect = DEFAULT_EXPECT_EXIT
        has_pending = False
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("#"):
                expect_match = _EXPECT_PATTERN.search(line)
                if expect_match:
                    pending_expect = int(expect_match.group(1))
                    has_pending = True
                # expect 주석이 아니면 일반 주석 → 무시
                continue
            # 같은 줄 끝에 붙은 `# expect: N`도 허용
            inline = _EXPECT_PATTERN.search(line)
            if inline:
                expect_exit = int(inline.group(1))
                command = line[: inline.start()].strip()
            else:
                expect_exit = pending_expect if has_pending else DEFAULT_EXPECT_EXIT
                command = line
            if command:
                commands.append({"command": command, "expect_exit": expect_exit})
            pending_expect = DEFAULT_EXPECT_EXIT
            has_pending = False
    return commands


_EXPECT_LOOSE = re.compile(r"#\s*expect\s*:", re.IGNORECASE)


def malformed_expect_lines(step_text: str) -> list[str]:
    """`# expect:` 를 썼지만 정수로 읽히지 않아 조용히 기본값이 되는 줄을 찾는다."""
    match = re.search(
        r"^## Acceptance Criteria\s*$\n(?P<body>.*?)(?=^## |\Z)",
        step_text,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return []
    bad = []
    for raw_line in match.group("body").splitlines():
        line = raw_line.strip()
        if _EXPECT_LOOSE.search(line) and not _EXPECT_PATTERN.search(line):
            bad.append(line)
    return bad


def output_path(phase_dir: Path, step_num: int) -> Path:
    return phase_dir / f"step{step_num}-ac-output.json"


def check(root: str, phase_dir: Path, write_json, step: dict, step_text: str, attempt: int) -> dict | None:
    """AC 명령을 전부 실행하고 expectExit와 비교해 판정한다. attempts에 누적 기록.

    반환: 이번 attempt의 결과 dict (AC가 없으면 None).
      {
        "step": N, "attempt": M, "passed": bool,
        "results": [{"command", "expectExit", "actualExit", "ok", "stdout", "stderr"}, ...]
      }
    """
    commands = extract_acceptance_commands(step_text)
    if not commands:
        return None

    results: list[dict] = []
    passed = True
    for entry in commands:
        command = entry["command"]
        expect_exit = entry["expect_exit"]
        timed_out = False
        try:
            completed = subprocess.run(
                command,
                cwd=root,
                shell=True,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT_SEC,
            )
            actual_exit, out, err = completed.returncode, completed.stdout, completed.stderr
        except subprocess.TimeoutExpired as exc:
            # 타임아웃이 없으면 멈춘 통합 테스트 하나가 phase 전체를 세운다.
            timed_out = True
            actual_exit = None
            out = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            err = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            err += f"\n[timeout] {COMMAND_TIMEOUT_SEC}초를 넘겨 중단했다."

        ok = (not timed_out) and actual_exit == expect_exit
        results.append({
            "command": command,
            "expectExit": expect_exit,
            "actualExit": actual_exit,
            "ok": ok,
            "timedOut": timed_out,
            # 전문을 싣지 않는다 — 빌드 로그가 수 MB면 developer 반환 JSON이 잘려 파싱이 깨진다.
            "stdout": _tail(out),
            "stderr": _tail(err),
        })
        if not ok:
            passed = False
            # 첫 실패에서 멈추지 않는다 — 나머지 명령도 돌려 전체 실패 상황을 한 번에 보고.

    attempt_record = {
        "step": step["step"],
        "attempt": attempt,
        "passed": passed,
        "results": results,
    }

    # attempts 누적 (덮어쓰기 아님)
    path = output_path(phase_dir, step["step"])
    existing = load_output(path) or {"step": step["step"], "attempts": []}
    if not isinstance(existing.get("attempts"), list):
        existing = {"step": step["step"], "attempts": []}
    existing["attempts"].append(attempt_record)
    write_json(path, existing)

    return attempt_record


def load_output(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None
