# spec-harness

명세를 먼저 확정하고, 확정된 명세대로 구현하게 하는 Claude Code 플러그인.

- 틀리면 데이터·돈·권한이 깨지는 곳은 추측으로 채우지 않고 사용자에게 묻는다.
- 통과 기준은 실행 명령이다. step마다 Acceptance Criteria 명령을 돌려 exit code로 판정한다.
- 구현한 에이전트와 검토하는 에이전트가 다르다.

## 어떤 skill을 쓰나

| 상황 | skill |
| --- | --- |
| 한 저장소에서 명세부터 구현까지 | `/spec-harness:run` |
| 여러 저장소(서버·앱)가 한 제품을 만든다: docs 저장소에서 기능 spec 확정·동결 | `/spec-harness:feature` |
| 위의 구현 저장소에서 동결된 기능 spec을 가져와 구현 | `/spec-harness:implement` |
| 끝난 작업의 실행 기록에서 반복되는 실패 찾기 | `/spec-harness:retro` |
| 흐름과 내가 개입할 지점 안내 | `/spec-harness:guide` |

## run의 흐름

| 묶음 | 단계 | 하는 일 |
| --- | --- | --- |
| 명세 | 1 Interview | 기존 코드·문서를 읽고 요청을 파악한다 |
| | 2 Specify | `spec.md`에 요구와 완료 기준을 쓴다 |
| | 3 Clarify | 모호한 곳을 사용자와 확정한다 |
| | 4 Scenarios | 요구마다 어떻게 확인할지 정한다 |
| | 5 Design | 설계 문서와 phase를 정한다. 여기서 요구와 불변 시나리오가 동결된다 |
| 변환·검증 | 6 Steps | step으로 나누고 step마다 AC를 쓴다 |
| | 7 Analyze | 검사관 여섯이 문서를 나눠 검사한다 |
| 실행 | 8 Execution | 실행 워크플로가 step마다 구현 → AC → 검토 → 커밋을 돈다 |
| | 9 PR Review | 사람이 PR을 검토한다 |
| | 10 Root Sync | 루트 문서에 반영하고 spec 폴더를 `_archive/`로 옮긴다 |

명세 묶음은 며칠에 걸쳐 진행해도 된다. 진행 상태는 spec 폴더의 `workflow-checklist.json`에 남고, 다음 세션은 끝나지 않은 단계부터 이어 간다.

주요 게이트는 스크립트가 막는다. 예를 들어 처리하지 않은 CRITICAL이 있거나, 검사한 뒤 문서가 바뀌었으면 실행이 시작되지 않는다. 단계별 조건은 `skills/run/SKILL.md`의 게이트 표에 있다.

## 저장소를 나눌 때

```
docs 저장소   feature: 기능 spec → 검사 → 계약 → 검사 → 동결(태그 F01-v1)
                                                            │
구현 저장소   implement: 가져오기(upstream/, 읽기만) → 범위 → 검증 매핑 → 설계 → 검사 → step → 실행
```

- 요구·시나리오·계약은 docs 저장소에서 한 번 정하고, 각 구현 저장소는 그 버전을 읽기만 한다.
- 구현하다 기능 spec을 바꿔야 하면 docs 저장소에서 버전을 올리고 다시 가져온다.
- 동작이나 계약이 바뀌지 않는 내부 작업(리팩터, 성능, 로깅)은 구현 저장소에서 `run`으로 한다.

자세한 흐름은 `skills/feature/SKILL.md`, `skills/implement/SKILL.md`에 있다.

## 설치

나만 쓸 때:

```
/plugin marketplace add KimYeonWook511/spec-harness-plugin
/plugin install spec-harness@KimYeonWook511-harness
/reload-plugins
```

팀이 같이 쓸 때는 저장소의 `.claude/settings.json`에 등록한다.

```bash
claude plugin marketplace add KimYeonWook511/spec-harness-plugin --scope project   # 터미널에서
```

```
/plugin install spec-harness@KimYeonWook511-harness   # 세션에서, project scope 선택
/reload-plugins
```

`.claude/settings.json`에 아래 두 키가 모두 있으면 된다. 설치 과정에서 `extraKnownMarketplaces`가 지워지는 경우가 있으니 커밋 전에 확인한다.

```json
{
  "extraKnownMarketplaces": {
    "KimYeonWook511-harness": {
      "source": { "source": "github", "repo": "KimYeonWook511/spec-harness-plugin" }
    }
  },
  "enabledPlugins": { "spec-harness@KimYeonWook511-harness": true }
}
```

새 버전은 `/plugin marketplace update KimYeonWook511-harness`로 받는다.

## 저장소 설정

설정이 없어도 동작한다. 이때 규칙 문서는 `CLAUDE.md`만 읽는다. 바꾸고 싶은 것만 `.spec-harness/config.json`에 적고 커밋한다.

```json
{
  "rule_docs": ["docs/coding-rules.md"],
  "commit_rule_docs": ["docs/commit-rules.md"],
  "spec_root": "docs/specs",
  "methodologies": ["bdd"],
  "workspace": { "base_ref": "develop", "branch_pattern": "<type>/<name>" }
}
```

| 키 | 뜻 |
| --- | --- |
| `rule_docs` | `CLAUDE.md` 말고 규칙으로 읽을 문서. `{"path": ..., "section": "## 핵심 원칙"}`이면 그 절만 읽는다 |
| `commit_rule_docs` | 커밋 메시지 규칙 문서 |
| `reference_docs` | step 문서가 언급할 때만 함께 읽는 참고 문서 |
| `template_dir` | spec 문서 템플릿을 저장소 것으로 쓸 때 (기본은 플러그인 내장) |
| `spec_root` | spec 폴더 위치 (기본 `docs/specs`) |
| `feature_root` | docs 저장소의 기능 spec 폴더 위치 (기본 `features`) |
| `upstream` | implement용. `path`는 docs 저장소의 로컬 경로, `on_newer_compatible`은 minor 새 버전이 있을 때 `warn`(기본) 또는 `block` |
| `methodologies` | 켤 방법론. `ddd`(도메인 규칙을 어디 둘지), `bdd`(시나리오를 검증 단위로) |
| `workspace` | `mode`(`worktree` 기본 · `branch`), `base_ref`(기본은 저장소 기본 브랜치), `branch_pattern`·`worktree_pattern`(`<type>`·`<name>` 치환), `types`(허용할 작업 종류) |
| `merge.agent` | Root Sync 전에 에이전트가 머지하려 할 때: `ask`(기본) · `root_sync`(막음) · `deny`(모든 머지 막음) |

`.gitignore`에는 진행 상태와 실행 부산물만 넣는다. spec 문서는 PR에서 보이도록 커밋한다.

```gitignore
/.spec-harness/run/
docs/specs/**/workflow-checklist.json
docs/specs/**/phases/index.json
docs/specs/**/phases/*/index.json
docs/specs/**/phases/*/step*-ac-output.json
docs/specs/**/phases/*/logs/
```

docs 저장소는 `/.spec-harness/run/`과 `features/*/workflow-checklist.json`만 넣는다.

## 구성

| 경로 | 내용 |
| --- | --- |
| `skills/` | run · feature · implement · retro · guide |
| `workflows/execute.js` | 실행 워크플로 |
| `agents/` | 검사관 6 (`analyzer-*`), 실행 에이전트 5 (`developer` · `reviewer` · `committer` · `recorder` · `finalizer`), `domain-expert` |
| `methodologies/` | 켜서 쓰는 방법론 (`ddd`, `bdd`) |
| `hooks/` | 실행 로그 기록, Root Sync 전 머지 확인 |
