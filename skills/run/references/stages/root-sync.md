# Root Sync

이 Stage는 Stage 9(PR Review) 완료가 확인된 뒤에만 착수한다. PR review까지 코드가 확정된 시점에 루트 문서를 현재 상태로 동기화한다. merge 직전 1회 수행을 기본으로 하며, 코드가 또 바뀌면 다시 실행할 수 있는 멱등 연산으로 본다.

문서 종류별로 동작이 다르다. 한 지시로 뭉치지 않는다.

- **ADR (append)**: 루트 ADR은 수정·삭제하지 않는다. spec ADR(staging)에서 새로 채택된 결정만 루트 전역 번호로 이어붙인다. 기존 결정을 대체하면 새 레코드에 `supersedes`를 적고, 옛 레코드 상태를 `superseded`로 바꾼다(상태 한 줄 갱신은 허용). 이미 기록된 결정인지 확인 후 새 결정만 추가한다.
- **architecture / db-schema / api-spec (overwrite)**: 루트 현재 파일과 spec 문서를 **둘 다 입력으로 읽고**, 기억으로 재작성하지 말고 현재 루트 기준으로 이번 변경분만 반영한 전체 완성본을 출력한다. 이번에 안 건드린 부분은 보존한다.

위 루트 동기화와 **별개로**, 이 spec의 작업 기록을 영구 보존한다.

- **실행 이력 내보내기** (옮기기 전에): 시도 이력은 진행 상태 파일에만 있어 옮기면 사라진다. 먼저 한 파일로 모아 스테이징한다. 스테이징한 파일은 아래 `git mv`가 함께 옮긴다.

  ```bash
  python3 "<SKILL_DIR>/scripts/execute.py" export-history <SPEC_ROOT>/<spec-name>
  git add <SPEC_ROOT>/<spec-name>/execution-history.json
  ```

- **`_archive` 승격**: Stage 8에서 커밋해 둔 spec 정본을 `<SPEC_ROOT>/_archive/pr-<PR번호>-<spec명>/`로 **옮긴다**(`git mv`). 작업 폴더는 그 자리에서 사라지고, 머지된 트리에는 `_archive` 사본만 남는다. PR 번호는 Stage 8에서 PR을 열 때 이미 정해져 있다.
  - **복사가 아니라 옮기는 이유**: 같은 내용이 두 경로에 남으면 어느 쪽이 정본인지 흐려지고, 나중에 한쪽만 고쳐지면 갈라진다. `_archive`는 끝난 작업이 가는 곳이므로 작업 폴더가 거기로 들어가는 것이 맞다.
  - **옮기지 않는 것**: 진행 상태·실행 부산물 — `phases/index.json`, `phases/<phase>/index.json`, `workflow-checklist.json`, `step<N>-ac-output.json`, `logs/`. `.gitignore` 대상이라 애초에 추적되지 않으며, 작업 폴더를 비울 때 함께 사라진다.
  - **승격 대상**: 그 밖의 **모든 `.md`**와 `analysis.json`·`execution-history.json`. `.md` 목록을 열거하지 않는 이유는, 열거하면 새 문서가 생길 때 조용히 빠지기 때문이다. 실제로는 `spec.md`·`plan.md`·`scenarios.md`·`data-model.md`·`architecture.md`·`db-schema.md`·`api-spec.md`·`adr.md`·`interview.md`·`research.md`와 `phases/<phase>/step<N>.md` 중 작성된 것이 해당한다.
  - **`scenarios.md`·`data-model.md`를 빠뜨리면 안 된다** — 동결된 계약과 상태 전이 정본이다. 작업 폴더는 이 단계에서 비워지므로, 옮기지 않으면 step 문서의 `## 검증 대상`이 가리키는 시나리오 식별자가 존재하지 않는 문서를 향하게 된다.
  - 옮기기만 한다. 내용을 재작성하지 않는다. 루트 ADR append는 위에서 이미 했으므로, `_archive`의 `adr.md`는 "이 spec이 그 결정에 어떻게 도달했나"의 맥락 기록이다.

sync 후 agent는 변경 요약(루트 문서 중 무엇을 갱신·보존했는지, `_archive`로 무엇을 승격했는지)을 보고하고 사용자 검토를 받는다. 커밋·push는 Stage 8(Execution)에서 오픈한 같은 PR에 쌓는다(루트 문서 갱신 + `_archive` 사본이 함께 올라간다).

## 이 Stage의 마지막

위 커밋·push가 끝나면 Root Sync를 `completed`로 찍는다. Stage 10(Root Sync)이 spec-harness의 마지막 단계다.

**merge는 이 워크플로의 단계가 아니다** — 누가 어떤 형식으로 머지하는지는 저장소가 자기 규칙으로 정한다. agent가 Bash로 내는 머지 명령은 `merge-hook`이 가로채 판정한다(`SKILL.md`의 "게이트" 표).

회고는 이 워크플로의 단계가 아니다. 끝난 spec들의 기록을 돌아보려면 `retro` skill(`/spec-harness:retro`)을 쓴다.
