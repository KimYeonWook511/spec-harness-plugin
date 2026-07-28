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
| Root Sync(10) | draft 해제 | 1~10이 모두 `completed`이고 `_archive` 승격본이 커밋됐다 | `ready-pr`가 파일·git으로 판정하고 막는다 |
| Root Sync(10) | 이른 머지 차단 | Root Sync가 안 끝난 spec이 있으면 Bash로 머지·draft 해제를 하지 못한다 | `merge-hook`이 판정하고 막는다 |

표에 나온 이름:

| 이름 | 무엇 |
| --- | --- |
| `preflight` · `verify-ac` · `close-analyze` · `ready-pr` | `<SKILL_DIR>/scripts/execute.py`의 서브커맨드. 파일·명령을 실제로 보고 판정한다 |
| `execute.js` | `<PLUGIN_DIR>/workflows/execute.js`. step 실행을 조율하며 조건이 어긋나면 다음 단계를 부르지 않는다 |
| `merge-hook` | `<PLUGIN_DIR>/skills/run/scripts/hooks/block_early_merge.py`. PreToolUse로 Bash 명령을 보고 이른 머지를 거절한다 |
| 검사관 여섯 | `spec-harness:analyzer-*`. Analyze의 관점별 전용 에이전트로, 읽기 전용이라 판정만 하고 스스로 막지 못한다 |
| `reviewer` | 전용 에이전트 `spec-harness:reviewer`. 읽기 전용이라 판정만 한다 |
| 메인 에이전트 | 이 skill을 실행하는 에이전트 |

**모델 판단이 하나도 끼지 않는 게이트는 다섯이다** — 실행 전 검사, step 형식, 분석 최신, step 3회 시도 한도, 중단된 step 재실행. 이 다섯은 스크립트가 파일과 자기 데이터(checklist·문서 해시·파서 결과·시도 횟수·step status)만 보고 판정한다.

Root Sync의 두 게이트는 스크립트와 hook이 막지만 통과 조건에 checklist 상태가 들어가고, 그것은 메인이 찍는다. 다만 `_archive` 승격본이 실제로 커밋됐는지는 git으로 확인하므로 **문서 승격을 건너뛴 채 draft를 벗기는 것은 막힌다.**

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
- Workflow는 spec 레벨 `workflow-checklist.json`(spec 폴더 바로 아래) 하나로 10개 Stage를 추적하며, 다음 Stage로 넘어가기 전 이전 Stage가 모두 `completed`여야 한다. 이 checklist는 Specify(2)에서 worktree를 만들 때 템플릿의 `workflow-checklist.json`을 복사해 생성한다.
- `harness` 진행 상태를 사용자에게 보고할 때는 1~10번 Workflow 상태 표를 함께 보여준다.
- `Analyze`(7) 통과 후에는 반드시 멈추고 작성된 문서 경로를 사용자에게 보고한 뒤 검토 응답을 기다린다. 바로 `execute.py` 실행 요청으로 넘어가지 않는다.
- `execute.py` 실행 전 반드시 사용자에게 진행 의사를 확인하고, 사용자가 진행을 승인한 뒤에만 실행한다(가벼운 확인 — 별도 Plan Mode·`ExitPlanMode` 절차는 거치지 않는다). 이 게이트는 스크립트가 막지 않으므로 메인 에이전트가 지킨다.
- Stage 8(Execution)에서 PR은 **draft로 연다.** GitHub이 draft PR의 머지를 거부해, Root Sync(10) 전에 머지되어 루트 문서 갱신과 `_archive` 승격이 날아가는 것을 막는다. draft를 벗기는 것은 Root Sync 끝의 `ready-pr`뿐이다.
- Stage 8(Execution)에서 PR을 연 뒤 메인 에이전트는 멈추고 사용자의 PR Review(9) 검토 완료 신호를 기다린다. "리뷰 코멘트가 아직 없음"은 PR Review 완료가 아니다. PR Review 완료가 확인되기 전에는 Root Sync(10)에 착수하지 않는다.
- Stage 10(Root Sync)는 두 가지를 한다. (1) 루트 문서 갱신 — ADR=append, 스냅샷(architecture/db-schema/api-spec)=overwrite로 동작이 다르다. (2) `_archive` 승격 — spec 정본(진행 상태·실행 부산물을 뺀 모든 문서)을 `<SPEC_ROOT>/_archive/pr-<번호>-<spec명>/`로 복사해 같은 PR에 커밋한다(진행 상태·실행 부산물은 휘발로 남김). 한 지시로 뭉치지 않는다(아래 Stage 8 참고).

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
- **`<TEMPLATE_DIR>`** — 쓸 템플릿 폴더(아래 "템플릿 폴더" 설명 참고).
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

### 1. Interview

**무엇을 만들지**를 질문으로 확정하는 단계다. 먼저 읽어서 답할 수 있는 것을 채우고, 남은 모호함을 사용자에게 묻는다. 아직 worktree도 `spec.md`도 만들지 않는다(스캐폴딩은 Specify(2)에서 한다).

이 단계와 Clarify(3)는 둘 다 질문하지만 대상이 다르다 — **Interview는 spec이 없을 때 "무엇을 만들지"를, Clarify는 spec 초안의 빈칸을** 다룬다.

#### 먼저 읽기 (묻기 전에)

이미 답할 수 있는 것을 묻지 않기 위해, 질문 전에 읽는다.

- `CLAUDE.md`를 읽고 현재 Repo 규칙을 파악한다.
- **활성 방법론을 확인한다** — 설정의 `methodologies`를 읽고, 있으면 각 manifest를 로드한다(위 "방법론(opt-in)" 절차). 이후 단계가 그 선언을 따른다. 비어 있으면 코어만 진행한다.
- **외부 기능 명세(PRD 등)가 있으면 읽는다** — 있으면 그것이 출발점이고, **읽었어도 부족한 부분은 계속 묻는다**(명세가 있다는 것이 확정됐다는 뜻은 아니다). 없으면 대화가 출발점이다. 리팩터링·버그 수정·탐색적 작업은 사전 명세가 없는 게 정상이다.
- 작업 범위에 직접 연결된 **코드와 테스트를 읽어** 현재 구조와 변경 범위를 파악한다. 기존 코드를 고치는 작업이면 아래 채점에 `기존 맥락` 축이 추가된다.
- **재개 확인**: 진행 중인 인터뷰 기록(`.spec-harness/run/interview-*.md`)이나 이미 만들어진 worktree·`spec.md`가 있으면 그것을 읽고 **이어서** 진행한다(아래 "재진입").

#### 모호함 채점

네 축으로 명확도(0~1)를 매기고, **명확도의 가중 합을 1에서 뺀 값**을 모호함으로 본다.

```
모호함 = 1 − Σ(축 명확도 × 가중치)
```

| 축 | 가중치 | 무엇을 보나 |
| --- | --- | --- |
| 목표 | 0.40 | 무엇을 왜 만드나. 한 문장으로 말할 수 있나. 누가 쓰나. 이 작업이 아닌 것은 무엇인가. |
| 제약 | 0.30 | **절대 하면 안 되는 것**은 무엇인가. 바꾸면 안 되는 기존 동작·계약. 성능·운영·보안 제약. |
| 완료 기준 | 0.30 | 무엇을 보면 됐다고 할 수 있나. 어떻게 확인하나. 엣지·실패 경우는 어떻게 되어야 하나. |
| 기존 맥락 | 0.15 | (기존 코드를 고칠 때만) 지금 어떻게 동작하나. 무엇을 재사용·대체하나. 영향 범위는 어디까지인가. |

- **`기존 맥락` 축이 활성되면 네 축의 가중치를 합이 1이 되도록 다시 나눈다**(목표 0.35 · 제약 0.25 · 완료 기준 0.25 · 기존 맥락 0.15). 합이 1을 넘으면 점수가 뜻을 잃는다.
- 축마다 점수를 매길 때 **아래 기준을 쓴다**(감으로 매기면 회차마다 흔들린다):
  - **0.0** — 아무 정보 없음. 물어봐야 한다.
  - **0.3** — 방향만 있고 대상·값이 없다("빠르게", "안정적으로", "적절히").
  - **0.6** — 대상은 정해졌지만 경계·예외가 안 정해졌다.
  - **1.0** — 이 축으로는 더 물을 것이 없다. 판단이 갈릴 여지가 없다.
- **읽어서 알아낸 것도 점수에 반영한다.** 사용자가 말하지 않았어도 코드·명세에서 확정된 것은 명확한 것이다.

#### 질문 루프

- 가중치가 큰 축부터(목표 → 제약 → 완료 기준 → 기존 맥락) 그 축의 점수를 올리는 질문을 한다.
- **한 번에 하나씩 묻는다.** 답을 받으면 그 축 점수를 갱신한다.
- 한 라운드(축 하나를 훑음)가 끝나면 **점수 표와 남은 모호함을 보여주고, 계속할지 사용자에게 확인한다.** 회차 상한은 두지 않는다 — 끝낼지는 사용자가 정한다.
- **답을 대신 만들지 않는다.** 모르는 것은 가정으로 메우지 말고 질문으로 남긴다. 사용자가 "적당히 해줘"라고 하면, 그 결정이 무엇을 뜻하는지 짚고 **가정으로 명시**한 뒤 넘어간다.
- **종료 권고는 모호함 0.2 이하**일 때 한다. 다만 이 수치는 **권고**이며, 사용자가 그 전에 끝낼 수 있다.
- **단, 위험영역의 미확정은 수치·사용자 판단과 무관하게 남길 수 없다.** 그 부분은 끝까지 묻고, 정말 미정이면 "무엇이 미정인지"를 spec에 미확정 마커로 넘긴다 — 임의 가정으로 메우지 않는다.

#### 산출

`.spec-harness/run/interview-<날짜시각>.md` 에 기록한다(휘발 폴더라 커밋되지 않는다. Specify(2)가 작업 공간을 만들 때 spec 폴더로 옮긴다).

```markdown
# 인터뷰 기록 — <작업 한 줄 설명>
- 일시 / 대상 저장소 상태(신규 작업 · 기존 코드 수정)
- 축 점수: 목표 0.XX · 제약 0.XX · 완료 기준 0.XX · 기존 맥락 0.XX → 모호함 0.XX

## 확정된 것
- <질문 → 답 → 그래서 무엇이 정해졌나>

## 드러난 가정
- <사용자가 명시하지 않았지만 이렇게 간주한 것. Specify가 spec의 가정 절로 옮긴다.>

## 남은 미확정
- <아직 못 정한 것. 위험영역이면 그렇게 표시한다.>
```

이 기록이 Specify(2)의 입력이다. **드러난 가정과 남은 미확정은 spec 초안에 마커로 옮겨져** Clarify(3)에서 다시 다뤄진다.

---

### 2. Specify

이 단계는 작업의 *무엇을·왜*를 확정하고 `spec.md` **초안**을 쓴다. 그 전에 **작업 공간(worktree)과 진행 추적(checklist)을 먼저 만든다** — 이후 모든 문서·구현이 이 worktree 안에서 산다.

#### 작업 공간 준비 (Specify 맨 앞 — 한 번)

1. **slug·type 확정**: 사용자의 한 줄 작업 설명에서 `<spec-name>` slug와 작업 종류(type)를 정한다. 종류 값은 설정(`.spec-harness/config.json`)의 `workspace.types`에서 고르고, 그 목록이 비어 있으면 **하네스가 값을 만들지 않고** 최근 브랜치 이름(`git branch -a`)에서 쓰이는 형태를 보거나 사용자에게 짧게 확인한다. spec 내용을 다 채우기 전에 *이름만* 먼저 정하는 것이다.
2. **작업 공간 생성·이동**: 설정의 `workspace`를 따른다.
   - `mode: "worktree"`(기본) — `worktree_pattern`이 정한 디렉터리에 워크트리를 만들고 그 안으로 이동한다. 메인 체크아웃을 건드리지 않아 작업이 섞이지 않는다.
   - `mode: "branch"` — 현재 체크아웃에서 브랜치만 새로 만들어 작업한다.
   - 브랜치 이름은 `branch_pattern`, 분기 기준은 `base_ref`를 쓴다. `base_ref`가 없으면 **저장소의 기본 브랜치**를 쓴다(하네스가 특정 브랜치 이름을 가정하지 않는다).
   - 이름 형식의 `<type>`·`<name>`은 위에서 정한 종류·slug로 치환한다.

   만든 뒤 그 안(또는 그 브랜치)으로 이동하고, 이동 직후 `pwd`와 `git branch --show-current`로 **의도한 위치·브랜치인지 반드시 확인한다.** 이후 모든 문서 작성·`execute.py` 실행은 이 작업 공간의 루트 기준이다.
3. **스캐폴딩(checklist 생성)**: worktree 안에 `<SPEC_ROOT>/<spec-name>/` 폴더를 만들고, 템플릿 폴더(`<TEMPLATE_DIR>` — 아래 참고)의 `workflow-checklist.json`을 `<SPEC_ROOT>/<spec-name>/workflow-checklist.json`으로 복사한다. 이 시점에 10개 Stage 진행 추적 checklist가 존재한다(실행 게이트가 이를 읽는다). **설계 문서(plan·architecture·data-model 등)는 지금 복사하지 않는다 — Design(5)에서 필요한 것만 템플릿 폴더에서 꺼내 만든다.** `spec.md`도 아래에서 새로 만든다.

> worktree·checklist는 spec당 한 번만 만든다. 재실행이면 이미 있으므로 건너뛴다.

> **템플릿 폴더 (`<TEMPLATE_DIR>`)**: 저장소 설정(`.spec-harness/config.json`)에 `template_dir`가 있고 그 경로가 실제로 있으면 그것을 쓰고, 없으면 이 스킬이 싣고 있는 `<SKILL_DIR>/templates/spec/`을 쓴다.

#### spec.md 초안 작성

**핵심 방식: 초안을 먼저 뽑는다.** 길게 대화한 뒤 받아쓰는 게 아니라, 가진 입력으로 `spec.md` 템플릿(`<TEMPLATE_DIR>/spec.md`)을 복사해 *지금* 채운다. 긴 질의응답은 이 단계가 아니라 Clarify(3)에서 일어난다. Specify의 목표는 "완성된 spec"이 아니라 **"빈칸이 마커·가정으로 드러난 초안"**이다.

> **활성 방법론의 요구 산출물**: 각 manifest의 `requires_in_spec`에 적힌 산출물을 이 spec에 포함시킨다. 지금 채울 수 없으면 임의로 메우지 말고 **미확정 마커로 남겨** Clarify(3)에서 확정한다. 그 산출물의 형식이 방법론 템플릿에 있으면 그것을 쓴다. 설계 판단이 필요하면 그 방법론의 `consult` 모드 agent를 `Task`로 띄워 함께 잡는다(예: ddd → `spec-harness:domain-expert`에 `consult 모드`임을 명시).

#### 입력 (어디서 출발하나)

- **외부에 기능 명세가 있으면** 그 조각을 참고해 이 spec 범위로 좁힌다.
- **없으면** 사용자와의 대화를 출발점으로 삼는다. 명세가 없는 것은 정상이다 — 리팩터링·버그 수정·기술 부채 정리·탐색적 작업은 사전 명세 자체가 없다.

#### 작성 규칙 (spec.md 템플릿의 작성 규칙을 따른다)

`spec.md` 템플릿 상단의 작성 규칙을 그대로 적용한다. 요지:

- **추측 금지.** 대화에서 명시되지 않은 결정을 그럴듯하게 지어내 채우지 않는다. 안 정해진 것은 둘 중 하나로 *드러낸다*:
  - 합리적 기본값이 있으면 → 그 값을 적되 `## 가정(Assumptions)`에 명시한다.
  - 기본값이 없으면 → `[NEEDS CLARIFICATION: 질문]` 마커로 남긴다(Clarify에서 해소).
- **위험영역은 기본값 금지.** 결제·인증·데이터 모델·상태 전이가 미확정이면 가정으로 메우지 않고 **반드시 마커**로 남긴다.
- **누락 금지.** 필수 섹션은 비우지 않는다. 해당 없으면 "해당 없음"이라고 적는다(빈 섹션이 곧 미검토 신호).
- 요구사항·완료 기준에는 ID(`FR-001`·`SC-001`)를 붙인다(Analyze가 이 ID로 커버리지를 추적).

#### 모호함을 마커로 남길 신호

아래에 해당하면 임의로 확정하지 말고 `[NEEDS CLARIFICATION]` 마커로 남긴다(Clarify에서 사용자와 해소).

- 요구사항이 둘 이상으로 해석될 수 있을 때
- 설계 선택이 결과에 큰 영향을 줄 때
- 외부 인증·API 키·수동 설정 등 사용자 개입이 필요할 때
- 기존 구조나 규칙과 충돌 가능성이 있을 때

산출: `<SPEC_ROOT>/<spec-name>/spec.md` (배경·시나리오·범위·요구사항·데이터 모델·완료 기준·제약·가정).

#### 작성 전 루트 문서 정합성 확인 (필수)

스펙 방향을 확정하기 전에, 작업이 기존 결정·원칙과 충돌하는지 **agent가 먼저 확인**한다. 임의로 방향을 정한 뒤 "충돌 지점을 검토해 달라"고 사용자에게 떠넘기지 않는다. 충돌이 발견되면 그 지점을 마커로 남기거나, 아래 제안 형식으로 사용자에게 방향을 묻는다.

1. **항상**: `docs/adr/index.md`(루트 ADR 색인)를 읽고, "주요 결정 키워드"를 훑어 이 작업과 관련된 ADR을 식별한 뒤 해당 항목을 확인한다.
2. **영역별**: 작업이 건드리는 영역에 해당하는 루트 문서를 추가로 확인한다.

| 작업이 건드리는 것 | 확인할 루트 문서 |
| --- | --- |
| 설계 방식·정책 (어떻게 풀까) | 루트 ADR (+ 관련 spec adr) |
| 구조·레이어·책임 배치 | `docs/architecture.md` |
| 데이터 모델·테이블·제약 | `docs/db-schema.md` |
| API 추가·변경 | `docs/api-spec.md` |

3. **제안 형식**: 확인 결과를 아래 형식으로 제시한다. 이 형식은 agent가 문서를 실제로 확인했다는 근거이며, 사용자는 정합 라벨만 보고 판단할 수 있다.

```
## 제안

관련 결정/문서:
- ADR-020 (cross-aggregate ID 참조) — 이 작업이 새 연관을 추가하므로 관련
- architecture.md (payment 도메인 책임) — 결제 상태를 건드리므로 관련

선택지:
A. <방식 A> — ADR-020 일치. 추천.
B. <방식 B> — ADR-020 위반. 채택하려면 ADR 갱신 필요.

→ 어느 방향으로 진행할까요?
```

- 기존 결정과 충돌하는 방향은 반드시 "위반/갱신 필요"로 명시한다.
- ADR이 많으므로 전문을 모두 읽지 말고, 색인으로 관련 항목을 식별한 뒤 그 항목만 깊이 읽는다.

#### 출구

초안이 서면(템플릿이 채워지고 빈칸이 마커·가정으로 드러나면) Clarify(3)로 이어간다. 초안 마커가 하나도 없어도 Clarify를 건너뛰지 않는다 — 마커는 초안 작성자가 잡은 것뿐이라, Clarify에서 점검 항목 전체를 최소 1회 훑어 표시되지 않은 모호함을 확인한 뒤에야 통과 여부를 정한다.

---

### 3. Clarify

`spec.md`의 모호함을 사용자와의 대화로 해소하는 단계다. **정해진 점검 항목으로 spec을 훑어 빈칸을 잡고, 최대 5개를 한 번에 하나씩 묻고, 답을 즉시 spec에 반영·기록**한다. 그 위에 **위험영역 불가침** 원칙을 게이트로 얹는다.

> 이 단계는 스크립트가 아니라 LLM 프롬프트로 동작한다. 메인 스레드에서 사용자와 직접 Q&A하며(서브에이전트 아님), 답을 받을 때마다 `spec.md`를 원자적으로 저장한다.

#### 시작 시

1. `spec.md`를 읽는다. 없으면 Specify(2)를 먼저 하라고 안내하고 여기서 spec을 새로 만들지 않는다.
2. **위험영역 목록을 확인한다.** 위험영역과 그 면제 규칙을 이 단계가 강제한다. 저장소가 규칙 문서로 위험영역을 따로 정했으면 그것도 포함한다.

#### 모호함 스캔 (점검 항목)

아래 고정 카테고리로 `spec.md`를 훑어, 각 항목을 **Clear / Partial / Missing**으로 내부 분류한다(coverage map). "agent가 모호하다고 느꼈나"가 아니라 "이 칸이 채워졌나"가 판정 기준이다.

- 기능 범위·동작 (목표/비목표, 성공 판정, 명시적 out-of-scope)
- 도메인·데이터 모델 (엔티티, 관계, **식별·유일성 규칙**, **상태 전이/lifecycle**)
- 상호작용·UX 흐름 (액터/역할, 핵심 동선, 빈/에러/로딩 상태)
- 비기능 품질 (성능, 확장성, 신뢰성, 관측성, **보안·프라이버시 authN/Z**, 컴플라이언스)
- 통합·외부 의존 (외부 서비스/API와 실패 모드, 데이터 포맷, 프로토콜/버전 가정)
- 엣지·실패 처리 (부정 시나리오, rate limit, 동시 편집 등 충돌 해소)
- 제약·트레이드오프 (기술 제약, 명시적 트레이드오프/기각 대안)
- 용어 일관성·쉬운 표현 (표준 용어, 회피할 동의어 + 풀어써야 할 비표준 비유·축약이나 난해한 표현이 남아 있는가)
- 완료 신호 (완료 기준의 검증 가능성, 측정 가능한 DoD)
- 기타·placeholder (TODO 마커, "robust"·"직관적" 등 정량화 안 된 모호 형용사)

Partial/Missing 항목은 질문 후보로 올리되, 다음이면 **뺀다**: 명확히 해도 구현·검증 전략이 실질적으로 안 바뀌거나, 설계(Design) 단계로 미루는 게 나은 경우.

#### 질문 큐 산정 (한 패스에 ≤5, 단 위험영역은 면제)

후보를 우선순위 큐로 만든다. 규칙:

- **일반 모호함**: 한 패스에 최대 5개. 5개를 넘으면 (영향 × 불확실성) 상위 5개만. 한 번에 다 보여주지 않는다.
- 각 질문은 객관식(2~5개 상호배타 옵션) 또는 단답(≤5단어)으로 답할 수 있어야 한다.
- 아키텍처·데이터 모델·태스크 분해·테스트 설계·UX·운영·컴플라이언스에 실질 영향을 주는 것만.
- **위험영역 면제 (원칙 강제)**: 위험영역 4종에 걸린 미확정 마커는 위 5개 한도와 deferral 대상에서 **제외된다.** 일반 모호함이 5개를 채워도, 위험영역 질문은 항상 큐에 남아 반드시 묻는다. 우선순위에 밀려 Deferred로 가지 않는다.

#### 질문 루프 (한 번에 하나)

- **정확히 한 질문씩** 제시한다. 다음 큐 질문을 미리 노출하지 않는다.
- 객관식: 최적 옵션을 먼저 분석해 **추천 옵션 + 이유(1~2문장)**를 맨 위에 두고, 그 아래 옵션 표를 낸다. 사용자는 옵션 문자로 답하거나, "추천"으로 추천을 수락하거나, 직접 단답할 수 있다.
- 단답: **제안 답 + 근거**를 먼저 주고, ≤5단어로 답하게 한다.
- 사용자가 "추천/yes"로 답하면 직전 추천을 답으로 쓴다. 모호하면 같은 질문 내에서 한 번 더 확인한다(질문 수에 추가 안 됨).
- **종료 조건**: 치명 모호함이 다 풀렸거나 / 사용자가 "그만·됐다" 신호 / 5개에 도달. **단, 위험영역 마커가 남아 있으면 종료하지 않는다**(면제 항목이라 5개 한도와 무관하게 끝까지 묻는다).

#### 답마다 즉시 반영·기록 (원자적)

수락된 답 하나마다:

1. `## Clarifications`가 없으면 만들고(개요 섹션 바로 뒤), 그 아래 `### Session YYYY-MM-DD`를 둔다.
2. `- Q: <질문> → A: <최종 답>` 한 줄을 추가한다.
3. 곧바로 해당 본문 섹션에 반영한다 — 기능 모호함→요구사항, 데이터/엔티티→데이터 모델, 비기능→완료 기준(모호 형용사를 수치로), 엣지→Edge Cases, 용어→전체 통일. 답이 기존 모호 문장을 무효화하면 그 문장을 **교체**한다(모순 잔존 금지).
4. **반영 직후 `spec.md`를 원자적으로 저장**한다(컨텍스트 유실 대비). 무관한 섹션은 재정렬하지 않는다.

#### 검증 (매 저장 + 최종)

- Clarifications에 수락 답당 정확히 한 줄(중복 없음). 한 패스에서 수락한 일반 질문은 5개 이하다(위험영역 면제분 제외). 누적 줄 수는 패스 수만큼 5를 넘을 수 있다 — 누적 총량은 검증하지 않는다.
- 새 답이 해소하려던 모호 placeholder가 본문에 남아 있지 않다. 모순되는 옛 문장 없음.
- 새로 추가된 heading은 `## Clarifications` / `### Session YYYY-MM-DD`만.
- 용어 일관성 유지.

#### 반복·종료 (사용자 판단으로 닫는다)

질문 루프의 종료 조건은 그 *패스*만 닫는다. Stage를 닫으려면 아래를 지킨다.

- **점검 항목 전체를 최소 1회 훑기 전에는 닫기를 제시하지 않는다.** 초안 마커를 다 풀었어도(또는 애초에 마커가 없어도) 재스캔을 1회 돌린다 — 초안 작성자가 마커로 남기지 못한 위험영역 미확정을 이 재스캔이 잡는다.
- **최소 스캔 이후 매 스캔 후 진행 의사를 묻는다.** agent가 스스로 Stage를 닫지 않는다 — 최소 스캔을 마친 뒤부터 각 패스가 끝날 때 "한 번 더 점검 항목을 훑을지 / 닫고 Scenarios(4)로 갈지"를 물어 방향을 정한다. 한 번에 닫지도, 무한 반복하지도 않는다.
- **종료 기준은 사용자 판단이다.** "모호함 완전 소거"가 아니라 **사용자가 충분히 해소됐다고 판단하는 시점**에 닫는다. 무모호 상태를 종료 조건으로 강제하지 않는다 — Design에서 확정할 계약·구현 세부(DTO 필드명·에러 코드 네이밍·JSON 매핑 방식 등)까지 여기서 붙들지 않는다.
- **위험영역은 사용자 판단과 무관하다(원칙 강제).** 위험영역(결제·인증·데이터 모델·상태 전이) 마커가 하나라도 남으면, 사용자가 "됐다"고 해도 이 Stage를 `completed`로 두지 않는다. 위험영역 마커는 5개 한도·deferral에서 면제되어 반드시 해소되며, 미확정 상태로는 Scenarios(4)로 넘어가지 않는다(실행 게이트가 이를 전제한다).

#### 게이트

- **모호함이 없으면**: 재스캔에서도 새 빈칸이 나오지 않고 사용자가 닫기로 하면, "물을 것 없음(치명 모호함 없음)"으로 통과하고 Scenarios(4) 진행을 권한다. 단 초안 마커만 푼 첫 패스 직후에 곧장 통과시키지 않는다 — 위 재스캔을 먼저 돌린다.
- 일반 모호함이 5개 한도에 걸려 못 푼 게 남으면 Deferred로 명시(위험영역은 Deferred 불가).
- 결정이 생기면 `adr.md`에 그때그때 append 한다.

---

### 4. Scenarios

확정된 요구를 **무엇을 보면 됐다고 할 수 있는가**로 옮기는 단계다. 여기서 정한 것이 step의 Acceptance Criteria가 되고, Analyze가 "요구 ↔ 시나리오 ↔ AC"를 대조하는 기준이 된다.

이 단계가 따로 있는 이유: 코어 게이트는 이미 **step마다 AC 통과를 요구**하고, Analyze는 "AC가 spec과 안 맞음"·"경합 검증 공백"을 검사한다. 그런데 그 AC가 어디서 나왔는지가 명세에 없으면 게이트가 근거 없이 도는 셈이다. 이 단계가 그 근거를 만든다.

#### 코어가 요구하는 것 (방법론 없이도)

`spec.md`의 **기능 요구사항(FR-###) 하나하나와, 확인 가능한 완료 기준(SC-###) 각각에 대해 "무엇을 어떻게 확인하는가"를 붙인다.** 그게 전부다.

- **요구사항과 완료 기준 양쪽에 붙인다.** 완료 기준만 다루면 대부분의 요구사항이 검증 계획 없이 지나간다 — 완료 기준은 원래 적고(작은 작업이면 1~2개) 요구사항은 많다.
- **요구사항 하나에 확인할 경우가 여럿이면 여럿 적는다.** 규칙·제약이 있는 요구사항은 성공 경우 하나로 끝나지 않는다(경계에서 어떻게 되나, 거절되면 상태가 남나).
- 확인할 수 없는 완료 기준은 완료 기준이 아니다 — 측정 가능하게 고치거나 Clarify(3)로 되돌린다. 다만 만들어서 확인할 수 없는 기준(출시 후 지표 등)은 그렇게 밝히고 넘어간다.
- 확인 방법은 개념 수준으로 적는다(어떤 명령으로 돌릴지는 Steps(6)에서 AC로 구체화된다).
- 산출: `spec.md`의 해당 절에 확인 방법을 함께 적거나, 양이 많으면 `scenarios.md`로 분리한다.

> **요구사항과 완료 기준은 서로 다른 축이다.** 요구사항은 "무엇을 할 수 있어야 하나", 완료 기준은 "무엇이 되면 끝인가"다. 확인 경우를 억지로 완료 기준에 이어 붙이지 않고, 성능·부하처럼 기능 요구사항이 아닌 것에서 나온 확인 경우는 완료 기준에만 붙인다.

#### 방법론이 얹는 것

행위 시나리오를 어떤 서식으로, 어느 축까지 전개할지는 **방법론이 정한다**. 활성 방법론의 `requires_in_spec`에 시나리오 산출물이 있으면 그 형식과 템플릿을 따른다(예: 상황·행위·기대 결과 구조, 동시성·멱등성·오류·경계 축 전개, 각 시나리오에 `불변`/`유동` 표시).

방법론을 켜지 않았다면 위 "코어가 요구하는 것"만 하고 넘어간다 — **없는 방법론의 서식을 흉내 내지 않는다.**

#### 불변과 유동을 가른다

시나리오가 촘촘할수록 검증은 단단해지지만 나중에 고치기 어려워진다. 그래서 **무엇이 계약이고 무엇이 편의인지 표시한다.**

- **`불변`** — 깨지면 데이터·돈·접근권한·외부 계약이 깨지는 것. 구현이 어렵다는 이유로 고치지 않는다. 이 표시는 명세 묶음을 나갈 때(Design(5) 통과) **동결**된다 — 그 전까지는 Scenarios·Design을 오가며 고칠 수 있다.
- **`유동`** — 지금 구현 방식에 딸린 것. 리팩터 중 바뀔 수 있다.
- 위험영역에 닿는 시나리오는 `불변`이 기본이다.

#### 게이트

- **기능 요구사항 중 확인 방법이 하나도 없는 것**, 또는 **확인 가능한 완료 기준 중 확인 방법이 없는 것**이 남아 있으면 **Design(5)으로 넘어가지 않는다.**
- 어떤 요구사항·완료 기준에도 붙지 않은 확인 경우가 있으면 어디서 나왔는지 밝히거나 지운다. 근거 없이 늘어난 검증은 나중에 고칠 때 발목만 잡는다.
- 활성 방법론이 요구한 시나리오 산출물이 미완이면 마찬가지로 넘어가지 않는다.
- `불변` 표시가 하나도 없으면 정말 없는지 한 번 되짚는다(위험영역에 닿는데 전부 `유동`인 것은 보통 표시를 안 한 것이다).

---

### 5. Design

`spec.md`(Clarify를 통과해 미확정 마커가 없는 상태)와 시나리오를 받아 **어떻게 만들 것인가**를 설계한다. 여기까지가 명세 묶음이다.

#### 설계 문서

`plan.md`가 **총괄 설계서**이고, 나머지는 그 하위 문서다. plan.md가 "무엇을 어떤 접근으로"를 잡고, 각 하위 문서가 관점별로 구체화한다.

- **`plan.md`** (상위, 항상 작성) — Summary + 기술 맥락(이 작업에서 *달라지는 것만*; 스택 고정값은 저장소 규칙 문서 참조) + **원칙 점검** + 구조 결정 + 어떤 하위 문서를 쓸지 지정 + **Phase 구성**(아래).
- 하위 문서 (이 작업에 필요한 것만 작성):
  - **`architecture.md`** — 구조·레이어·책임·데이터 흐름.
  - **`data-model.md`** — 도메인 엔티티·관계·식별·**상태 전이**(도메인 모델을 다루면). ← 위험영역.
  - **`db-schema.md`** — 테이블·인덱스·마이그레이션(물리 스키마). data-model이 개념, db-schema가 물리.
  - **`api-spec.md`** — API 계약(API 변경이 있으면).
  - **`adr.md`** — 채택 결정 staging(기록할 결정이 생기면 그때그때 append).
  - **`research.md`** — 기술 선택 조사(새 의존성·미해결 기술 선택이 있을 때만).
  - **활성 방법론의 템플릿** — 각 manifest의 `templates`에 있는 것을 이 spec의 설계 문서로 쓸 수 있다(`<PLUGIN_DIR>/methodologies/<이름>/templates/`). 필요한 것만 꺼내 쓰고, 방법론이 요구한 산출물(`requires_in_spec`)은 빠뜨리지 않는다. 모델 경계·용어 같은 설계 판단이 걸리면 그 방법론의 `consult` 모드 agent를 `Task`로 띄워 함께 잡는다.

**원칙 점검 (GATE)**: plan을 확정하기 전에 아래를 점검한다. 저장소가 지정한 규칙 문서(설정의 `rule_docs`)가 있으면 그것도 기준에 넣는다. 활성 방법론이 있으면 그 manifest의 `adds_checks`도 이 시점에 함께 본다 — 설계가 그 규칙을 위반하면 Analyze(7)까지 미루지 않고 여기서 고친다.

- 위험영역에 닿는데 spec.md에 미확정 마커가 남아 있으면, **설계를 진행하지 않고 Clarify(3)로 되돌아간다.**
- 설계가 규칙 문서가 정한 구조·의존 방향·경계·예외 처리 규약을 위반하면, plan.md "복잡도·예외 기록"에 정당화하거나 설계를 고친다. 원칙을 희석하지 않는다.
- **트랜잭션 경계 점검**: 외부 시스템 호출(결제·메일·원격 API 등)이 데이터베이스 트랜잭션 경계 안에서 일어나는 설계가 아닌가. 위반이면 설계를 고친다 — 트랜잭션이 열린 채 외부 응답을 기다리면 잠금이 길어지고, 경합 시 상대의 커밋을 보지 못해 수렴에 실패한다.
- **시나리오 충족 점검**: Scenarios(4)에서 정한 시나리오가 **이 설계로 전부 확인 가능한가.** 확인할 수 없는 시나리오가 있으면 설계를 고친다 — 시나리오를 설계에 맞춰 깎지 않는다.
- **설계가 드러낸 시나리오 보강**: 경합·복구·트랜잭션 경계처럼 **설계를 알아야 구체화되는 시나리오**가 보이면 Scenarios 산출물에 추가한다. 위험영역에 닿는 것은 `불변`으로 표시한다.

#### Phase 구성 (`plan.md`에 적는다)

**몇 번에 나눠 통합·검증할 것인가**를 여기서 정한다. phase는 "그 단위만으로 한 번 통합·검증할 가치가 있는 덩어리"이고, 앞이 서야 뒤가 서는 선후 의존은 그 자체가 구조 판단이라 설계에 속한다. 각 phase를 어떤 커밋들로 쪼갤지(step)는 Steps(6)의 일이니 여기서 적지 않는다.

- **기본값은 spec당 phase 1개**(`1-main`)다. 통합 지점이 한 번뿐인 보통 크기의 작업은 나누지 않는다.
- 아래 중 하나가 분명할 때만 여러 개로 나눈다.
  - 강한 선후 의존: 앞 phase가 끝나야 다음 phase를 안전하게 시작할 수 있다. (예: 공통 도메인·인프라 선행 → 그 위에 기능)
  - 중간 검증 가치: 큰 작업에서 중간에 한 번 끊어 제대로 됐는지 확인하고 가는 게 의미 있다.
- 큰 작업을 phase 없이 step만 길게 늘어놓지 않는다. 중간 통합 지점이 없으면 검증이 끝으로 몰려 되돌림 비용이 커진다.
- phase 이름은 `<순번>-<slug>` 형식을 쓰고, **순번은 개수와 무관하게 항상 1부터 시작한다**(`1-main` / `1-foundation`·`2-engine`). 실행 순서의 정본은 `phases/index.json`의 배열이다.
- 각 phase에 **"이 phase 끝에 무엇이 검증되는가"**를 한 줄로 적는다. 그게 통합 지점의 정의다.

#### 이 단계를 닫을 때 (명세 묶음 종료 · 동결)

Design을 `completed`로 두는 순간 **요구와 `불변` 시나리오가 동결**된다. 닫기 전에 확인한다.

- spec.md에 미확정 마커가 남아 있지 않다.
- 모든 시나리오가 이 설계로 확인 가능하고, 설계가 드러낸 시나리오는 보강됐다.
- 동결된다는 사실을 사용자에게 알리고 진행 의사를 확인한다 — 이후 요구를 바꾸려면 명세 묶음으로 되돌아와야 한다.

---

### 6. Steps

동결된 명세·시나리오·설계를 **기계가 실행할 단위로 옮긴다.** 여기서부터는 다시 만들어도 되는 산출물이다 — 실행이 막히면 명세를 건드리지 않고 이 분해만 고친다.

**phase는 Design(5)이 `plan.md`에 정해 놓았다.** 이 단계는 그 phase를 **step으로 나누고** 실행 파일을 만든다. phase 구성이 실제로 잘못됐다고 판단되면 임의로 바꾸지 말고 Design(5)으로 되돌아가 고친다.

> **활성 방법론의 요구 (`requires_in_steps`)**: 각 manifest의 `requires_in_steps`에 적힌 요구를 step 문서 본문에 **문장으로** 적는다(예: bdd → "그 step이 확인할 시나리오를 테스트로 옮긴다"를 구현 지시 첫 항목으로). Stage 8에서 구현하는 agent가 읽는 것은 step 문서이므로, 어떤 방법론이 켜졌는지 이름만 알려주면 그 요구는 구현 단계에서 지켜지지 않는다. Analyze(7)가 step 문서를 보고 이 반영 여부를 확인한다.

#### Step 설계 원칙

- 한 step은 테스트 가능한 사용자 기능 단위를 기본값으로 삼는다.
- API feature는 domain, repository, service, controller, test가 같은 사용자 기능 완성에 필요하면 한 step에 함께 포함한다.
- 레이어별 step 분리는 공통 도메인 선행 작업, 독립 DB 마이그레이션처럼 분리 검증이 명확히 필요한 경우에만 사용한다.
- command/query는 데이터 흐름과 검증 기준이 다르면 분리하고, 같은 정책과 aggregate를 공유하는 command 동작은 묶을 수 있다.
- 각 step 문서는 독립 실행 가능한 자기완결 문서여야 한다.
- **각 step 문서에 `## 검증 대상` 절을 두고, 이 step이 확인하는 요구사항·완료 기준·시나리오를 목록으로 밝힌다.** 이 목록이 없으면 어떤 요구가 어느 step에서 검증되는지 대조할 수 없어, Analyze(7)가 대응 관계를 추측해야 하고 계약으로 표시한 것이 조용히 빠져도 잡히지 않는다. `## 관련 문서`(읽을 문서를 가리킴)와 성격이 다르니 한 절에 섞지 않는다. 여기 적은 식별자는 문서 안에만 두고 코드·테스트 이름에 옮기지 않는다.
- step 설계 시 구현 단위와 커밋 단위가 같은 기능/정책 목적을 가리키도록 나눈다. 파일 단위로 과도하게 쪼개지 않는다.
- 관련 문서 경로와 이전 step 결과를 이해하는 데 필요한 파일 경로를 명시한다.
- 구현 지시는 인터페이스와 핵심 제약 위주로 작성하고, 내부 구현은 과도하게 고정하지 않는다.
- Acceptance Criteria는 실행 가능한 커맨드로만 적는다. (이 AC가 "스펙에서 벗어남"의 정의선이다.)
- **AC는 Scenarios(4)에서 정한 시나리오를 옮긴 것이다 — 여기서 새로 발명하지 않는다.** 시나리오가 "무엇을 확인하는가"를 정했고, AC는 그것을 "어떤 명령으로 확인하는가"로 바꾼 것이다. 어떤 시나리오에도 대응하지 않는 AC가 있으면 그 AC가 잘못됐거나 시나리오가 빠진 것이다(후자면 Scenarios로 돌아간다).
- **`불변`으로 표시된 시나리오는 반드시 어떤 step의 AC에 대응해야 한다.** 대응이 없으면 그 계약은 검증되지 않는다 — Analyze(7)가 이 대응 관계를 대조한다.
- **동시 실행 시의 정합(같은 자원을 동시에 만들거나 갱신하는 경합 수렴 등)을 요구하는 step은 AC에 실제 경합을 재현하는 테스트를 건다.** 협력 객체를 대역으로 바꾼 단위·부분 테스트는 실제 트랜잭션·잠금 거동을 재현하지 못해 경합 버그를 놓치므로, 단위·부분 테스트만으로 통과시키지 않는다. 그 테스트를 쓰는 방식에 대한 규칙 문서가 있으면 그것을 따른다.
- 주의사항은 `하지 마라. 이유: ...` 형식으로 구체적으로 작성한다.
- step name은 kebab-case slug를 사용한다.

산출 (설계 문서는 Design(5)이 이미 만들었다 — 이 단계는 실행 파일만 만든다):
- `<SPEC_ROOT>/<spec-name>/phases/index.json` — `plan.md`의 Phase 구성을 그대로 옮긴 phase 목록.
- `<SPEC_ROOT>/<spec-name>/phases/<phase-name>/index.json`, `phases/<phase-name>/step{N}.md`.

step 문서와 phase index는 템플릿 폴더의 `step.md`·`phase-index.json`을 복사해 쓴다 — `## Acceptance Criteria` 헤더가 어긋나면 AC가 파싱되지 않는다.

포맷과 상세 규칙은 `references/phase-files.md`를 따른다.

루트 docs 동기화(`sync-root-docs`)는 phase의 step으로 두지 않는다. Stage 10(Root Sync)에서 phase 바깥에서 수행한다.

---

### 7. Analyze

구현 전, 작성된 문서들을 읽기 전용으로 점검하는 게이트다. **관점이 다른 검사관 여섯을 `Task` 도구로 동시에 띄워** 각자의 전문성으로 판정받고, 메인 에이전트가 그 결과를 모아 사용자와 항목별로 처리한다. 이 단계는 워크플로(Stage 8 전용) 바깥이므로 메인이 직접 호출한다.

| 검사관 | 무엇을 보나 |
| --- | --- |
| `analyzer-traceability` | 요구 → 시나리오 → step 검증 대상 → AC 사슬이 끊긴 곳, 커버리지 표 |
| `analyzer-domain` | 엔티티 식별·상태 전이, 위험영역 판별과 그 시나리오의 안정성 표시 |
| `analyzer-concurrency` | 경합 수렴·멱등성·트랜잭션 경계·부분 실패 후 보상 |
| `analyzer-access` | 누가 부를 수 있나, 신원을 무엇으로 확인하나, 남의 데이터가 보이는 경로 |
| `analyzer-rules` | `rule_docs`가 정한 구조·의존 방향·예외 처리 위반, 핵심 산출물 누락 |
| `analyzer-clarity` | 측정 기준 없는 요구, 미해소 표시, 용어 불일치, 중복·충돌 |

**나눈 이유는 한 에이전트가 열 가지를 한 번에 보면 뒤쪽이 얕아지기 때문이다.** 그래서 각 발견 유형은 **정확히 한 검사관에게만** 배정한다 — 두 곳에 두면 규칙이 갈라진다. 공통 규칙(read-only·입력·심각도·반환 형식)은 `references/analysis-contract.md` 하나에 있다.

#### 호출

여섯을 한 번에 띄운다. 각 프롬프트에 아래를 넣는다.

- spec 폴더 경로 `<SPEC_ROOT>/<spec-name>/`
- 공통 계약 경로 `<PLUGIN_DIR>/skills/run/references/analysis-contract.md`
- 활성 방법론 이름과 각 manifest 경로 (없으면 없다고 밝힌다)
- 재분석이면 이전 `analysis.json` 경로

활성 방법론의 `agents` 중 `review` 모드를 가진 것이 있으면 **일곱 번째로 함께 띄운다**(예: ddd → `spec-harness:domain-expert`). 그 리포트는 방법론 관점이라 위 여섯과 나란히 놓는다.

#### 모으기 — `<SPEC_ROOT>/<spec-name>/analysis.json`

검사관들은 읽기 전용이라 파일을 못 쓴다. 각자 리포트 끝에 JSON 블록을 내고, **메인이 그것들을 모아** `analysis.json`으로 저장한다. 스키마는 `references/phase-files.md`를 따른다.

병합 규칙:

- 같은 지점을 여럿이 지적했으면 하나로 합치고 `reported_by`에 검사관과 각자의 심각도를 함께 적는다. `severity`는 그중 가장 높은 것으로 둔다.
- **심각도가 엇갈리면 그 사실을 지운 채 합치지 않는다.** 한쪽이 CRITICAL, 다른 쪽이 MEDIUM으로 본 것은 판단이 갈렸다는 뜻이고, 다관점 검사의 가치는 그 이견이 드러나는 데 있다. triage에서 사용자에게 양쪽을 보여준다.
- 어느 검사관도 발견을 못 냈어도 그 검사관의 `not_applicable`은 남긴다 — 무엇을 보고 없다고 했는지가 근거다.

#### triage — 항목별로 처리한다

CRITICAL과 HIGH를 `AskUserQuestion`으로 처리한다(한 호출에 최대 4개씩 묶는다). MEDIUM·LOW는 기록만 남기고 묻지 않는다.

| 선택 | 기록 | 뜻 |
| --- | --- | --- |
| 고친다 | `{"kind": "fixed"}` | 문서를 고치고 Analyze를 다시 돈다 |
| 반려한다 | `{"kind": "rejected", "reason": "..."}` | 근거 없이는 기록하지 않는다 |
| 자세히 본다 | 기록 없음 | 어떤 요구·시나리오가 어떻게 깨지는지 설명하고 다시 묻는다 |

이견이 있는 항목은 선택지를 보여주기 전에 **누가 무엇을 다르게 봤는지** 먼저 알린다.

#### 게이트·종료

Analyze는 `set-stage`로 닫지 않는다. 아래 명령이 확인하고 닫는다.

```bash
python3 "<SKILL_DIR>/scripts/execute.py" close-analyze <SPEC_ROOT>/<spec-name>
```

- **CRITICAL은 근거를 적은 반려만 통과한다.** `fixed`는 막힌다 — "고치기로 했다"는 의사일 뿐이고, 해소는 **다시 분석해 그 발견이 사라지는 것**으로만 확인된다.
- step 문서의 AC 파싱 계약(`## Acceptance Criteria` 헤더·명령 블록·`expect:` 값·`## 검증 대상`)이 어긋나면 닫지 않는다. 이것이 깨져 있으면 Execution에서 step마다 같은 실패를 반복한다.
- 통과하면 그 시점 문서의 fingerprint를 `analysis.json`에 남긴다. 이후 문서가 바뀌면 preflight가 낡은 분석을 잡아 재분석을 요구한다.
- 수정은 자동 적용하지 않는다 — 사용자가 어디로 되돌아갈지(Specify·Clarify·Design) 정해 사람이 고친다.

#### Analyze 통과 후 필수 중단

- 작성·수정한 spec 문서(`spec.md`·`plan.md`·`architecture.md`·`data-model.md`·`db-schema.md`·`api-spec.md`·`adr.md`), phase index, step 문서, `analysis.json`, `workflow-checklist.json` 경로를 사용자에게 보고한다.
- 이 시점의 checklist는 `Interview`부터 `Analyze`까지(1~7)만 `completed`여야 하고, `Execution`(8) 이후는 `pending`이어야 한다.
- 사용자의 단순한 "진행해", "계속해", "Implement the plan"은 문서 검토 완료 또는 실행 승인으로 해석하지 않는다.

---

### 8. Execution

Stage 8(Execution) 실행은 **dynamic workflow(`/spec-harness:execute`)를 기동**해 수행한다. `execute.py`를 직접 돌려
phase를 완주시키지 않는다 — 대신 preflight로 workflow 인자를 만들고, workflow가 step 루프를 돈다.
실행 전 아래 순서를 반드시 거친다. 이 순서는 스크립트가 막지 않으므로 메인 에이전트가 지킨다(`preflight`가 막는 것은 checklist 상태뿐이다).

1. Analyze까지의 결과(작성한 spec 문서·phase 경로)와 실행 계획을 사용자에게 보고하고, 실행 진행 의사를 가볍게 확인받는다. 별도 Plan Mode·`ExitPlanMode` 절차는 거치지 않는다.
2. `AskUserQuestion`으로 agent별 실행 모델을 수집한다. (아래 "실행 옵션 수집" 절 참고)
3. 수집한 모델을 phase index의 `execution` 필드에 기록한 뒤, preflight → workflow 기동으로 실행한다.

- workflow는 worktree 안에서 기동하며, committer·finalizer 서브에이전트를 통해 커밋·push를 수행한다.
- 이 Stage에 들어가기 전 checklist의 `Interview`부터 `Analyze`까지(1~7)는 모두 `completed`여야 한다.
- 사용자가 승인하지 않으면 구현으로 진행하지 않는다.

> spec 문서(spec·plan·scenarios·architecture·data-model·db-schema·api-spec·adr)와 phase·step·index·checklist는 `<SPEC_ROOT>/<spec-name>/` 아래에 있고 **작업 중에는 `.gitignore` 대상**이라 커밋하지 않는다(예외: Stage 8에서 `<SPEC_ROOT>/_archive/`로 승격되는 사본). 따라서 workflow 기동 전 "spec 문서 사전 커밋" 단계는 없다. committer는 코드 변경만 커밋하며, 작업 중 spec 폴더는 git에 잡히지 않는다.

#### 실행 옵션 수집

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

수집된 값은 phase index의 `execution` 필드에 1회 기록되어 추적 가능해진다. 재실행 시에는 기존 값이 보존된다. 자세한 스키마는 `references/phase-files.md`를 참고한다.

#### 실행 — Stage 8 자동 흐름 (in_progress → phase 루프 → completed)

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
- step 완료/중단 상태는 recorder가 phase index에 기록한다. 상세 산출물·파일 포맷은 `references/phase-files.md`를 따른다.
- 결과 `outcome`이 `blocked`/`error`이면 즉시 중단된 것이다. 사용자에게 `stopped_at_step`·`reason`을 보고한다. finalize는 일어나지 않는다.
- **중단된 step의 재개는 사람이 원인을 고친 뒤 `reset-step`으로 명시적으로 신호한다**(아래 "중단·재개").
- agent는 사용자 승인 없이 실패 회피 목적으로 step 요구사항, Acceptance Criteria, spec 문서, root docs를 수정해 재시도하지 않는다.
- 실패 원인이 문서 누락, Acceptance Criteria 오류처럼 명확해 보여도 자동 수정하지 않는다. 먼저 원인과 수정 계획을 사용자에게 제시한다.

#### 중단·재개 (pending-only)

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

#### 커밋·finalize

step별 committer는 **코드 변경만 커밋**한다. spec 폴더(`<SPEC_ROOT>/<spec-name>/` — spec 문서·phase·step·index·checklist)는 전부 `.gitignore` 대상이라 `git status`·`git add`에 잡히지 않으므로, committer가 신경 쓸 필요가 없다.

phase 종료 시점에 finalizer(`execute.py finalize`)는 git 커밋을 만들지 않는다. 대신 다음을 한다:

1. phase index.json에 `completed_at`을 기록하고, 상위 spec `phases/index.json`의 이 phase status를 `completed`로 동기화한다. (둘 다 gitignore라 워킹트리 상태로만 남는다 — 재개·skip 판단에 쓰인다.)
2. `execution.push`가 true이고 `--no-push`가 아니면 현재 feature 브랜치를 원격으로 push한다. 이 push가 올리는 것은 step별 committer가 만든 **코드 커밋**이다.

`execution.push`가 false면 push를 생략하지만, PR은 원격에 push해야 열 수 있으므로 Stage 9(PR Review)로 진행하려면 push가 필요하다.

#### Stage 8 종료

- Stage 8은 workflow로 phase의 step을 모두 완료하고, phase 끝에서 원격 push한 뒤 PR을 오픈하는 것으로 종료한다.
- PR 오픈(`gh pr create --draft`)은 메인 에이전트가 phase 루프 직후 수행한다. workflow는 구현·검증·커밋·push까지 책임지고, PR 오픈은 그 바깥이다.
- draft로 여는 것은 Root Sync(10) 전 머지를 서버가 막게 하는 장치다. 저장소가 `.spec-harness/config.json`의 `pr.draft_until_root_sync`를 false로 두면 draft 없이 열되, 그때는 `merge-hook`이 agent의 Bash만 막아 사람의 수동 머지는 막히지 않는다.
- 루트 docs 동기화는 Stage 8(Execution)에 포함하지 않는다. Stage 10(Root Sync)에서 수행한다.
- 실행 중 코드가 spec 설계와 달라지면 **해당 spec 폴더의 설계 md(`architecture.md`·`api-spec.md`·`db-schema.md`)만 실제 구현된 대로 갱신**하고 루트 상태 문서는 건드리지 않는다. `spec.md`(요구·완료 기준)는 실행 중 편집하지 않는다 — 요구 변경은 Clarify로 되돌아간다. 루트 승격은 Root Sync(10)가 한다.
- PR은 Stage 8에서 한 번만 오픈한다. PR Review(9)는 같은 브랜치·같은 PR에 커밋·push를 더 쌓을 뿐 PR을 새로 열지 않는다.
- PR을 오픈한 뒤 메인 에이전트는 PR Review(9)로 자동 진행하지 않고 멈춰, 사용자의 검토 완료 신호를 기다린다. 이 시점에 리뷰 코멘트가 아직 없다는 것은 PR Review 완료가 아니므로, Root Sync(10)를 앞당기지 않는다.

---

### 9. PR Review

Stage 8(Execution)에서 오픈한 PR에 달린 review를 처리한다.

이 단계는 기본적으로 **사용자가 PR을 검토하는 단계**다. 메인 에이전트는 Execution(8)에서 PR을 연 뒤 멈추고 사용자의 검토 완료 신호를 기다린다(요청 시 agent가 검토·반영을 위임받을 수 있으나, 대부분 사용자 검토로 본다).

PR은 draft 상태다. draft에서도 리뷰·코멘트·CI는 그대로 동작하고 머지만 잠긴다.

**Stage 10(Root Sync) 진입 게이트** — 아래를 분명히 구분한다.

- **리뷰 코멘트가 없다는 것은 PR Review 완료가 아니다.** 리뷰가 뒤늦게 코드를 바꾸면 미리 만든 Root Sync 산출물이 어긋난다.
- **Stage 9(PR Review) 완료**는 다음 둘 중 하나다. (1) 사용자가 검토를 종료했다고 알린 경우(코멘트 처리 완료 포함), (2) 사용자가 명시적으로 agent에 검토를 위임했고 그에 따른 반영이 끝난 경우.
- Stage 9(PR Review) 완료가 확인되기 **전에는** Stage 10(Root Sync)에 착수하지 않는다. 완료가 확인된 뒤에야 Root Sync(10)를 진행하며, 그 단계는 메인 에이전트가 자동으로 처리해도 된다. Root Sync가 끝나면 harness는 종료하고, merge는 사람이 수동으로 한다.

review 처리 방식:

- 사람이 review 코멘트(예: GitHub에 연결한 코드리뷰 봇, 또는 다른 리뷰어)를 보고 항목별 처리 방향(accept / reject / modify)을 **결정**한다.
- 결정에 따른 코드 수정·답변·thread resolve는 **사람이 이 단계에서 직접 수행**한다(harness 워크플로 바깥). 수정 커밋·push는 Stage 8(Execution)에서 오픈한 같은 브랜치/같은 PR에 쌓는다. `execute.py`의 commit agent는 Stage 8 전용이며 이 Stage에 관여하지 않는다.
- review 수정이 계약/구조/결정을 바꿨다면 Stage 10(Root Sync)에서 그 변경을 루트에 반영한다. 내부 구현만 바뀐 경우 루트 동기화가 불필요할 수 있다.

---

### 10. Root Sync

이 Stage는 Stage 9(PR Review) 완료가 확인된 뒤에만 착수한다. PR review까지 코드가 확정된 시점에 루트 문서를 현재 상태로 동기화한다. merge 직전 1회 수행을 기본으로 하며, 코드가 또 바뀌면 다시 실행할 수 있는 멱등 연산으로 본다.

문서 종류별로 동작이 다르다. 한 지시로 뭉치지 않는다.

- **ADR (append)**: 루트 ADR은 수정·삭제하지 않는다. spec ADR(staging)에서 새로 채택된 결정만 루트 전역 번호로 이어붙인다. 기존 결정을 대체하면 새 레코드에 `supersedes`를 적고, 옛 레코드 상태를 `superseded`로 바꾼다(상태 한 줄 갱신은 허용). 이미 기록된 결정인지 확인 후 새 결정만 추가한다.
- **architecture / db-schema / api-spec (overwrite)**: 루트 현재 파일과 spec 문서를 **둘 다 입력으로 읽고**, 기억으로 재작성하지 말고 현재 루트 기준으로 이번 변경분만 반영한 전체 완성본을 출력한다. 이번에 안 건드린 부분은 보존한다.

위 루트 동기화와 **별개로**, 이 spec의 작업 기록을 영구 보존한다.

- **`_archive` 승격**: 작업 중 휘발 상태였던 spec 문서 중 **정본만** `<SPEC_ROOT>/_archive/pr-<PR번호>-<spec명>/`로 복사한다. PR 번호는 Stage 8(Execution)에서 PR을 열 때 이미 정해져 있다. `<SPEC_ROOT>/*`는 `.gitignore` 대상이지만 `_archive`는 예외라(`!<SPEC_ROOT>/_archive`), 이 사본만 git에 잡혀 같은 PR에 커밋된다.
  - **승격 제외(휘발로 남김)**: 진행 상태·실행 부산물 — `phases/index.json`, `phases/<phase>/index.json`, `workflow-checklist.json`, `step<N>-ac-output.json`, `logs/`.
  - **승격 대상**: 그 밖의 **모든 `.md`**와 `analysis.json`. `.md` 목록을 열거하지 않는 이유는, 열거하면 새 문서가 생길 때 조용히 빠지기 때문이다. 실제로는 `spec.md`·`plan.md`·`scenarios.md`·`data-model.md`·`architecture.md`·`db-schema.md`·`api-spec.md`·`adr.md`·`interview.md`·`research.md`와 `phases/<phase>/step<N>.md` 중 작성된 것이 해당한다.
  - **`scenarios.md`·`data-model.md`를 빠뜨리면 안 된다** — 동결된 계약과 상태 전이 정본이다. spec 폴더는 작업 후 지워지므로, 승격하지 않으면 step 문서의 `## 검증 대상`이 가리키는 시나리오 식별자가 존재하지 않는 문서를 향하게 된다.
  - 복사만 한다. 내용을 재작성하지 않는다. 루트 ADR append는 위에서 이미 했으므로, `_archive`의 `adr.md`는 "이 spec이 그 결정에 어떻게 도달했나"의 맥락 사본이다.

sync 후 agent는 변경 요약(루트 문서 중 무엇을 갱신·보존했는지, `_archive`로 무엇을 승격했는지)을 보고하고 사용자 검토를 받는다. 커밋·push는 Stage 8(Execution)에서 오픈한 같은 PR에 쌓는다(루트 문서 갱신 + `_archive` 사본이 함께 올라간다).

#### draft 해제 — 이 Stage의 마지막

위 커밋·push가 끝나고 Root Sync를 `completed`로 찍은 뒤, draft를 벗긴다.

```bash
python3 "<SKILL_DIR>/scripts/execute.py" ready-pr <SPEC_ROOT>/<spec-name>
```

이 명령은 checklist 1~10이 모두 `completed`이고 `_archive/pr-<번호>-<spec명>/spec.md`가 HEAD에 커밋됐는지 확인한 뒤에만 `gh pr ready`를 부른다. staging만 한 상태는 통과하지 못한다 — 커밋되지 않은 사본은 PR에 올라가지 않는다. 어긋나면 무엇이 빠졌는지 낸다.

`gh pr merge`·`gh pr ready`를 Bash로 직접 부르는 것은 `merge-hook`이 막는다. 승격을 건너뛴 채 draft를 벗길 경로를 없애기 위함이다.

Stage 10(Root Sync)이 spec-harness의 마지막 단계다. draft가 벗겨진 뒤 merge는 **사람이 수동으로** 수행한다 — agent는 어떤 경우에도 merge하지 않는다. 작업 회고·지식 축적이 필요하면 harness 바깥에서 별도로 처리한다(이 워크플로의 책임이 아니다).
