# Execution

Stage 8(Execution) 실행은 **dynamic workflow(`/spec-harness:execute`)를 기동**해 수행한다. `execute.py`를 직접 돌려
phase를 완주시키지 않는다 — 대신 preflight로 workflow 인자를 만들고, workflow가 step 루프를 돈다.
실행 전 아래 순서를 반드시 거친다. 이 순서는 스크립트가 막지 않으므로 메인 에이전트가 지킨다(`preflight`가 막는 것은 checklist 상태뿐이다).

1. Analyze까지의 결과(작성한 spec 문서·phase 경로)와 실행 계획을 사용자에게 보고하고, 실행 진행 의사를 가볍게 확인받는다. 별도 Plan Mode·`ExitPlanMode` 절차는 거치지 않는다.
2. **명세를 먼저 커밋한다** (아래 절).
3. `AskUserQuestion`으로 agent별 실행 모델을 수집한다. (아래 "실행 옵션 수집" 절 참고)
4. 수집한 모델을 phase index의 `execution` 필드에 기록한 뒤, preflight → workflow 기동으로 실행한다.

- workflow는 worktree 안에서 기동하며, committer·finalizer 서브에이전트를 통해 커밋·push를 수행한다.
- 이 Stage에 들어가기 전 checklist의 `Interview`부터 `Analyze`까지(1~7)는 모두 `completed`여야 한다.
- 사용자가 승인하지 않으면 구현으로 진행하지 않는다.

> spec 정본(spec 문서·step 문서·`analysis.json` 등)은 **Stage 8 진입 때 한 번 커밋해 PR 에서 보이게 한다**(아래 "명세를 먼저 커밋한다"). 그 뒤 구현이 설계와 달라져 spec 설계 md 를 as-built 로 고치면 그 수정은 **그것을 만든 step 의 커밋에 함께** 들어간다. 진행 상태·실행 부산물(`workflow-checklist.json`·`phases/**/index.json`·`step<N>-ac-output.json`·`logs/`)만 `.gitignore` 대상이라 커밋되지 않는다.

## 명세를 먼저 커밋한다

구현을 시작하기 전에 spec 정본을 **한 커밋으로** 남긴다. 그래야 PR을 여는 순간부터 리뷰어가 그 문서를 볼 수 있다.

```
docs: <spec명> 명세를 기록한다
```

**왜 먼저 커밋하나.** 루트 상태 문서 갱신은 Root Sync(10)까지 미뤄지는데, 그 사이 리뷰어는 "루트가 왜 코드와 안 맞나"를 판단할 근거가 없다. 그 근거가 spec 문서에 있으므로 리뷰 전에 보여야 한다. 마지막에 한 번에 올리면 정작 리뷰 시점에는 안 보인다.

커밋 대상은 spec 정본이다 — `.md`, `analysis.json`, 방법론이 요구한 `.yaml`. 진행 상태·실행 부산물은 `.gitignore`가 막는다.

> 저장소가 이 형태를 받으려면 `.gitignore`가 spec 폴더를 통째로 무시하지 않고 **진행 상태·실행 부산물만** 무시해야 한다. 설치 안내의 `.gitignore` 절을 따른다.

## 실행 옵션 수집

workflow 기동 직전, `AskUserQuestion`으로 agent별 모델을 한 번에 수집한다. 한 호출에 세 질문을 묶어 전달해 한 화면에 동시에 표시한다.

| 질문 (header) | 옵션 (label) | 기본 권장 |
| --- | --- | --- |
| Developer | `sonnet (Recommended)` / `opus` / `haiku` | sonnet |
| Reviewer | `opus (Recommended)` / `sonnet` / `haiku` | opus |
| Commit | `haiku (Recommended)` / `sonnet` / `opus` | haiku |

옵션값 변환 규칙:

- label에서 첫 공백 또는 ` (` 이전 토큰을 추출해 모델 값으로 사용한다. 예: `"sonnet (Recommended)"` → `sonnet`.
- 사용자가 "Other"를 선택하고 자유 입력하면 입력 문자열을 그대로 모델 값으로 전달한다. alias(`opus`/`sonnet`/`haiku`)와 full name 형태를 모두 받는다.
- 옵션을 묻지 않고 기본값으로 진행하라는 명시 지시가 있으면 Developer=sonnet / Reviewer=opus / Commit=haiku를 사용한다.

수집된 값은 phase index의 `execution` 필드에 1회 기록되어 추적 가능해진다. 재실행 시에는 기존 값이 보존된다. 자세한 스키마는 `<SKILL_DIR>/references/phase-files.md`를 참고한다.

## 실행 — Stage 8 자동 흐름 (in_progress → phase 루프 → completed)

`phases` 파일이 준비되고 모델이 정해지면, 메인은 **Stage 8 진입과 동시에 아래 ①~③을 하나의 자동 흐름으로 수행한다.** 사람이 단계마다 개입해 in_progress·completed를 일일이 지시하는 게 아니라, 메인이 이 절차를 끝까지 자동으로 진행한다. checklist는 **spec 레벨에 하나**(`workflow-checklist.json`, spec 폴더 바로 아래)이고, 그 안에서 **phase는 여러 개일 수 있다**(각 phase가 자기 step들을 따로 돈다).

> **스크립트 경로 (`<SKILL_DIR>`)**: 아래 명령의 `<SKILL_DIR>`는 이 스킬(run)의 base directory 절대경로다 — 스킬이 호출될 때 함께 주어지는 그 경로를, `<SPEC_ROOT>/<spec-name>` 같은 다른 자리표시자처럼 실제 값으로 치환해 실행한다. 플러그인은 설치 시 전역 캐시로 복사되므로 저장소 상대경로로는 스크립트를 찾을 수 없다. (매 Bash 호출은 새 셸이라 셸 변수로는 이어지지 않으니, 매 명령에서 절대경로로 치환한다.)

**① Execution을 in_progress로 — 자동, 진입 시 1회**

Stage 8에 들어가면 메인이 곧바로 checklist의 Execution을 in_progress로 표시한다(phase 루프를 시작하기 직전, spec 단위 1회).

```bash
python3 "<SKILL_DIR>/scripts/execute.py" set-stage <SPEC_ROOT>/<spec-name> Execution in_progress
```

**② phase 루프 — 모든 phase에 대해 preflight → workflow 반복 (자동)**

메인은 spec의 각 phase(`1-main`, 또는 `1-domain`·`2-api` …)를 순서대로 돌린다. phase가 하나면 1회, 여러 개면 차례로 반복한다. 사람 개입 없이 이어서 진행한다.

```bash
# (2-a) preflight — 위에서 만든 작업 공간 루트에서
python3 "<SKILL_DIR>/scripts/execute.py" preflight <SPEC_ROOT>/<spec-name>/phases/<phase-name>/
```

STDOUT으로 `{"ok": true, "execute": "...", "phase_dir": "...", "steps": [...], "execution": {...}, ...}`
형태의 JSON 한 줄이 나온다. 이것을 그대로 workflow 인자로 넘긴다.

```
# (2-b) workflow 기동
/spec-harness:execute with args <preflight가 출력한 JSON 전체>
```

> 참고: 이 런타임에서 workflow `args`는 JSON **문자열**로 주입된다. workflow 스크립트가 내부에서
> 파싱하므로, preflight 출력 JSON을 그대로 넘기면 된다. 자연어로 막연히 "실행해" 두면 args가 채워지지 않으니
> 저장된 `/spec-harness:execute` 명령으로 호출한다.

workflow는 `pending`인 step부터 순차로 developer→(AC확인)→reviewer→committer→recorder를 돌리고,
모든 step이 끝나면 finalizer로 **그 phase를 닫는다**(이 phase의 completed_at·spec index phase status·push). 진행은 `/workflows` 뷰로 관찰하고, 사람용 로그는 `<phase>/logs/<role>.log`에 쌓인다. 한 phase가 `blocked`/`error`로 멈추면 루프를 멈추고 사람에게 보고한다(자동 재개하지 않는다).

**③ Execution을 completed로 — 자동, 전 phase 완료 시 1회**

phase 루프가 끝나 `phases/index.json`의 모든 phase status가 completed가 되면, 메인이 곧바로 Execution을 completed로 표시하고 PR Review(9)로 넘어간다.

```bash
python3 "<SKILL_DIR>/scripts/execute.py" set-stage <SPEC_ROOT>/<spec-name> Execution completed
```

> **왜 set-stage가 흐름의 양 끝에만 있나**: in_progress·completed는 *spec 전체*의 Execution 상태라 phase 루프를 감싸는 자리에서 1회씩 자동으로 찍는다. 반면 preflight·finalize는 *phase 단위*라 spec 레벨 Stage를 건드리지 않는다 — phase 하나가 끝났다고 Execution을 completed로 만들면, 남은 phase가 있을 때 어긋나기 때문이다. 그래서 "phase 닫기(finalize)"와 "Execution 닫기(set-stage completed)"를 분리하되, 메인이 ①~③을 한 흐름으로 자동 수행한다.

실행 규칙:
- 구현 요청을 받으면 먼저 `phases` 문서와 `workflow-checklist.json`이 준비됐는지, 사용자 진행 확인을 받았는지 확인한다.
- 준비 또는 승인이 부족하면 구현하지 않고 누락된 Stage로 돌아간다.
- 사용자가 명시적으로 수동 구현을 지시한 경우에만 workflow를 우회할 수 있으며, 이때도 해당 예외를 먼저 사용자 업데이트에 분명히 남긴다.

workflow 운영 규칙:
- step 완료/중단 상태는 recorder가 phase index에 기록한다. 상세 산출물·파일 포맷은 `<SKILL_DIR>/references/phase-files.md`를 따른다.
- 결과 `outcome`이 `blocked`/`error`이면 즉시 중단된 것이다. 사용자에게 `stopped_at_step`·`reason`을 보고한다. finalize는 일어나지 않는다.
- **중단된 step의 재개는 사람이 원인을 고친 뒤 `reset-step`으로 명시적으로 신호한다**(아래 "중단·재개").
- agent는 사용자 승인 없이 실패 회피 목적으로 step 요구사항, Acceptance Criteria, spec 문서, root docs를 수정해 재시도하지 않는다.
- 실패 원인이 문서 누락, Acceptance Criteria 오류처럼 명확해 보여도 자동 수정하지 않는다. 먼저 원인과 수정 계획을 사용자에게 제시한다.

## 중단·재개 (pending-only)

- `blocked`/`error`로 멈추면 사용자 승인 없이 자동 복구하지 않는다. 실패 step·사유를 보고한다.
- workflow는 **`pending`인 step만 실행**한다. 그래서 중단된 step(`blocked`/`error`)을 그냥 재실행하면
  workflow가 자동 재개하지 않고 다시 멈춘다(`needs_reset: true`). 이는 의도된 동작이다 — 원인을 안 고친 채
  재실행해 같은 실패를 반복하며 토큰을 낭비하지 않게 하기 위함이다.
- 사람이 원인을 고친 뒤(예: 누락 문서 보강, 환경 문제 해결), 그 step을 pending으로 되돌린다:

```bash
python3 "<SKILL_DIR>/scripts/execute.py" reset-step <SPEC_ROOT>/<spec-name>/phases/<phase-name>/ --step N
```

  그런 다음 같은 phase로 preflight → `/spec-harness:execute`를 다시 기동하면, 이미 `completed`인 step은
  건너뛰고 reset한 step부터 재개한다.

## 커밋·finalize

step별 committer는 **코드 변경과, 그 step 이 as-built 로 고친 spec 설계 문서를 함께** 커밋한다. 진행 상태·실행 부산물은 `.gitignore` 대상이라 `git status`·`git add`에 잡히지 않으므로 신경 쓸 필요가 없다.

phase 종료 시점에 finalizer(`execute.py finalize`)는 git 커밋을 만들지 않는다. 대신 다음을 한다:

1. phase index.json에 `completed_at`을 기록하고, 상위 spec `phases/index.json`의 이 phase status를 `completed`로 동기화한다. (둘 다 진행 상태 파일이라 gitignore 대상이고 워킹트리 상태로만 남는다 — 재개·skip 판단에 쓰인다.)
2. `execution.push`가 true이고 `--no-push`가 아니면 현재 feature 브랜치를 원격으로 push한다. 이 push가 올리는 것은 step별 committer가 만든 **코드 커밋**이다.

`execution.push`가 false면 push를 생략하지만, PR은 원격에 push해야 열 수 있으므로 Stage 9(PR Review)로 진행하려면 push가 필요하다.

## Stage 8 종료

- Stage 8은 workflow로 phase의 step을 모두 완료하고, phase 끝에서 원격 push한 뒤 PR을 오픈하는 것으로 종료한다.
- PR 오픈(`gh pr create`)은 메인 에이전트가 phase 루프 직후 수행한다. workflow는 구현·검증·커밋·push까지 책임지고, PR 오픈은 그 바깥이다.
- 루트 docs 동기화는 Stage 8(Execution)에 포함하지 않는다. Stage 10(Root Sync)에서 수행한다.
- 실행 중 코드가 spec 설계와 달라지면 **해당 spec 폴더의 설계 md(`architecture.md`·`api-spec.md`·`db-schema.md`)만 실제 구현된 대로 갱신**하고 루트 상태 문서는 건드리지 않는다. `spec.md`(요구·완료 기준)는 실행 중 편집하지 않는다 — 요구 변경은 Clarify로 되돌아간다. 루트 승격은 Root Sync(10)가 한다.
- PR은 Stage 8에서 한 번만 오픈한다. PR Review(9)는 같은 브랜치·같은 PR에 커밋·push를 더 쌓을 뿐 PR을 새로 열지 않는다.
- PR을 오픈한 뒤 메인 에이전트는 PR Review(9)로 자동 진행하지 않고 멈춰, 사용자의 검토 완료 신호를 기다린다. 이 시점에 리뷰 코멘트가 아직 없다는 것은 PR Review 완료가 아니므로, Root Sync(10)를 앞당기지 않는다.
