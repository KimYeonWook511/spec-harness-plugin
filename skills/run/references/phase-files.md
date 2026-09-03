# phase 파일 구조 · AC 스키마 · agent 반환 계약 (spec-harness)

spec-harness가 다루는 phase 디렉터리의 파일 구조와, 각 단계가 주고받는 데이터 계약을 정의한다.
SKILL.md의 흐름을 이해한 뒤, 구체 스펙이 필요할 때 이 문서를 참조하라.

## 목차
1. 디렉터리 레이아웃
2. index.json 구조 (phase / spec)
3. step 문서와 Acceptance Criteria 스키마 (`# expect:`)
4. AC 검증 결과(ac-output.json) 구조
5. agent 반환 JSON 계약 (5종)
6. 실행 산출물과 정본의 구분

---

## 1. 디렉터리 레이아웃

```
<SPEC_ROOT>/<spec>/                  # ── 정본은 추적, 진행 상태·실행 부산물만 .gitignore
├── spec.md                         # spec 작업 스펙 (제품 전체 명세 아님)
├── plan.md                         # 총괄 설계서 (하위 설계 문서의 상위 인덱스)
├── architecture.md                 # 구조·레이어·데이터 흐름 (delta 스냅샷, plan 하위)
├── data-model.md                   # 도메인 엔티티·식별·상태 전이 (plan 하위)
├── db-schema.md                    # 물리 스키마 변경분 (plan 하위)
├── api-spec.md                     # API 변경분 (plan 하위)
├── adr.md                          # ADR staging (이번 작업의 결정사항, plan 하위)
├── scenarios.md                    # (선택) 시나리오를 spec.md에서 분리할 때. 완료 기준별 확인 방법·불변/유동 표시
├── interview.md                    # 인터뷰 기록 (Specify가 작업 공간을 만들 때 옮겨온 것)
├── research.md                     # (선택) 기술 선택 조사 — 새 의존성·미해결 선택 시만
├── workflow-checklist.json         # spec 레벨: Stage 진행 추적 + 실행 전 게이트(preflight가 검사)
└── phases/
    ├── index.json                  # spec 레벨: phase 목록과 각 phase status
    └── <phase>/                    # 예: 1-main (단일) / 1-domain, 2-api (복수). 순번은 항상 1부터
        ├── index.json              # phase 레벨: steps(목차) + execution(설정) + step status
        ├── step1.md                # step 문서 (구현 지시 + ## 검증 대상 + ## Acceptance Criteria)
        ├── step2.md
        ├── step1-ac-output.json    # (실행 산출) AC 검증 결과 attempts 누적 — reviewer가 읽음
        └── logs/                   # (실행 산출) <role>.log 사람용 로그
```

> checklist(`workflow-checklist.json`, spec 폴더 바로 아래)는 **spec 레벨에 하나**다. Stage 진행은 spec 전체의 것이고
> PR·Root Sync도 spec 단위이므로 phase마다 두지 않는다. phase가 여러 개여도 checklist는 하나이며, 각 phase는
> 그 안의 step만 workflow로 실행한다. (phases 폴더는 Steps(6)에서 생기지만 checklist는 그보다 먼저 Specify(2)에서 만들어지므로 phases 밖 spec 루트에 둔다.)

> step 문서·phase index 골격도 템플릿 폴더에 있다(`step.md`·`phase-index.json`). 기계가 헤더 문자열로 파싱하므로 이 둘은 템플릿에서 복사해 쓴다.

> spec 문서 템플릿과 `workflow-checklist.json` 골격은 템플릿 폴더에 있다(`SKILL.md`의 템플릿 폴더 설명 참고). checklist는 Specify(2)에서, 설계 문서는 Design(5)에서 필요한 것만 만든다.

저장소의 루트 문서(ADR·규칙 문서 등)는 전역 베이스다.
spec 문서가 이번 작업의 구체 결정, 루트 문서가 전역 원칙이다(충돌 시 spec 우선).

---

## 2. index.json 구조

### phase 레벨 (`phases/<phase>/index.json`)

```json
{
  "steps": [
    { "step": 1, "name": "domain-model", "status": "pending", "summary": null },
    { "step": 2, "name": "repository",   "status": "pending", "summary": null }
  ],
  "execution": {
    "developer_model": "sonnet",
    "reviewer_model": "opus",
    "committer_model": "haiku",
    "push": true
  },
  "created_at": "2026-06-16T...",
  "completed_at": null
}
```

- `steps`: 이 phase의 step 목차. 각 step의 `status`(`pending`|`completed`|`blocked`|`error`)와 `summary`는
  recorder/finalizer가 갱신한다. **workflow는 `pending`인 step만 실행한다** — `completed`는 건너뛰고,
  `blocked`/`error`로 멈춘 step은 자동 재개하지 않는다. 사람이 원인을 고친 뒤
  `execute.py reset-step <PHASE_DIR> --step N`으로 그 step을 pending으로 되돌려야 재실행 시 다시 잡힌다.
  (안 고친 채 재실행해 같은 실패를 반복하며 토큰을 낭비하지 않도록, reset을 명시적 신호로 요구한다.)
- `execution`: agent별 모델과 push 여부. preflight가 이 값을 workflow 인자로 옮긴다.
  `push`는 `true`로 기록한다 — Execution은 PR 오픈으로 끝나고 PR은 push된 브랜치에만 열 수 있다.
  로컬에서만 돌려 볼 때는 index를 고치지 말고 finalize에 `--no-push`를 준다.
- `completed_at`: finalize가 채운다.

### spec 레벨 (`phases/index.json`)

```json
{
  "phases": [
    { "phase": "1-domain", "status": "completed" },
    { "phase": "2-api",    "status": "pending" }
  ]
}
```

finalizer가 phase 완료 시 해당 phase status를 `completed`로 동기화한다.

### workflow-checklist.json (Stage 진행 + 실행 전 게이트)

`harness` workflow의 10개 Stage 진행을 기록한다. **spec 레벨에 하나** 두며(`<spec>/workflow-checklist.json`, spec 폴더 바로 아래),
Specify(2)에서 worktree를 만들 때 템플릿 폴더에서 복사해 만든다. 항목 제목은 `SKILL.md`의 Workflow 제목과 정확히 일치해야 한다.

```json
{
  "workflow": "harness",
  "status": "drafting",
  "items": [
    { "order": 1, "group": "명세", "title": "Interview", "status": "completed" },
    { "order": 2, "group": "명세", "title": "Specify", "status": "completed" },
    { "order": 3, "group": "명세", "title": "Clarify", "status": "completed" },
    { "order": 4, "group": "명세", "title": "Scenarios", "status": "completed" },
    { "order": 5, "group": "명세", "title": "Design", "status": "completed" },
    { "order": 6, "group": "변환·검증", "title": "Steps", "status": "completed" },
    { "order": 7, "group": "변환·검증", "title": "Analyze", "status": "completed" },
    { "order": 8, "group": "실행", "title": "Execution", "status": "pending" },
    { "order": 9, "group": "실행", "title": "PR Review", "status": "pending" },
    { "order": 10, "group": "실행", "title": "Root Sync", "status": "pending" }
  ]
}
```

**실행 전 게이트**: `preflight`가 이 파일을 검사한다. **Execution(8) 직전 단계(1~7)가 모두 `completed`이고 Stage 8이
`pending`/`in_progress`가 아니면 preflight가 거부**하여(`{"ok": false, ...}`) workflow가 기동되지 않는다.
즉 탐색·논의·설계·문서작성을 건너뛰고 곧바로 구현에 돌입하는 것을 기계적으로 막는다.

필드 규칙:
- `workflow`: 항상 `harness`
- `items`: `SKILL.md`의 1~10번 Stage 순서·제목을 그대로 사용(order/title 일치 필수). `group`은 표시용이며 검증 대상이 아니다.
- Stage 1~6은 진행하며 작성·갱신한다. Stage 7(Analyze)은 `close-analyze`만 `completed`로 만든다.
- `Execution`(8)은 **메인이 Stage 8 자동 흐름으로 갱신**한다 — 진입 시 `set-stage … in_progress`, phase 루프를 다 돈 뒤 `set-stage … completed`를 자동 호출(spec 단위 1회씩). `PR Review`(9)·`Root Sync`(10)은 리뷰 결과·승격 완료를 사람이 확인한 시점에 `set-stage`로 갱신한다. preflight·finalize는 phase 단위라 이 Stage들을 건드리지 않는다(기계가 spec 레벨 Stage를 자기 판단으로 바꾸지 않는다).
- 단 10은 9가 `completed`된 뒤에만 갱신한다(리뷰 코멘트 부재를 9 완료로 보지 않는다). Stage 10이 마지막이며, 이후 merge는 사람이 수동으로 한다.
- 이 파일은 로컬 추적용이다(진행 상태라 `.gitignore` 대상 — 6장 참고).

### analysis.json (Analyze 판정 + 항목별 처리)

Analyze(7)의 검사관 여섯이 낸 JSON 블록을 메인이 모아 spec 레벨에 하나 둔다(`<spec>/analysis.json`).
`close-analyze`가 이 파일을 보고 Stage 7을 닫고, `preflight`가 `fingerprint`로 분석이 낡았는지 본다.

```json
{
  "generated_at": "2026-07-28T14:00:00+09:00",
  "closed_at": null,
  "inspectors": ["traceability", "domain", "concurrency", "access", "rules", "clarity"],
  "findings": [
    {
      "id": "D1",
      "category": "상태 전이",
      "severity": "CRITICAL",
      "location": "data-model.md",
      "summary": "취소 상태에서 빠져나오는 전이가 없다",
      "recommendation": "재예약이 새 건인지 같은 건의 복귀인지 확정한다",
      "reported_by": [
        { "inspector": "domain", "severity": "CRITICAL" },
        { "inspector": "clarity", "severity": "MEDIUM" }
      ],
      "carried_disposition": null,
      "disposition": null
    }
  ],
  "not_applicable": {
    "concurrency": ["단일 사용자 조회 흐름이라 경합 자원이 없다"]
  },
  "coverage": [
    { "key": "FR-001", "scenarios": ["SCN-001"], "steps": ["step2"], "note": "" }
  ],
  "fingerprint": {}
}
```

필드 규칙:
- `severity`는 `reported_by` 중 **가장 높은 값**이다. 낮춰 적으면 게이트가 열린다.
- `reported_by`의 심각도가 엇갈리면 그것이 검사관 간 이견이다. 합치면서 지우지 않는다.
- `disposition`은 triage 결과다. `null`(미처리) / `{"kind":"fixed"}` / `{"kind":"rejected","reason":"..."}`.
  **CRITICAL은 `reason`이 있는 `rejected`만 `close-analyze`를 통과한다.**
- `carried_disposition`은 이전 분석에서 근거와 함께 반려된 항목을 다시 발견했을 때 그 근거를 옮긴 것이다.
- `fingerprint`는 `close-analyze`가 쓴다 — 판정 대상 문서(`spec.md`·`plan.md`·`scenarios.md`·설계 md·`step<N>.md`)의 내용 해시. 진행 상태 파일은 넣지 않는다(실행 중 바뀐다).
- `coverage`는 추적성 검사관만 채운다.

---

## 3. step 문서와 Acceptance Criteria 스키마

step 문서(`stepN.md`)는 자유 형식의 구현 지시 + `## 검증 대상` + `## Acceptance Criteria` 섹션으로
구성된다.

### `## 검증 대상` (이 step이 무엇을 확인하나)

이 step이 확인하는 **시나리오를 목록으로 밝히고, 각 시나리오가 나온 요구사항·완료 기준을 괄호로
덧붙이는** 절이다. 없으면 어떤 요구가 어느 step에서 검증되는지 대조할 수 없고, 계약으로 표시한 것이
조용히 빠진 것을 아무도 잡지 못한다.

```markdown
## 검증 대상
- SCN-004 전날 23:59 예약 성공 (FR-003)
- SCN-005 자정 정각 거절 (FR-003)
- SCN-010 동시 100건에서 중복 0건 (SC-002)
```

- **`## 관련 문서`와 다르다** — 그쪽은 읽을 문서, 이 절은 확인할 대상이다. 한 절에 섞지 않는다.
- 괄호 안의 요구는 시나리오 산출물에서 그대로 옮긴다. 어긋나면 시나리오 산출물이 맞다.
- 시나리오에 식별자 서식이 없는 저장소라면 확인할 경우를 문장으로 적는다. 형식은 활성 방법론이 정한다.
- **시나리오로 표현되지 않는 step**(순수 리팩터·마이그레이션 등)은 요구사항·완료 기준을 직접 적거나
  "기존 동작 유지"를 명시한다. 비워 두지 않는다.
- **여기 적은 식별자는 문서 안에만 둔다.** 코드·테스트 이름·주석에 옮기지 않는다 — spec은 작업 후
  아카이브되고 코드만 남아 그 식별자가 나중 독자에게 의미를 잃는다.
- reviewer가 이 목록을 짚어 대응하는 검증이 추가됐는지 본다. 대응은 테스트 케이스 단위이며, 파라미터화
  테스트 하나가 여러 경우를 덮어도 된다.

### Acceptance Criteria 파싱 규칙 (verify-ac가 따르는 실제 규칙)

- `## Acceptance Criteria` 헤더부터 다음 `## ` 헤더(또는 문서 끝)까지가 AC 본문.
- 그 안의 ` ```bash ` 또는 ` ```sh ` 코드블록의 **각 줄**이 명령 후보.
- 빈 줄은 무시.
- **`# expect: N`** 형태의 주석은 **바로 다음 명령**의 기대 exit code를 지정한다.
- 그 외 `#` 주석은 무시.
- 기대 exit를 지정하지 않은 명령의 기본 기대값은 **0**.
- 명령은 **워크트리 루트에서 셸로 실행된다.** 그래서 파일 경로는 **저장소 루트 기준 상대경로**로 쓴다
  (`src/...`·`build.gradle` 처럼). 머신마다 다른 절대경로(홈 디렉터리로 시작하는 경로 등)를 쓰지 마라 —
  다른 머신·다른 워크트리에서 깨지고, 개인 경로가 아카이브되는 spec 문서에 그대로 남는다.

### 예시

```markdown
## Acceptance Criteria

​```bash
<테스트 실행 명령> <Money 관련 테스트만 고르는 인자>
# expect: 1
test -f src/.../<삭제됐어야 하는 파일>
​```
```

- 첫 명령(테스트 실행): 기대 exit 0 (지정 없음) → 테스트가 통과해야 ok.
- 둘째 명령 `test -f src/...` + `# expect: 1`: **파일이 없어야** ok
  (있으면 `test -f`가 0을 반환하는데 기대는 1이므로 실패). "이 파일이 삭제됐어야 한다"를 표현.
  경로가 저장소 루트 기준 상대경로인 점에 주의한다.

> 테스트·빌드 명령은 그 프로젝트가 쓰는 것을 그대로 적는다 — 하네스는 특정 빌드 도구를 전제하지 않고,
> 셸에서 실행되는 명령과 기대 exit code만 본다. `# expect:`로 기대 exit를 명시하면 위 둘째처럼
> "없어야 한다"(exit 1 기대) 류 AC도 표현된다.

### 동시성 정합 요구의 AC

동시 실행 시의 정합을 요구하는 step은 실제 저장소를 쓰고 병행 실행으로 경합을 일으키는 테스트를 AC 명령으로 둔다. 대역으로 바꾼 단위·부분 테스트만으로 통과시키지 않는다. 테스트 작성 방식은 이 저장소가 지정한 규칙 문서를 따른다.

---

## 4. AC 검증 결과 (`stepN-ac-output.json`)

verify-ac가 실행할 때마다 그 attempt 결과를 누적 기록한다(감사용). 구조:

```json
{
  "step": 1,
  "attempts": [
    {
      "attempt": 1,
      "passed": false,
      "results": [
        { "command": "<테스트 명령>", "expectExit": 0, "actualExit": 1, "ok": false }
      ]
    },
    { "attempt": 2, "passed": true, "results": [ ... ] }
  ]
}
```

- `passed`: 그 attempt의 모든 명령이 기대 exit와 일치했는가.
- `results[].ok`: 명령별 `actualExit == expectExit` 여부.
- verify-ac는 첫 실패에서 멈추지 않고 **모든 명령을 끝까지 실행**해 전체 실패 상황을 한 번에 보여준다.
- AC가 없는 step이면 `{ "passed": true, "no_ac": true }` 형태를 반환한다.

reviewer는 이 파일의 최신 attempt를 읽어 developer의 자기보고와 대조한다(불일치 시 retryable_error).

---

## 5. agent 반환 JSON 계약

workflow(JS)는 각 agent의 반환 JSON으로 분기한다. agent는 **마지막 행동으로 해당 JSON만** 출력한다.

### developer
```json
{
  "step": 1, "attempt": 1,
  "status": "completed | blocked | error",
  "summary": "<완료한 변경 한 줄. 빈 문자열 금지>",
  "blocked_reason": "<blocked/error일 때 사람이 판단할 것. 아니면 null>",
  "struggles": "<버린 접근·막힌 점·ADR 충돌 처리. 없으면 null>",
  "ac": { "passed": true, "results": [ ... verify-ac 출력 ... ] }
}
```

### reviewer
```json
{ "step": 1, "decision": "approved | retryable_error | blocked", "message": "<사유>" }
```
- `approved`가 기본. `retryable_error`는 한 문장으로 짚을 수 있는 구체적 결함(또는 AC 정합 불일치).
  `blocked`는 사람 개입이 반드시 필요할 때만(드물게).

### committer
```json
{ "committed": true, "commits": ["feat: ...", "test: ..."] }
```
- workflow는 이 보고를 신뢰하고 엄격 검증하지 않는다. 안전망은 finalizer + `git status`.

### recorder (stdout JSON)
```json
{ "ok": true, "step": 1, "status": "completed" }
```

### finalizer (stdout JSON)
```json
{ "ok": true, "pushed": false, "branch": "...", "push_skipped": true }
```

> JSON 형식 보장: 기본은 **프롬프트 계약**(agent가 "이 JSON만 출력")이고, workflow의 `parseAgentJson`이
> 코드펜스·앞뒤 설명을 견고하게 벗겨 파싱한다. 런타임이 `schema` 강제를 지원하면(trial 확인 후)
> 그 위에 스키마 검증을 얹는다(`execute.js`의 `SUPPORTS_SCHEMA`).

---

## 6. 실행 산출물 vs 정본

**`<SPEC_ROOT>/<spec-name>/` 아래에서 `.gitignore` 대상은 진행 상태·실행 부산물뿐이다.** spec 정본은 Stage 8 진입 때 한 번 커밋되고, Root Sync(10)에서 `_archive/pr-<번호>-<spec명>/`로 옮겨진다. 그 사이 as-built 수정은 그것을 만든 step 커밋에 함께 들어간다.

- **함께 사라지는 것**: `index.json`·`workflow-checklist.json`(진행 상태), `step<N>-ac-output.json`·`logs/`(실행 부산물). 추적되지 않아 작업 폴더를 비울 때 없어진다.
- **`_archive`로 옮기는 것**: 그 밖의 모든 `.md` — `spec.md`·`plan.md`·`architecture.md`·`data-model.md`·`db-schema.md`·`api-spec.md`·`adr.md`·`scenarios.md`·`interview.md`·`research.md`·`step<N>.md` 중 작성된 것. 그리고 `analysis.json` — 무엇을 발견하고 왜 그렇게 처리했는지를 나중에 되짚을 유일한 근거다.

보존 가치가 있는 결정·계약은 Root Sync에서 루트 문서로도 승격된다.

| 파일 | 누가 쓰나 | 누가 읽나 |
|---|---|---|
| `phases/<phase>/index.json`, `phases/index.json` | recorder(step status) / finalizer(completed_at·spec index) | preflight·재실행 skip 판단 |
| spec 문서 (spec·plan·architecture·data-model·db-schema·api-spec·adr·scenarios) | developer/사람 | reviewer·Root Sync 승격 |
| `stepN-ac-output.json` | verify-ac(attempt마다 append) | reviewer(자기보고 대조) |
| `logs/<role>.log` | 로깅 hook | 사람(사후 분석·디버깅) |

- developer/recorder/committer/finalizer는 자기 영역 밖의 정본을 건드리지 않는다.
- phase index는 committer가 staging하지 않는다(진행 상태라 `.gitignore`에 걸려 잡히지 않는다). finalizer가 phase 끝에 워킹트리 상태로 동기화한다.
- **`stepN-output.json`은 만들지 않는다.** 결과를 agent
  반환값으로 받고 검증은 ac-output.json·git·log·index가 대신하므로 읽는 주체가 없다(dead artifact 회피).
