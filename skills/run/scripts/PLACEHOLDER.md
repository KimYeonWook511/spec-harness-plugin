# scripts (자리표시)

엔진 스크립트가 여기 들어간다. 플러그인 안에서는 `${CLAUDE_PLUGIN_ROOT}/skills/run/scripts/...`로 참조한다.

- `execute.py` — 실행 단계 진입/상태 관리
- `acceptance_check.py` — step의 AC 커맨드를 실제 실행하고 기대 exit code와 대조 (임의 셸 실행, 스택 무관)
- `git_ops.py` — 커밋·브랜치 등 git 조작
- `format_events.py` — 진행 이벤트 포맷

이 스크립트들은 git·python·셸만 전제하며 특정 빌드 도구를 하드코딩하지 않는다.
