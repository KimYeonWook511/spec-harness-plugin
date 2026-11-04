---
name: implement
description: 구현 저장소(서버·앱 등)에서 docs 저장소에 동결된 기능 spec 버전을 가져와 이 플랫폼에서 설계하고 구현할 때 이 skill을 쓴다. "F01-v1 구현하자", "기능 spec 가져와서 서버 작업 시작", "F02 앱 쪽 구현", "동결된 기능 spec대로 고쳐야 하는 버그" 같은 요청이 해당한다. 기능 spec을 만들거나 고치는 것은 docs 저장소의 `feature`, 기능 spec과 무관한 플랫폼 내부 작업(리팩터·성능·로깅)은 `run`이다.
---

# 기능 구현

docs 저장소가 동결한 기능 spec 버전(`F01-v1`)을 가져와, **어떻게 만들지**를 이 저장소에서 정하고 구현한다. 가져온 요구·시나리오·계약은 읽기만 한다. 바꿔야 하면 docs 저장소에서 기능 변경으로 버전을 올리고 다시 가져온다.

규칙과 같은 절차는 `run`의 것을 그대로 쓰고, 이 문서에는 다른 점만 적는다.

## 이 skill을 쓰는 일

| 작업 | 범위 |
| --- | --- |
| 동결된 기능의 구현 | 그 버전의 요구 중 이번 PR이 맡을 것 |
| 구현 버그 (기능 spec이 분명히 정했는데 코드가 다르다) | 어긴 요구·시나리오 + 회귀를 막는 플랫폼 시나리오 |
| 새 기능 버전 반영 | 바뀐 요구·시나리오·계약 |

기능 spec이 정하지 않은 경우가 버그로 드러났거나, 사용자에게 보이는 동작·계약을 바꿔야 하면 이 skill이 아니라 docs 저장소의 `feature`(기능 변경)다.

## 자리표시자

- **`<SKILL_DIR>`** — 이 skill의 base directory 절대경로.
- **`<RUN_DIR>`** — `<SKILL_DIR>/../run`.
- **`<EXEC>`** — `<RUN_DIR>/scripts/execute.py`.
- **`<SPEC_ROOT>`** — 설정의 `spec_root`, 없으면 `docs/specs`.
- **`<S>`** — 이번 구현 spec 폴더 `<SPEC_ROOT>/<spec-name>`.

설정(`.spec-harness/config.json`)의 `upstream.path`가 docs 저장소의 로컬 체크아웃을 가리켜야 한다. `upstream.on_newer_compatible`은 minor 새 버전(구현을 다시 확인할 필요 없음)이 있을 때 알리기만 할지(`warn`, 기본) 막을지(`block`)다.

## 구현 spec 폴더

```
<S>/
├─ upstream.json          가져온 버전·출처 커밋·파일 해시
├─ upstream/              가져온 기능 spec, 읽기만 한다: spec · scenarios · contract · glossary · domain/ · openapi
├─ spec.md                이번 PR이 맡는 범위
├─ verification.md        가져온 시나리오 → 이 플랫폼의 검증, 플랫폼 시나리오
├─ plan.md 와 설계 문서     서버: architecture · data-model · db-schema · adr / 앱: screens · data-layer · adr
├─ review-design.json     Design Review(설계 검사) 결과
├─ analysis.json          Analyze(문서 검사) 결과
└─ phases/ …              run과 같다
```

ID: 가져온 것은 그대로(`F01-FR-003`, `F01-SCN-012`), 이 플랫폼에서만 쓰는 것은 `P-FR-001`, `P-SCN-001`. 어느 쪽도 코드·테스트 이름에 넣지 않는다.

## 게이트

`<RUN_DIR>/SKILL.md`의 게이트 표에서 Execution(실행) 이후는 그대로 적용된다. 그 앞은 이렇다.

| 단계 | 게이트 | 누가 막나 |
| --- | --- | --- |
| Import(가져오기) | 가져온 태그가 docs 저장소에 있는 동결 버전이다 | `import-feature` |
| Clarify(모호함 해소) | 플랫폼 위험영역 마커 0, docs 저장소에 낸 변경 요청 중 답이 없는 것 0 | 메인 에이전트 |
| Verification(검증 매핑) | 이번 범위의 가져온 시나리오가 모두 검증에 매핑됐다 | 메인 에이전트. Design Review·Analyze가 다시 본다 |
| Design(설계) (앱) | 계약 형태가 확정된 버전을 가져왔다 | 메인 에이전트 |
| Design Review · Analyze | CRITICAL은 고치거나 근거를 남기고 넘긴다, 검사한 뒤 문서 불변, 가져온 기능 spec(`upstream/`) 불변 | `close-review` · `close-analyze` |
| Analyze | Design Review 이후 `spec.md`·`verification.md` 불변 | `close-analyze` |
| Execution | 가져온 기능 spec 불변, major 새 버전(구현을 다시 확인해야 하는 변경) 없음, 가져온 뒤 분석이 낡지 않았다 | `preflight` |

## 진행 상태 표

| 묶음 | 단계 | 상태 |
| --- | --- | --- |
| 가져오기 | Import |  |
| 명세 | Scope(범위 정하기) |  |
| 명세 | Clarify |  |
| 명세 | Verification |  |
| 설계 | Design |  |
| 설계 | Design Review |  |
| 변환·검증 | Steps(step 분해) |  |
| 변환·검증 | Analyze |  |
| 실행 | Execution |  |
| 실행 | PR Review(PR 리뷰) |  |
| 실행 | Root Sync(루트 문서 반영) |  |

## 흐름

`run`의 단계 파일을 쓸 때 단계 번호는 이 표의 이름으로 바꿔 읽는다. "명세 묶음으로 되돌아간다"는 이 skill에서 "docs 저장소의 기능 변경으로 보낸다"다.

### 1. Import

1. `<RUN_DIR>/references/stages/specify.md`의 "작업 공간 준비" 1~2를 따라 작업 공간(worktree)을 만든다.
2. `python3 "<EXEC>" init-checklist <S> --workflow implement`
3. 사용자에게 가져올 버전을 확인하고 `python3 "<EXEC>" import-feature <S> --version F01-v1`
4. docs 저장소의 `CHANGELOG.md`에서 이 버전 항목을 읽어, 무엇이 바뀌었는지 사용자에게 알린다. 끝나면 Import를 `completed`로 둔다.

### 2. Scope

이번 PR이 가져온 요구 중 무엇을 맡는지 정해 `<S>/spec.md`(템플릿 `<SKILL_DIR>/templates/spec.md`)를 쓴다. 기능 하나는 구현 spec 여러 개로 나뉠 수 있다.

- 가져온 요구의 일부만 맡으면 어디까지인지 적고, 나머지를 어느 구현 spec이 맡는지 적는다.
- 플랫폼 요구(`P-FR`)는 더할 수 있다. 가져온 요구를 바꾸거나 약하게 만들거나, 가져온 시나리오와 다른 결과를 내는 플랫폼 요구는 둘 수 없다.
- `<RUN_DIR>/references/stages/specify.md`대로 작성 전에 이 저장소의 루트 문서와 부딪히는지 확인한다.

### 3. Clarify

`<RUN_DIR>/references/stages/clarify.md`를 따르되 **플랫폼 안의 모호함만** 다룬다(서버: 마이그레이션·데이터 보존, 앱: 기기에 저장하는 개인정보 등). 모호함이 가져온 요구·시나리오·계약 수준이면 멈추고, docs 저장소에 기능 변경 요청을 낸 뒤 `spec.md`의 `## docs 저장소에 낸 변경 요청`에 적고 새 버전을 기다린다. `upstream/`을 고치지 않는다.

### 4. Verification

`<SKILL_DIR>/references/verification.md`를 따른다.

### 5. Design

`<RUN_DIR>/references/stages/design.md`를 따른다. 다른 점:

- 서버는 run의 설계 템플릿을 그대로 쓴다. 앱은 `screens.md`·`data-layer.md`(`<SKILL_DIR>/templates/`)를 쓴다.
- "명세 묶음 종료·동결" 절은 적용하지 않는다. 동결은 docs 저장소에서 이미 끝났다.
- **계약 형태**: 서버가 설계하며 `openapi.yaml`의 형태를 확정하거나 바꿔야 하면, docs 저장소에 PR을 올려 기능 변경(버전은 → `<SKILL_DIR>/../feature/references/change.md`)을 받은 뒤 `import-feature`로 다시 가져온다. 서버의 API 문서(코드에서 생성한 OpenAPI)가 가져온 `openapi.yaml`과 어긋나지 않는지 CI로 대조하는 것을 권한다.
- **앱**은 계약 형태가 확정된 버전을 가져온 뒤에만 Design을 닫는다. 그 버전의 `openapi.yaml`로 클라이언트와 목 서버를 만든다.

### 6. Design Review

`<RUN_DIR>/references/stages/analyze.md`의 호출·모으기·항목별 처리·다시 검사를 따른다. 결과 파일은 `<S>/review-design.json`, 검사 대상 고정은 `start-review <S> --stage "Design Review"`, 닫기는 `close-review <S> --stage "Design Review"`다. 검사관에게 넘기는 검사 범위는 `<SKILL_DIR>/references/design-review.md`에 있다.

### 7. Steps

`<RUN_DIR>/references/stages/steps.md`를 따른다. step의 `## 검증 대상`은 가져온 시나리오(`F01-SCN-…`)와 플랫폼 시나리오(`P-SCN-…`)를 가리킨다.

### 8. Analyze

`<RUN_DIR>/references/stages/analyze.md`를 그대로 따른다(`start-review <S> --stage Analyze`, `close-analyze <S>`). 검사관 프롬프트에는 `<SKILL_DIR>/references/design-review.md`의 "Analyze에 더하는 것"을 함께 넣는다.

### 9~11. Execution · PR Review · Root Sync

`<RUN_DIR>/references/stages/execution.md`·`pr-review.md`·`root-sync.md`를 따른다. 다른 점:

- developer는 가져온 요구·시나리오·계약과 `verification.md`를 함께 받는다. `upstream/`은 고치지 않는다.
- preflight가 `upstream/`이 그대로인지와 docs 저장소의 새 버전을 함께 본다. major 새 버전이 있으면 막히고, minor 새 버전은 `upstream_notes`로 알린다. 알림이 오면 사용자에게 전한다.
- "명세를 먼저 커밋한다"에서 커밋하는 파일과 Root Sync에서 `_archive`로 옮기는 파일에 `upstream.json`·`upstream/`·`review-design.json`을 넣는다. 나중에 이 구현이 어느 버전을 기준으로 했는지 저장소 안에서 확인할 수 있다.
- Root Sync가 끝나면 docs 저장소 `index.md`의 이 플랫폼 열을 구현한 버전으로 갱신하는 PR을 낼지 사용자에게 묻는다.
