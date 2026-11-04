# 검사 (Spec Review · Contract Review)

검사를 두 번 하는 이유: 계약은 spec 위에 짓는다. spec의 결함을 계약까지 끌고 가면 고칠 곳이 두 배가 된다. Spec Review는 spec 자체의 품질을, Contract Review는 계약과 주변 문서의 일치를 본다.

호출·결과 모으기·항목별 처리는 `<RUN_DIR>/references/stages/analyze.md`의 "호출", "모으기", "triage"를 따른다. 다른 점은 아래뿐이다.

| | Spec Review | Contract Review |
| --- | --- | --- |
| 검사 대상 고정 (검사관을 띄우기 직전) | `python3 "<EXEC>" start-review <F> --stage "Spec Review"` | `python3 "<EXEC>" start-review <F> --stage "Contract Review"` |
| 결과 파일 | `<F>/review-1.json` | `<F>/review-2.json` |
| 닫기 | `python3 "<EXEC>" close-review <F> --stage "Spec Review"` | `python3 "<EXEC>" close-review <F> --stage "Contract Review"` |

결과 파일 형식은 `analysis.json`과 같다(`<RUN_DIR>/references/phase-files.md`). 재검사면 이전 결과 파일 경로를 함께 넘긴다.

## 검사관에게 넘기는 검사 범위

각 검사관 프롬프트에 공통 계약 경로와 함께 아래 블록을 넣는다. 검사관은 이 블록이 정한 문서와 질문만 본다.

두 블록 모두 이 규칙을 함께 넣는다: **한 플랫폼이 다른 플랫폼과 합의하지 않고 정해도 되는 것은 이 검사의 발견이 아니다.** 그런 것은 `not_applicable`에 "구현 저장소 몫"으로 적는다.

판단은 "다른 플랫폼의 동작이 이 결정에 달려 있나"로 한다.

| 구현 저장소 몫 | 계약이라 이 검사의 발견 |
| --- | --- |
| 서버가 중복을 무엇으로 막는지 | 서버의 어떤 응답(5xx, 타임아웃)을 앱이 어떤 경우로 다루는지 |
| 앱이 오프라인 표시를 어떤 모양으로 하는지 | 결과를 확인할 수 있는 응답이 있는지(예: 누구로 처리됐는지 드러나는가) |
| 서버가 한도를 무엇 단위로 세는지 | 한도에 걸렸을 때 앱이 받는 것과 할 일 |

### Spec Review

```
검사 범위: 기능 spec (Spec Review)
읽을 문서: <F>/spec.md, <F>/scenarios.md, <F>/interview.md, 이 기능이 쓰는 domain/<entity>.md, glossary.md
보지 않는 것: 계약, step·AC (아직 없다)
```

| 검사관 | 질문 |
| --- | --- |
| traceability | 모든 요구·완료 기준에 시나리오가 있나. 어떤 요구에도 걸리지 않는 시나리오는 없나 |
| domain | 상태 전이가 닫혀 있나(들어갈 길과 나올 길). 식별이 분명한가. 위험영역 시나리오가 `불변`인가 |
| access | 누가 무엇을 할 수 있고 무엇을 볼 수 있는지 빠짐없나. 요구가 가르려는 주체(사람·설치·호출자)를 지키는 쪽이 판별할 수단이 있나 |
| concurrency | 같은 요청이 두 번, 서로 다른 요청이 동시에 올 때 결과가 정해졌나. 결과만 보고 방법은 묻지 않는다 |
| rules | 플랫폼 내부(③)가 spec·시나리오에 섞였나. 관찰 지점이 로그·DB뿐인 시나리오가 있나 |
| clarity | 측정 기준 없는 요구, 남은 마커, 용어 불일치(spec·domain·glossary 사이) |

### Contract Review

```
검사 범위: 기능 계약 (Contract Review)
읽을 문서: <F>/spec.md, <F>/scenarios.md, <F>/contract.md, api/openapi.yaml, 이 기능이 쓰는 domain/<entity>.md, glossary.md
보지 않는 것: 구현 설계
```

| 검사관 | 질문 |
| --- | --- |
| traceability | spec의 모든 거절·상태가 계약에 오류 코드·상태값으로 있나. 요구 없는 계약 요소는 없나. `contract.md`와 `openapi.yaml`이 같은 것을 말하나 |
| domain | 계약의 상태값이 domain의 상태·전이와 같은가 |
| access | 엔드포인트별 "누가"가 spec과 같은가. 남의 데이터가 보이는 응답은 없나. 요구가 가르려는 주체를 서버가 요청에서 판별할 수 있나 |
| concurrency | 요청 규칙(멱등·재시도·반영 지연)이 시나리오의 동시성 결과를 다 덮나 |
| rules | 계약에 플랫폼 내부(③)가 새어 들었나(예: 락 방식, 캐시 키) |
| clarity | 모든 오류에 앱이 할 일이 있나. 용어가 spec·glossary·contract·openapi에서 같은가 |

## 닫은 뒤

검사가 끝난 뒤 판정 대상 문서를 고쳤으면 닫히지 않는다. 다시 검사하는 것이 원칙이고, 문구 수준이라 다시 검사할 필요가 없다면 바뀐 파일과 이유를 사용자에게 알리고 확인받은 뒤 `--edited "<이유>"`로 닫는다. 그 이유와 파일은 결과 파일의 `edited_after_review`에 남는다.

`close-review`가 판정 대상 문서의 지문을 결과 파일에 남기고 그 단계를 `completed`로 둔다. Contract Review는 Spec Review 이후 `spec.md`·`scenarios.md`가 바뀌었으면 닫히지 않는다 — 계약을 만들다 요구를 고쳤다면 Spec Review부터 다시 돌린다. domain·glossary는 그 사이 Domain 단계가 확정하므로 바뀌어도 된다.

닫은 결과(처리한 항목, 반려 근거)를 사용자에게 보고하고 다음 단계로 간다.
