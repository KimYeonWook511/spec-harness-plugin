# Analyze

구현 전, 작성된 문서들을 읽기 전용으로 점검하는 게이트다. **관점이 다른 검사관 여섯을 `Task` 도구로 동시에 띄워** 각자의 전문성으로 판정받고, 메인 에이전트가 그 결과를 모아 사용자와 항목별로 처리한다. 이 단계는 워크플로(Stage 8 전용) 바깥이므로 메인이 직접 호출한다.

| 검사관 | 무엇을 보나 |
| --- | --- |
| `analyzer-traceability` | 요구 → 시나리오 → step 검증 대상 → AC 사슬이 끊긴 곳, 커버리지 표 |
| `analyzer-domain` | 엔티티 식별·상태 전이, 위험영역 판별과 그 시나리오의 안정성 표시 |
| `analyzer-concurrency` | 경합 수렴·멱등성·트랜잭션 경계·부분 실패 후 보상 |
| `analyzer-access` | 누가 부를 수 있나, 신원을 무엇으로 확인하나, 남의 데이터가 보이는 경로 |
| `analyzer-rules` | `rule_docs`가 정한 구조·의존 방향·예외 처리 위반, 핵심 산출물 누락 |
| `analyzer-clarity` | 측정 기준 없는 요구, 미해소 표시, 용어 불일치, 중복·충돌 |

**나눈 이유는 한 에이전트가 열 가지를 한 번에 보면 뒤쪽이 얕아지기 때문이다.** 그래서 각 발견 유형은 **정확히 한 검사관에게만** 배정한다 — 두 곳에 두면 규칙이 갈라진다. 공통 규칙(read-only·입력·심각도·반환 형식)은 `<SKILL_DIR>/references/analysis-contract.md` 하나에 있다.

## 호출

여섯을 한 번에 띄운다. 각 프롬프트에 아래를 넣는다.

- spec 폴더 경로 `<SPEC_ROOT>/<spec-name>/`
- 공통 계약 경로 `<PLUGIN_DIR>/skills/run/references/analysis-contract.md`
- 활성 방법론 이름과 각 manifest 경로 (없으면 없다고 밝힌다)
- 재분석이면 이전 `analysis.json` 경로

활성 방법론의 `agents` 중 `review` 모드를 가진 것이 있으면 **일곱 번째로 함께 띄운다**(예: ddd → `spec-harness:domain-expert`). 그 리포트는 방법론 관점이라 위 여섯과 나란히 놓는다.

## 모으기 — `<SPEC_ROOT>/<spec-name>/analysis.json`

검사관들은 읽기 전용이라 파일을 못 쓴다. 각자 리포트 끝에 JSON 블록을 내고, **메인이 그것들을 모아** `analysis.json`으로 저장한다. 스키마는 `<SKILL_DIR>/references/phase-files.md`를 따른다.

병합 규칙:

- 같은 지점을 여럿이 지적했으면 하나로 합치고 `reported_by`에 검사관과 각자의 심각도를 함께 적는다. `severity`는 그중 가장 높은 것으로 둔다.
- **심각도가 엇갈리면 그 사실을 지운 채 합치지 않는다.** 한쪽이 CRITICAL, 다른 쪽이 MEDIUM으로 본 것은 판단이 갈렸다는 뜻이고, 다관점 검사의 가치는 그 이견이 드러나는 데 있다. triage에서 사용자에게 양쪽을 보여준다.
- 어느 검사관도 발견을 못 냈어도 그 검사관의 `not_applicable`은 남긴다 — 무엇을 보고 없다고 했는지가 근거다.

## triage — 항목별로 처리한다

CRITICAL과 HIGH를 `AskUserQuestion`으로 처리한다(한 호출에 최대 4개씩 묶는다). MEDIUM·LOW는 기록만 남기고 묻지 않는다.

| 선택 | 기록 | 뜻 |
| --- | --- | --- |
| 고친다 | `{"kind": "fixed"}` | 문서를 고치고 Analyze를 다시 돈다 |
| 반려한다 | `{"kind": "rejected", "reason": "..."}` | 근거 없이는 기록하지 않는다 |
| 자세히 본다 | 기록 없음 | 어떤 요구·시나리오가 어떻게 깨지는지 설명하고 다시 묻는다 |

이견이 있는 항목은 선택지를 보여주기 전에 **누가 무엇을 다르게 봤는지** 먼저 알린다.

## 게이트·종료

Analyze는 `set-stage`로 닫지 않는다. 아래 명령이 확인하고 닫는다.

```bash
python3 "<SKILL_DIR>/scripts/execute.py" close-analyze <SPEC_ROOT>/<spec-name>
```

- **CRITICAL은 근거를 적은 반려만 통과한다.** `fixed`는 막힌다 — "고치기로 했다"는 의사일 뿐이고, 해소는 **다시 분석해 그 발견이 사라지는 것**으로만 확인된다.
- step 문서의 AC 파싱 계약(`## Acceptance Criteria` 헤더·명령 블록·`expect:` 값·`## 검증 대상`)이 어긋나면 닫지 않는다. 이것이 깨져 있으면 Execution에서 step마다 같은 실패를 반복한다.
- 통과하면 그 시점 문서의 fingerprint를 `analysis.json`에 남긴다. 이후 문서가 바뀌면 preflight가 낡은 분석을 잡아 재분석을 요구한다.
- 수정은 자동 적용하지 않는다 — 사용자가 어디로 되돌아갈지(Specify·Clarify·Design) 정해 사람이 고친다.

## Analyze 통과 후 필수 중단

- 작성·수정한 spec 문서(`spec.md`·`plan.md`·`architecture.md`·`data-model.md`·`db-schema.md`·`api-spec.md`·`adr.md`), phase index, step 문서, `analysis.json`, `workflow-checklist.json` 경로를 사용자에게 보고한다.
- 이 시점의 checklist는 `Interview`부터 `Analyze`까지(1~7)만 `completed`여야 하고, `Execution`(8) 이후는 `pending`이어야 한다.
- 사용자의 단순한 "진행해", "계속해", "Implement the plan"은 문서 검토 완료 또는 실행 승인으로 해석하지 않는다.
