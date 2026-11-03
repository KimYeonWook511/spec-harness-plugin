---
name: run
description: 이 저장소에서 "harness로 spec 실행", "하네스로 이 phase 돌려줘", "<spec>의 <phase>를 자동 실행", 또는 구현 전 명세 정의(Specify)·모호함 해소(Clarify)·검증 시나리오 확정(Scenarios)·설계(Design)·step 분해(Steps)·정합성 검사(Analyze)·phase/step 기반 자동 구현 요청이 오면 반드시 이 skill을 사용한다. 명세를 먼저 확정하고 그 명세가 구현을 끌고 가는 SDD 워크플로우로, 위험영역(결제·인증·데이터 모델·상태 전이 등 틀리면 데이터·돈·접근권한이 깨지는 영역)은 가정 없이 확정한다. 인터뷰·Specify·Clarify·Scenarios·Design·Steps·Analyze의 확정 단계부터, 준비된 phase를 dynamic workflow(/spec-harness:execute)로 자동 완주시키는 실행, PR·루트 동기화까지 전체를 담당한다. 사용자가 "skill"·"harness"·"workflow"·"스펙"이라는 말을 정확히 쓰지 않아도 이 흐름에 해당하면 적용한다.
---

# Spec Harness Workflow

이 harness는 **명세를 먼저 확정하고, 그 명세가 구현을 끌고 가게** 한다(이른바 명세 주도 개발, SDD). 바로 코드를 짜지 않는다 — 먼저 spec을 세우고(Specify), 모호한 곳은 추측으로 메우지 않고 마커로 드러내 사용자와 해소하며(Clarify), 위험영역(틀리면 데이터·돈·접근권한이 깨지는 영역 — 결제·인증·데이터 모델·상태 전이 등)은 절대 가정하지 않는다. 그렇게 *확정된* 명세와 설계만 자동 실행으로 넘긴다.

전체 흐름은 10개 Stage이고, 성격이 다른 **세 묶음**으로 나뉜다.

| 묶음 | Stage | 성격 |
| --- | --- | --- |
| **명세** | 1 Interview · 2 Specify · 3 Clarify · 4 Scenarios · 5 Design | **사람이 주도**해 무엇을 어떻게 만들지 확정한다. 끝에서 요구와 시나리오가 **동결**된다. |
| **변환·검증** | 6 Steps · 7 Analyze | 확정된 명세를 기계가 실행할 단위로 옮기고, 옮긴 것이 명세와 맞는지 대조한다. **다시 만들어도 되는** 산출물이다. |
| **실행** | 8 Execution · 9 PR Review · 10 Root Sync | **기계가 구현**하고 사람이 리뷰하며 루트에 반영한다. |

명세 묶음은 며칠에 걸쳐 오갈 수 있고 실행 묶음은 한 번에 완주한다. 그래서 **한 세션에 다 끝내지 않아도 되며**, checklist를 근거로 중간 단계부터 재개한다(아래 "재진입").

### 동결 — 무엇이 불변인가

동결은 **명세 묶음을 나갈 때(Design(5) 통과) 한 번** 일어난다. 그 안에서는 단계 사이를 오갈 수 있다.

| 대상 | 동결되나 | 이후 |
| --- | --- | --- |
| `spec.md`의 요구·완료 기준 | **동결** | **읽기만 한다.** 요구가 바뀌면 명세 묶음으로 되돌아가 새 버전으로 다시 확정한다. 실행 중 편집 금지. |
| `불변`으로 표시한 시나리오 | **동결** | **계약이다.** 구현이 어렵다는 이유로 고치지 않는다. |
| `유동`으로 표시한 시나리오 | 동결 안 함 | 구현 방식이 바뀌면 함께 바뀔 수 있다. |
| 설계 문서(구조·스키마·API 등) | 동결 안 함 | 코드가 달라지면 **실제 구현된 대로** 갱신한다. |
| phase·step·AC | 동결 안 함 | 실행이 막히면 재분해할 수 있다. |

동결과 재작성 가능을 가르는 기준은 "**틀렸을 때 무엇이 깨지는가**"다. 요구·불변 시나리오가 흔들리면 만들던 것이 달라지고, 분해가 틀린 것은 다시 나누면 된다.

### 게이트 — 무엇이 막나

게이트는 **조건을 만족하지 못하면 다음 단계로 넘어가지 않는 지점**이다. 무엇이 그것을 막는지는 게이트마다 다르고, 이 표가 단일 출처다. 각 단계 본문에서는 그냥 "게이트"라고 부른다.

| 단계 | 게이트 | 통과 조건 | 누가 판정하고 누가 막나 |
| --- | --- | --- | --- |
| Clarify(3) | 위험영역 확정 | 위험영역 마커가 하나도 남지 않았다. 사용자가 "됐다"고 해도 면제되지 않는다 | 메인 에이전트 |
| Scenarios(4) | 확인 방법 완비 | 확인 방법이 없는 기능 요구사항·완료 기준이 없다 | 메인 에이전트 |
| Design(5) | 원칙 점검 | 위험영역이 모두 확정됐고, 규칙 문서를 위반하지 않는다 | 메인 에이전트 |
| Design(5) | 동결 확인 | 동결된다는 사실을 알리고 사용자가 진행 의사를 밝혔다 | 사용자가 답해야 넘어간다 |
| Analyze(7) | 정합성 | CRITICAL 중 근거를 적은 반려가 아닌 것이 없다 | 검사관 여섯이 판정하고 `close-analyze`가 막는다 |
| Analyze(7) | step 형식 | 모든 step 문서에서 AC와 `## 검증 대상`이 파싱된다 | `close-analyze`가 파서로 판정하고 막는다 |
| Execution(8) | 분석 최신 | Analyze를 닫은 뒤 판정 대상 문서가 바뀌지 않았다 | `preflight`가 내용 해시로 판정하고 막는다 |
| Analyze(7) | 검토 후 중단 | 작성한 문서 경로를 보고하고 사용자의 검토 응답을 받았다. "진행해"는 승인이 아니다 | 사용자가 답해야 넘어간다 |
| Execution(8) | 실행 승인 | 사용자가 실행을 승인했다 | 사용자가 답해야 넘어간다 |
| Execution(8) | 실행 전 검사 | 1~7이 모두 `completed`이고 Stage 8이 `pending` 또는 `in_progress`다 | `preflight`가 판정하고 막는다 |
| Execution(8) | AC 통과 | 각 명령의 exit code가 기대값과 일치한다 | `verify-ac`가 exit code로 판정해 파일에 남기지만, `execute.js`가 보는 값은 **developer가 반환한 것**이다 |
| Execution(8) | 보고 대조 | developer가 보고한 AC 결과가 파일에 기록된 것과 일치한다 | `reviewer`가 파일을 읽어 판정하고 `execute.js`가 막는다 |
| Execution(8) | 검토 승인 | reviewer 판정이 `approved`다 | `reviewer`가 판정하고 `execute.js`가 막는다 |
| Execution(8) | step 3회 시도 한도 | 한 step의 시도가 3회를 넘지 않는다(형식 오류·AC 미통과·재검토 요청을 합쳐 센다) | `execute.js`가 판정하고 막는다 |
| Execution(8) | 중단된 step 재실행 | 그 step의 status가 `pending`이다 | `execute.js`가 판정하고 막는다 |
| Root Sync(10) | 리뷰 완료 | Stage 9가 `completed`다. 리뷰 코멘트가 없다는 것은 완료를 뜻하지 않는다 | 사용자가 답해야 넘어간다 |
| Root Sync(10) | 이른 머지 검사 | Root Sync가 `completed`이고 `_archive` 승격본이 HEAD에 커밋됐다 | `merge-hook`이 checklist와 git으로 판정한다. 거절할지 확인만 할지는 저장소 설정 `merge.agent`가 정한다 |

표에 나온 이름:

| 이름 | 무엇 |
| --- | --- |
| `preflight` · `verify-ac` · `close-analyze` | `<SKILL_DIR>/scripts/execute.py`의 서브커맨드. 파일·명령을 실제로 보고 판정한다 |
| `execute.js` | `<PLUGIN_DIR>/workflows/execute.js`. step 실행을 조율하며 조건이 어긋나면 다음 단계를 부르지 않는다 |
| `merge-hook` | `<PLUGIN_DIR>/skills/run/scripts/hooks/block_early_merge.py`. PreToolUse로 Bash 명령을 보고 이른 머지를 판정한다 |
| 검사관 여섯 | `spec-harness:analyzer-*`. Analyze의 관점별 전용 에이전트로, 읽기 전용이라 판정만 하고 스스로 막지 못한다 |
| `reviewer` | 전용 에이전트 `spec-harness:reviewer`. 읽기 전용이라 판정만 한다 |
| 메인 에이전트 | 이 skill을 실행하는 에이전트 |

**모델 판단이 하나도 끼지 않는 게이트는 다섯이다** — 실행 전 검사, step 형식, 분석 최신, step 3회 시도 한도, 중단된 step 재실행. 이 다섯은 스크립트가 파일과 자기 데이터(checklist·문서 해시·파서 결과·시도 횟수·step status)만 보고 판정한다.

Root Sync의 게이트는 통과 조건에 checklist 상태가 들어가고, 그것은 메인이 찍는다. 다만 `_archive` 승격본이 실제로 커밋됐는지는 git으로 확인하므로 **문서 승격을 건너뛴 것은 드러난다.** 이 hook은 agent의 Bash 명령만 본다 — 사람이 GitHub 웹에서 머지 버튼을 누르는 것은 막지 못한다.

나머지 열은 어딘가에 모델 판단이 들어간다. 특히 **AC 통과 게이트를 오해하지 마라.**

> `verify-ac`가 명령을 실제로 돌려 exit code로 판정하고 그 결과를 `step<N>-ac-output.json`에 남기는 것은 맞다. 그런데 `execute.js`는 **파일을 읽을 수단이 없어서**(워크플로 스크립트에 파일 접근이 없다) developer가 반환한 JSON의 `ac.passed`를 본다. 즉 이 게이트는 **developer의 자기보고**에 걸려 있고, 그것을 파일과 대조하는 것은 바로 아래 "보고 대조" 게이트(`reviewer`가 수행)다. **두 게이트는 짝이다** — 대조를 빠뜨리면 AC를 통과하지 않은 코드가 커밋까지 갈 수 있다.

그래서 게이트를 새로 더할 때는 **무엇이 그것을 막는지, 그 판정에 모델이 끼는지 함께 정해야 한다.** 정하지 않으면 지시만 남고 실제로는 아무것도 막지 않는다.

### 명세 묶음 안에서 되돌아오는 길

명세 묶음은 한 방향으로만 흐르지 않는다. 아래 두 되돌림은 **정상 동작**이며, 막지 않는다.

- **Scenarios(4) → Clarify(3)**: 시나리오를 쓰다 보면 "이 경우엔 어떻게 되나"가 드러난다. 시나리오 작성은 가장 좋은 모호함 탐지기다 — 그때는 임의로 가정하지 말고 Clarify로 돌아가 확정한다.
- **Design(5) → Scenarios(4)**: 시나리오는 두 종류다. **행위·계약 시나리오**는 설계를 몰라도 쓰지만(그래서 Design보다 먼저 쓴다), **기술 시나리오**(경합·복구·트랜잭션 경계 등)는 설계를 알아야 구체화된다. 설계가 그런 시나리오를 드러내면 Scenarios 산출물에 보강한다.

순서가 이렇게 정해진 이유: **검증이 설계를 끌고 가야 하고, 설계가 검증을 정해선 안 된다.**

### 재진입 — 한 세션에 다 끝내지 않아도 된다

명세 묶음은 며칠에 걸쳐 오갈 수 있다. 그래서 이 skill은 **중간부터 재개**할 수 있다.

- 시작할 때 **진행 상태를 먼저 확인한다**: 작업 공간(worktree·브랜치)이 이미 있는지, spec 폴더와 `workflow-checklist.json`이 있는지, 인터뷰 기록(`.spec-harness/run/interview-*.md`)이 남아 있는지.
- checklist가 있으면 **`completed`가 아닌 첫 단계부터** 이어간다. 이미 끝낸 단계를 다시 돌리지 않는다.
- 사용자가 특정 단계를 다시 하자고 하면(예: "다시 구체화하자") **그 단계로 되돌아가되, 되돌아간다는 사실과 그 뒤 단계가 다시 열린다는 것을 알린다**(예: Clarify로 돌아가면 Scenarios·Design을 다시 확인해야 한다).
- 동결 이후(Design 통과 후) 요구를 바꾸려면 **명세 묶음으로 되돌아가는 것이 정상 경로**다. 실행 중에 spec을 몰래 고치지 않는다.

**Stage 8(Execution) 실행은 dynamic workflow(`/spec-harness:execute`)를 기동해 수행한다.**
preflight가 phase index.json을 읽어 workflow 인자를 만들고, workflow가 step마다
developer→reviewer→committer→recorder 서브에이전트를 돌린 뒤 finalize까지 자동으로 완주한다.

## 용어

작업 단위의 위계를 고정한다.

- **spec**: 최상위 작업 단위. 하나의 `spec.md`(확정·동결된 명세)가 정점이고, `<SPEC_ROOT>/<spec-name>/` 폴더 하나가 한 spec이다. 리팩터링·버그픽스·기능 추가 등 "한 덩어리 작업" 하나가 한 spec.
- **phase**: spec 안에서 "그 단위로 한 번 통합·검증할 가치가 있는 덩어리". 기본은 spec당 1개(`1-main`), 강한 선후 의존·중간 검증 가치가 있을 때만 여러 개.
- **step**: phase 안의 구현 작업 단위. **커밋 1개**에 대응하며 자기완결적 AC를 가진다. Stage 8(Execution)에서 workflow가 실행한다.

또 **Stage**(워크플로 전체의 진행 단계 1~10)와 위 작업 단위는 다른 축이다. 즉 Stage 8(Execution) "안에서" workflow(`/spec-harness:execute`)가 한 spec의 phase·step들을 순차 실행하는 포함 관계다.

---

## 필수 준수 규칙

아래 규칙은 반드시 지켜야 한다.

- **위험영역은 가정하지 않는다.** 위험영역이 spec에서 미확정이면 기본값으로 메우지 않고 마커로 남겨 Clarify(3)에서 사용자와 확정한다. 위험영역 마커가 남아 있으면 Scenarios(4)로 넘어가지 않는다. Clarify는 이 마커들을 5개 질문 한도·deferral에서 면제해 끝까지 묻는다.
- 이 skill을 사용하는 작업에서는 `phases`가 준비된 이후의 기본 구현 경로를 수동 파일 수정이 아니라 `execute.py` 실행으로 본다.
- 사용자가 명시적으로 `execute.py`를 쓰지 말라고 하지 않은 이상, agent가 직접 구현을 시작하면 안 된다.
- `Implement the plan`은 자동으로 직접 구현을 뜻하지 않는다. `phases` 준비 여부와 실행 승인 여부를 먼저 확인해야 한다.
- Workflow는 spec 레벨 `workflow-checklist.json`(spec 폴더 바로 아래) 하나로 10개 Stage를 추적하며, 다음 Stage로 넘어가기 전 이전 Stage가 모두 `completed`여야 한다. 이 checklist는 Specify(2)에서 `execute.py init-checklist`로 생성한다.
- `harness` 진행 상태를 사용자에게 보고할 때는 1~10번 Workflow 상태 표를 함께 보여준다.
- `Analyze`(7) 통과 후에는 반드시 멈추고 작성된 문서 경로를 사용자에게 보고한 뒤 검토 응답을 기다린다. 바로 `execute.py` 실행 요청으로 넘어가지 않는다.
- `execute.py` 실행 전 반드시 사용자에게 진행 의사를 확인하고, 사용자가 진행을 승인한 뒤에만 실행한다(가벼운 확인 — 별도 Plan Mode·`ExitPlanMode` 절차는 거치지 않는다). 이 게이트는 스크립트가 막지 않으므로 메인 에이전트가 지킨다.
- Stage 8(Execution)에서 연 PR은 **Root Sync(10)가 끝나기 전에 머지하지 않는다.** 먼저 머지되면 루트 문서 갱신과 `_archive` 승격이 날아간다.
- Stage 8(Execution)에서 PR을 연 뒤 메인 에이전트는 멈추고 사용자의 PR Review(9) 검토 완료 신호를 기다린다. "리뷰 코멘트가 아직 없음"은 PR Review 완료가 아니다. PR Review 완료가 확인되기 전에는 Root Sync(10)에 착수하지 않는다.
- Stage 10(Root Sync)는 두 가지를 한다. (1) 루트 문서 갱신 — ADR=append, 스냅샷(architecture/db-schema/api-spec)=overwrite로 동작이 다르다. (2) `_archive` 승격 — 실행 이력을 `execution-history.json`으로 내보낸 뒤, Stage 8에서 커밋해 둔 spec 정본과 함께 `<SPEC_ROOT>/_archive/pr-<번호>-<spec명>/`로 옮겨 같은 PR에 커밋한다(진행 상태·실행 부산물은 추적되지 않아 함께 사라진다). 한 지시로 뭉치지 않는다(`references/stages/root-sync.md`).

---

## Workflow 상태 표

`harness`를 진행하면서 사용자에게 상태를 보고할 때는 아래 표 형식을 사용한다.

| 묶음 | 단계 | Stage | 상태 |
| --- | --- | --- | --- |
| 명세 | 1 | Interview |  |
| 명세 | 2 | Specify |  |
| 명세 | 3 | Clarify |  |
| 명세 | 4 | Scenarios |  |
| 명세 | 5 | Design |  |
| 변환·검증 | 6 | Steps |  |
| 변환·검증 | 7 | Analyze |  |
| 실행 | 8 | Execution |  |
| 실행 | 9 | PR Review |  |
| 실행 | 10 | Root Sync |  |

상태 표는 `workflow-checklist.json`이 있으면 그 값을 기준으로 표시한다. checklist 생성 전에는 현재 대화에서 실제 완료한 Stage만 `✅`로 표시한다.

`execute.py`는 checklist의 Stage 상태를 *자기 판단으로* 갱신하지 않는다(특히 phase 단위인 preflight·finalize는 spec 레벨 Stage를 건드리지 않는다). 대신 Stage 8(Execution)은 **메인이 자동 흐름으로** 갱신한다 — Stage 8 진입 시 `set-stage … in_progress`, phase 루프를 다 돈 뒤 `set-stage … completed`를 자동으로 호출한다(사람이 단계마다 지시하지 않는다). Stage 1~6은 진행하며 작성하고, Stage 7(Analyze)은 `close-analyze`가 검사한 뒤 닫는다. Stage 9·10은 리뷰 결과·승격 완료 등 사람 판단이 필요한 시점에 `set-stage`로 갱신한다.

---

## 자리표시자

이 문서의 `<...>`는 실제 값으로 치환해 쓴다.

- **`<SPEC_ROOT>`** — spec 작업 공간이 사는 곳. 저장소 설정(`.spec-harness/config.json`)의 `spec_root`가 있으면 그 값, 없으면 `docs/specs`.
- **`<SKILL_DIR>`** — 이 스킬(run)의 base directory 절대경로(스킬이 호출될 때 함께 주어진다).
- **`<PLUGIN_DIR>`** — 이 플러그인의 루트. `<SKILL_DIR>`에서 두 단계 위(`skills/run` → 플러그인 루트)다. 방법론 선언은 `<PLUGIN_DIR>/methodologies/<이름>/manifest.yaml`에 있다.
- **`<TEMPLATE_DIR>`** — spec 문서 템플릿 폴더. 저장소 설정의 `template_dir`가 있고 그 경로가 실제로 있으면 그것을, 없으면 `<SKILL_DIR>/templates/spec/`을 쓴다.
- **`<spec-name>`** — 이번 작업의 spec slug.

## 먼저 읽을 것

항상 먼저 아래를 읽는다.

- `CLAUDE.md`
- 저장소가 지정한 규칙 문서(설정 `.spec-harness/config.json`의 `rule_docs`·`commit_rule_docs`)

그 다음 현재 작업 대상 spec 문서를 먼저 읽는다.

- `spec.md` — 요구·완료 기준 (항상)
- `plan.md` — 총괄 설계서·Phase 구성
- `scenarios.md` — 확정된 검증 대상 (있으면)
- `data-model.md` — 엔티티·식별·**상태 전이** (있으면. 위험영역이다)
- `architecture.md`·`db-schema.md`·`api-spec.md`·`adr.md` (작성된 것)

모두 `<SPEC_ROOT>/<spec-name>/` 아래에 있다. 이 목록은 `build-context`가 구현 단계에서 주입하는 것과 같다 — 한쪽만 늘리면 갈라진다.

spec 문서와 `phases` 문서로 부족한 공통 맥락이 있을 때만 설정의 `reference_docs`에 나열된 문서를 추가로 읽는다.
작업 범위에 직접 연결된 코드와 테스트도 함께 읽는다.

> **누가 어느 문서를 쓰나:** Specify가 `spec.md`, Clarify가 `spec.md`의 `## Clarifications`, Design(5)이 `architecture.md`·`api-spec.md`·`db-schema.md`를, Steps(6)이 phase·step 파일을 만든다. `adr.md`는 한 단계에 묶지 않고 **결정이 생기는 곳(주로 Clarify·Design)에서 그때그때 append**한다.

> **문서 용어(전 산출물 공통):** harness가 만드는 모든 문서(`spec.md`·`plan.md`·설계 문서·`phases/**/step<N>.md`)는 다음을 따른다 — 표준 기술 용어는 그대로 쓰되 일반적이지 않은 비유·축약이나 난해한 표현은 쉽게 풀어써 명료하게 다듬는다. 이 규칙은 spec.md 템플릿 작성 규칙(근원), Clarify의 점검 항목(spec 게이트), Analyze 검출 패스(전 문서 게이트)에서 각각 강제된다.

---

## 방법론 (opt-in)

이 하네스의 10개 Stage 흐름과 게이트는 **방법론 무관 코어**다. 그 위에 저장소가 "일하는 방식"을 얹을 수 있다.

**켜는 방법**: 설정(`.spec-harness/config.json`)의 `methodologies`에 이름을 넣는다(예: `["ddd", "bdd"]` — 여러 개를 함께 켤 수 있다).
목록이 비어 있거나 설정이 없으면 **코어만 돈다** — 그게 정상 동작이며, 방법론을 켜라고 권하지 않는다.

**적용 절차 (Stage 1 시작 시 한 번)**:
1. 설정의 `methodologies`를 읽는다. 비어 있으면 이 절을 건너뛰고 코어 흐름만 진행한다.
2. 각 이름에 대해 `<PLUGIN_DIR>/methodologies/<이름>/manifest.yaml`을 `Read`한다. 없으면 사용자에게 알리고
   그 방법론은 적용하지 않는다(임의로 대체하지 않는다).
3. 각 manifest의 `min_engine_version`이 **이 플러그인 버전보다 높으면 그 방법론은 적용하지 않고** 사용자에게
   알린다(플러그인 버전은 `<PLUGIN_DIR>/.claude-plugin/plugin.json`의 `version`). 그 방법론이 쓰는 연결
   지점이 아직 없어서, 선언만 읽고 진행하면 요구가 조용히 빠진다.
4. 여러 개면 각 manifest의 `requires`(선행 필요)·`conflicts_with`(동시 사용 불가)를 대조한다. 충돌하면
   **진행하지 않고** 사용자에게 무엇이 충돌하는지 알리고 어느 쪽을 끌지 확인한다.
5. 아래 표대로 각 단계에 얹는다.

| manifest 항목 | 어디에 얹히나 |
| --- | --- |
| `requires_in_spec` | **Specify(2)**: 그 산출물을 spec에 요구한다. 없으면 미확정 마커로 남겨 Clarify(3)에서 확정한다. 시나리오 산출물이면 Scenarios(4)가 그 형식을 따른다. Analyze(7)가 실제로 있는지 확인한다. |
| `agents` (`consult` 모드) | **Specify(2)·Clarify(3)·Scenarios(4)·Design(5)**: 설계 판단이 필요할 때 `invoke_as` 이름으로 `Task`를 띄워 함께 잡는다. |
| `templates` | **Scenarios(4)·Design(5)**: `<PLUGIN_DIR>/methodologies/<이름>/templates/` 아래 템플릿을 그 spec의 시나리오·설계 문서로 쓸 수 있다. |
| `requires_in_steps` | **Steps(6)**: 그 요구를 step 문서 본문에 **문장으로** 적는다. 구현하는 agent가 읽는 것은 step 문서이므로, 방법론 이름만 알려주면 구현 단계에서 지켜지지 않는다. Analyze(7)가 실제로 반영됐는지 확인한다. |
| `adds_checks` | **Analyze(7)**: 검사관들의 검출 항목에 그 검사들을 **추가**한다. 각 검사관에게 활성 방법론 이름과 manifest 경로를 함께 넘기고, 각자 자기 관점에 해당하는 규칙만 적용한다. |
| `agents` (`review` 모드) | **Analyze(7)**: 검사관 여섯과 별도로 그 agent를 띄워 방법론 관점 검토 리포트를 받는다. |

**불변식 — 방법론은 자기 검사를 더할 수 있을 뿐, 코어 게이트를 끄지도 느슨하게 하지도 못한다.**
특히 위험영역 확정, 실행 전 검사, AC 통과, 사람 승인 지점은 어떤 방법론도 무력화할 수 없다. manifest가
그런 것을 요구하면 따르지 않고 사용자에게 알린다.

`enforcement: instance-defined`인 검사는 **무엇을 검사할지만** 방법론이 정하고, 그것을 무엇으로 강제하는지
(정적 분석·아키텍처 테스트 등)는 저장소가 정한다. 저장소에 그 수단이 없으면 검사는 리포트로만 남는다.

---

## Workflow

각 단계의 절차는 `references/stages/`에 단계마다 한 파일로 있다. **단계에 들어갈 때마다 그 파일을 Read한 뒤 진행한다.** 읽지 않으면 그 단계의 산출 형식과 게이트가 빠진다.

### 1. Interview

spec이 없을 때 무엇을 만들지 질문으로 확정한다. worktree와 `spec.md`는 아직 만들지 않는다.

- 산출: `.spec-harness/run/interview-<날짜시각>.md`
- 절차: `references/stages/interview.md`

### 2. Specify

작업 공간과 checklist를 만들고, 빈칸이 마커·가정으로 드러난 `spec.md` 초안을 쓴다.

- 산출: 작업 공간, `workflow-checklist.json`, `spec.md`
- 절차: `references/stages/specify.md`

### 3. Clarify

점검 항목으로 `spec.md`를 훑어 모호함을 한 번에 하나씩 묻고 답을 즉시 반영한다. 위험영역은 끝까지 묻는다.

- 산출: `spec.md`의 `## Clarifications`와 반영된 본문
- 절차: `references/stages/clarify.md`

### 4. Scenarios

요구·완료 기준마다 무엇을 어떻게 확인할지 붙이고 `불변`/`유동`을 표시한다.

- 산출: `spec.md`의 확인 방법 또는 `scenarios.md`
- 절차: `references/stages/scenarios.md`

### 5. Design

설계 문서와 phase 구성을 정한다. 이 단계를 닫으면 요구와 `불변` 시나리오가 동결된다.

- 산출: `plan.md`와 필요한 하위 설계 문서
- 절차: `references/stages/design.md`

### 6. Steps

phase를 step으로 나누고 실행 파일을 만든다.

- 산출: `phases/index.json`, `phases/<phase>/index.json`, `phases/<phase>/step<N>.md`
- 절차: `references/stages/steps.md`

### 7. Analyze

검사관 여섯이 문서를 읽기 전용으로 점검하고, 항목별로 처리한 뒤 `close-analyze`로 닫는다. 통과 후 반드시 멈춘다.

- 산출: `analysis.json`
- 절차: `references/stages/analyze.md`

### 8. Execution

명세를 커밋하고 dynamic workflow로 phase를 완주한 뒤 PR을 연다.

- 산출: step별 커밋, PR
- 절차: `references/stages/execution.md`

### 9. PR Review

사용자가 PR을 검토한다. 완료 신호를 받기 전에는 Root Sync에 착수하지 않는다.

- 절차: `references/stages/pr-review.md`

### 10. Root Sync

루트 문서를 갱신하고, 실행 이력을 내보낸 뒤 spec 정본을 `_archive`로 옮긴다.

- 산출: 갱신된 루트 문서, `<SPEC_ROOT>/_archive/pr-<번호>-<spec명>/`
- 절차: `references/stages/root-sync.md`
