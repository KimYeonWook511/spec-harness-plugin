# spec-harness

명세를 먼저 확정하고, 그 명세가 구현을 끌고 가는 SDD(Spec-Driven Development) 하네스.
Claude Code 플러그인으로 배포한다.

## 무엇을 하나

바로 코드를 짜지 않는다. 먼저 명세를 세우고, 모호한 곳은 추측으로 메우지 않고 사용자와 확정한 뒤,
*확정된* 명세만 자동 실행으로 넘긴다. 명세가 상류, 코드가 하류다.

전체는 8단계로 흐른다.

```
탐색 → 명세(Specify) → 모호함 해소(Clarify) → 설계·분해(Plan+Tasks) → 정합성 검사(Analyze)
   → 자동 실행(Execution) → PR Review → 루트 동기화(Root Sync)
```

앞 5단계는 사람이 검토·확정하는 구간이고, 뒤 3단계는 확정된 명세를 코드로 옮겨 루트에 반영하는 구간이다.
위험영역(결제·인증·데이터 모델·상태 전이)은 가정으로 메우지 않고 반드시 확정한 뒤 넘어간다.

## 구성 (3층)

- **엔진** — 방법론 무관 프로세스. `skills/`(진입) + `agents/`(루프 역할) + `workflows/`(실행 오케스트레이션).
- **방법론(opt-in)** — `methodologies/<name>/`. 켜면 그 방법론의 검사·agent·템플릿이 얹힌다. 안 켜면 코어만 돈다.
- **인스턴스(이 플러그인 밖)** — 각 repo가 제공한다. 활성 방법론 목록, 강제 도구 바인딩(정적 분석·아키텍처 테스트 등), 스택·컨벤션 값. 플러그인에는 담지 않는다.

## 구성 요소

- **skill `run`** — 진입점(`/spec-harness:run`). 8단계 프로세스를 지휘한다. 상세 동작과 파일·데이터 계약은 이 skill이 담는다.
- **workflow `execute`** — Stage 6(자동 실행) 오케스트레이터(`/spec-harness:execute`). step마다 구현→검증→검토→커밋→기록을 돌리고, 모든 step이 끝나면 마무리한다.
- **agents (6)** — 실행 루프 역할: `developer`·`reviewer`·`committer`·`recorder`·`finalizer`, 그리고 Analyze 게이트의 `analyzer`.
- **`methodologies/`** — opt-in 방법론(예: `ddd`). 각 방법론은 manifest 하나로 자기 검사·전용 agent·템플릿을 밝힌다.

## 설치

```
/plugin marketplace add KimYeonWook511/spec-harness-plugin
/plugin install spec-harness@KimYeonWook511-harness
```

## 사용

- 진입: `/spec-harness:run`
- 실행 워크플로: `/spec-harness:execute`
- 방법론은 각 repo가 활성 목록에 넣어 opt-in한다(예: `[ddd]`). 아무것도 안 넣으면 코어만 동작한다.

## 저장소 설정 (선택)

하네스는 어느 문서가 그 저장소의 규칙인지 알지 않는다. 규칙으로 읽을 문서는 저장소가 직접 나열한다.
설정이 없으면 문서 주입 없이 코어 흐름만 돈다(오류가 아니다).

`.spec-harness/config.json`:

```json
{
  "rule_docs": [
    { "path": "docs/coding-rules.md", "section": "## 핵심 원칙" },
    "docs/spec-constitution.md"
  ],
  "reference_docs": ["docs/api-spec.md", "docs/db-schema.md"],
  "template_dir": "docs/specs/_template"
}
```

- **`rule_docs`** — 구현 단계에서 **항상 주입**하는 규칙 문서. 문자열이면 문서 전문, 객체면 지정한
  섹션만 넣는다. 섹션 문자열은 저장소가 정하며 하네스는 특정 제목을 전제하지 않는다. 지정한 섹션을
  찾지 못하면 전문을 넣고 그 사실을 컨텍스트에 알림으로 남긴다(규칙이 조용히 빠지지 않게).
- **`reference_docs`** — step 문서가 그 경로를 언급할 때만 주입하는 참고 문서.
- **`template_dir`** — spec 문서 템플릿을 저장소가 자기 것으로 쓰고 싶을 때만 지정한다. 지정이 없거나
  그 경로가 없으면 이 플러그인이 싣고 있는 기본 템플릿을 쓴다. 그래서 템플릿을 준비하지 않은
  저장소에서도 바로 시작할 수 있다.

### .gitignore

하네스는 저장소 파일을 대신 고치지 않는다. 아래 규칙은 저장소가 직접 추가한다.

```gitignore
/.spec-harness/run/     # 실행 중 생기는 진행 마커·로그 상태 (휘발)
docs/specs/*            # 진행 중 spec 작업 공간 (휘발)
!docs/specs/_archive     # 완료 후 승격한 아카이브만 추적
```

`.spec-harness/config.json`은 **커밋한다** — 그 저장소의 규칙 선언이라 팀이 공유해야 한다.
`.spec-harness/` 전체를 무시하면 설정까지 빠져 규칙 주입이 조용히 사라진다.
spec 작업 공간을 추적하지 않는 것은 하네스의 설계다 — 진행 중 문서는 휘발이고, 완료된 spec만
아카이브로 승격해 커밋한다.

## 버전 관리

`plugin.json`의 `version` + git 태그로 관리한다. 새 버전은 내용을 고치고 version을 올리는 커밋/태그이며,
사용하는 repo는 `/plugin update`로 받는다.
