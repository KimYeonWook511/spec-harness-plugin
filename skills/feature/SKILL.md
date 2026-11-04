---
name: feature
description: 여러 저장소(서버·앱 등)가 한 제품을 만들 때, 공유 docs 저장소에서 기능 spec을 만들고 고치고 동결할 때 이 skill을 쓴다. "PRD에서 기능 뽑자", "기능 목록 만들어줘", "F01 기능 spec 확정하자", "기능 spec 바꿔야 해", "spec에 이 경우가 빠졌어", "계약 버전 올려줘", "기능 동결" 같은 요청이 해당한다. 한 저장소 안에서 명세부터 구현까지 하는 작업은 `run`, 사용법 안내는 `guide`다.
---

# 기능 spec

여러 저장소가 한 제품을 만들면 **무엇을 만들고 어떻게 확인할지**를 공유 docs 저장소에서 확정·동결하고, **어떻게 만들지**는 각 구현 저장소가 정한다. 이 skill은 docs 저장소에서 기능 spec을 만들고, 고치고, 버전을 붙인다.

규칙(위험영역은 가정하지 않는다, 게이트마다 누가 막는지 정한다, 불변 시나리오는 계약이다)은 `run`과 같다. 같은 절차는 `run`의 단계 파일을 그대로 쓰고, 이 문서에는 다른 점만 적는다.

## 언제 어느 진입점을 쓰나

| 작업 | 진입점 |
| --- | --- |
| 새 기능 (PRD에서) | docs 저장소에서 `feature` → 각 구현 저장소에서 구현 |
| 기존 기능의 동작 변경 | docs 저장소에서 `feature`(기능 변경) → 버전 올림 → 각 구현 저장소에서 구현 |
| 사용자에게 보이는 동작·계약이 바뀌지 않는 일 (리팩터, 성능, 로깅, 의존성 업그레이드) | 해당 구현 저장소의 `run` |

구현 저장소는 동결된 기능 spec 버전을 입력으로 삼는다. 전용 진입점이 생기기 전에는 `run`의 Interview 입력으로 기능 버전(예: `F01-v1`)과 다룰 요구 ID를 적는다.

**버그는 "기능 spec이 이 경우를 뭐라고 하나"로 가른다.**

| 답 | 경로 |
| --- | --- |
| 기대 동작을 분명히 정했는데 코드가 다르다 | 구현 버그. 그 구현 저장소에서 고친다. 기능 spec은 그대로다 |
| 이 경우를 정하지 않았다 / 정한 대로인데 그게 틀렸다 | `feature`(기능 변경) |
| 플랫폼마다 계약을 다르게 읽었다 | `feature`(기능 변경), 계약 수정 |
| 동작 규칙과 무관하다 (화면 깨짐, 크래시, 메모리) | 그 구현 저장소의 `run` |

## 나누는 선

| 층 | 예 | 어디에 |
| --- | --- | --- |
| ① 사용자 관점 동작 | 저장하면 정리 중이 보이고, 끝나면 카드가 열린다 | 기능 spec·시나리오 |
| ② 경계 계약 | 상태값, 오류 코드, 멱등·재시도 규칙, 입력 제약, 반영 지연 | 계약(`contract.md`·`openapi.yaml`) |
| ③ 플랫폼 내부 | 서버: 락·트랜잭션·캐시 / 앱: 화면 전환·로컬 저장 | 구현 저장소 |

서버 기술로 보이는 것도 결과가 다른 플랫폼에 닿으면 ②로 올린다. "멱등 키로 중복 방지"는 서버 설계지만, "같은 요청을 두 번 보내도 하나만 남고, 앱은 재시도 때 같은 키를 보낸다"는 계약이다.

## 자리표시자

- **`<FEATURE_ROOT>`** — 설정(`.spec-harness/config.json`)의 `feature_root`, 없으면 `features`.
- **`<F>`** — 이번 기능 폴더 `<FEATURE_ROOT>/F<번호>-<slug>` (예: `features/F01-anonymous-start`).
- **`<SKILL_DIR>`** — 이 skill의 base directory 절대경로.
- **`<RUN_DIR>`** — `<SKILL_DIR>`의 형제인 `run` skill 폴더(`<SKILL_DIR>/../run`).
- **`<EXEC>`** — `<RUN_DIR>/scripts/execute.py`.

## 저장소 구조

```
<docs 저장소>/
├─ prd.md
├─ glossary.md               공통 용어집
├─ domain/<entity>.md        엔티티별 식별·상태·전이·불변식
├─ api/openapi.yaml          API 형태
├─ adr/                      여러 플랫폼에 걸친 결정
├─ CHANGELOG.md              기능 버전 기록
└─ <FEATURE_ROOT>/
   ├─ index.md               기능 목록 + 플랫폼별 상태
   └─ F01-<slug>/
      ├─ interview.md · spec.md · scenarios.md · contract.md
      ├─ review-1.json · review-2.json
      └─ workflow-checklist.json   진행 상태 (.gitignore)
```

용어집·domain·openapi는 기능마다 두지 않는다. 여러 기능에 걸치는 상태 전이를 쪼개면 갈라진다. 태그가 커밋 전체를 고정하므로 공유 파일도 기능 버전과 함께 고정된다. 템플릿은 `<SKILL_DIR>/templates/`에 있다.

ID는 `F01-FR-001`, `F01-SC-001`, `F01-SCN-001`처럼 기능 번호를 붙인다. 구현 저장소가 이 ID로 가리킨다. 코드·테스트 이름에는 넣지 않는다.

## 게이트

| 단계 | 게이트 | 누가 막나 |
| --- | --- | --- |
| Clarify | 위험영역 마커 0 | 메인 에이전트 |
| Scenarios | 모든 요구·완료 기준에 관찰 가능한 시나리오 | 메인 에이전트 |
| Spec Review | CRITICAL은 근거를 적은 반려만 | `close-review` |
| Contract Review | CRITICAL은 근거를 적은 반려만 + Spec Review 이후 spec·시나리오 불변 | `close-review` |
| 두 검사 | `start-review`로 고정한 문서가 닫을 때까지 그대로다(바뀌면 재검사, 또는 사용자 확인 뒤 `--edited`로 사유 기록) | `close-review` |
| Freeze | 두 검사가 닫혔고 그 뒤 문서가 바뀌지 않았다, CHANGELOG·기능 목록에 항목이 있다, 버전 규칙을 지켰다 | `freeze` |
| Freeze | 동결된다는 사실을 알리고 사용자가 진행을 밝혔다 | 사용자가 답해야 넘어간다 |
| Freeze | 태그는 머지된 깨끗한 체크아웃에서만 | `freeze --tag` |

**버전 규칙**: 첫 동결은 `v1`. `spec.md`·`contract.md`와 `scenarios.md`의 **`불변` 시나리오**가 그대로면 minor(`v1.1`), 하나라도 바뀌면 major(`v2`). `유동` 시나리오만 바뀐 것은 minor다. 불변을 유동으로 내리는 것도 major다. `freeze`가 직전 태그와 비교해 막는다.

단계 정의와 검사별 판정 대상 문서는 `<RUN_DIR>/stages.json`의 `feature`에 있다.

## 진행 상태 표

| 묶음 | 단계 | 상태 |
| --- | --- | --- |
| 명세 | Interview |  |
| 명세 | Specify |  |
| 명세 | Clarify |  |
| 명세 | Scenarios |  |
| 명세 | Spec Review |  |
| 계약 | Domain |  |
| 계약 | Contract |  |
| 계약 | Contract Review |  |
| 동결 | Freeze |  |

## 흐름 — 새 기능

`run`의 단계 파일을 쓸 때 단계 번호와 이름은 이렇게 바꿔 읽는다: Design·Analyze가 맡던 계약 확정은 Contract로, 검사는 Spec Review·Contract Review로, 동결은 Freeze로. 구현 설계(DTO·테이블·화면)는 이 skill에서 다루지 않는다.

방법론은 `<RUN_DIR>/SKILL.md`의 "방법론 (opt-in)" 절차를 그대로 따른다(설정의 `methodologies`).

### 0. 기능 목록

처음 한 번, 그리고 PRD가 바뀔 때 한다. PRD를 읽고 기능을 나눠 `<FEATURE_ROOT>/index.md`(템플릿 `index.md`)에 적는다. 기능 하나의 크기는 이 기준으로 정한다.

- **혼자 동결할 수 있다**: 다른 기능 spec이 미확정이어도 요구와 시나리오를 못 박을 수 있다.
- **사용자가 할 수 있는 것이 생긴다**: 끝나면 사용자가 실제로 무언가를 할 수 있다. "테이블 만들기"는 기능이 아니다.
- **위험영역이 몰리지 않는다**: 인증·개인정보·데이터 모델·상태 전이가 한 기능에 몰리면 나눈다. Clarify가 과부하된다.

사용자에게 확인받을 때 아래 셋을 함께 보인다. 기능 이름만 보여 주면 사용자가 나눈 방식이 맞는지 판단할 수 없다.

1. **PRD 대응표** — PRD의 범위 항목마다 맡는 기능을 하나씩 적는다. 어느 기능에도 들어가지 않은 항목과 두 기능에 걸친 항목을 표 아래에 따로 적는다. 빠진 항목은 아무도 만들지 않고, 겹친 항목은 두 기능이 같은 규칙을 따로 정한다.
2. **기능마다 크기 근거** — 위 세 기준을 어떻게 만족하는지 한 줄씩. 만족하지 못하는 기준이 있으면 그렇다고 적는다.
3. **경계 질문** — PRD만으로 어느 기능이 맡을지 정할 수 없는 규칙만 묻는다(예: "지각 판정은 회차 기능과 출석 체크 기능 중 어디서 정하나"). 기능 안의 세부는 각 기능의 Interview에서 묻는다.

정한 경계는 `index.md`의 `## 기능 경계`에 남긴다. 각 기능의 Interview가 이것을 읽는다. 목록·대응표·경계를 사용자와 확정한 뒤 의존 순서상 앞선 기능부터 골라 1단계로 간다.

### 1. Interview

`<RUN_DIR>/references/stages/interview.md`를 따른다. 다른 점:

- 먼저 읽을 것: PRD의 해당 범위, `index.md`(특히 `## 기능 경계`), 의존 기능의 동결본(태그), `domain/`, `glossary.md`, `adr/`.
- 산출은 2단계에서 `<F>/interview.md`로 옮긴다.

### 2. Specify

`<RUN_DIR>/references/stages/specify.md`를 따른다. 다른 점:

- 작업 공간 slug는 `F<번호>-<slug>`, spec 폴더는 `<F>`다. checklist는 `python3 "<EXEC>" init-checklist <F> --workflow feature`로 만든다.
- `spec.md`는 `<SKILL_DIR>/templates/spec.md`로 쓴다.
- 엔티티 상태가 걸리면 `domain/<entity>.md` **초안**도 이 단계에서 쓴다(템플릿 `entity.md`). 위험영역이라 Spec Review가 봐야 한다.
- 루트 문서 정합성 확인의 대상은 `adr/`, `domain/`, `glossary.md`, 의존 기능의 동결본이다.

### 3. Clarify

`<RUN_DIR>/references/stages/clarify.md`를 그대로 따른다. 답은 `spec.md`의 `## Clarifications`와 domain 초안에 반영한다. 계약 세부(오류 코드 이름·필드)는 Contract에서 정하므로 여기서 붙들지 않는다.

### 4. Scenarios

`<RUN_DIR>/references/stages/scenarios.md`를 따른다. 다른 점:

- `<F>/scenarios.md`(템플릿 `scenarios.md`)에 **관찰 가능한 결과만** 적는다. 관찰 지점이 로그·DB뿐이면 구현 저장소의 몫이므로 적지 않는다.
- 동시성·멱등은 결과만 적는다("하나만 남는다", "진 쪽은 충돌 오류"). 검증 방법(동시 100건 등)은 구현 저장소가 정한다.
- `불변`은 Freeze에서 동결된다.

### 5. Spec Review

`<SKILL_DIR>/references/review.md`를 따른다. spec 자체의 품질을 본다.

### 6. Domain

Spec Review에서 고친 내용을 반영해 `domain/<entity>.md`를 확정한다. 이번 기능의 용어를 `glossary.md`에 `| 용어 | 코드 식별자 | 뜻 | 쓰지 않는 말 |`로 더하고, 여러 플랫폼에 걸친 결정만 `adr/`에 적는다. 끝나면 checklist의 Domain을 `completed`로 둔다.

### 7. Contract

`<SKILL_DIR>/references/contract.md`를 따른다.

### 8. Contract Review

`<SKILL_DIR>/references/review.md`를 따른다. 계약과 spec·관련 문서가 서로 맞는지 본다.

### 9. Freeze

`<SKILL_DIR>/references/freeze.md`를 따른다.

## 흐름 — 기능 변경

`<SKILL_DIR>/references/change.md`를 따른다. 요구 변경, spec 빈칸 수정, 계약 수정, 구현 저장소가 올린 계약 확정이 모두 이 흐름이다.
