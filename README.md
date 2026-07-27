# spec-harness

명세를 먼저 확정하고, 그 명세가 구현을 끌고 가는 SDD(Spec-Driven Development) 하네스.
Claude Code 플러그인으로 배포한다.

## 구성 (3층)

- **엔진** — 방법론 무관 프로세스. `skills/`(진입) + `agents/`(루프 역할) + `workflows/`(실행 오케스트레이션).
- **방법론(opt-in)** — `methodologies/<name>/`. 켜면 그 방법론의 검사·agent·템플릿이 얹힌다. 안 켜면 코어만 돈다.
- **인스턴스(이 플러그인 밖)** — 각 repo가 제공한다. 활성 방법론 목록, 강제 도구 바인딩(정적 분석·아키텍처 테스트 등), 스택·컨벤션 값. 플러그인에는 담지 않는다.

## 설치

```
/plugin marketplace add <이 repo 주소>
/plugin install spec-harness@my-harness
```

## 사용

- 진입: `/spec-harness:run`
- 실행 워크플로: `/spec-harness:execute`
- 방법론은 각 repo가 활성 목록에 넣어 opt-in한다(예: `[ddd]`). 아무것도 안 넣으면 코어만 동작.

## 버전 관리

`plugin.json`의 `version` + git 태그로 관리한다. 새 버전은 내용을 고치고 version을 올리는 커밋/태그이며,
사용하는 repo는 `/plugin update`로 받는다.
