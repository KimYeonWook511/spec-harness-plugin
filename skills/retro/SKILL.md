---
name: retro
description: 끝난 spec들의 실행 기록을 돌아보고 반복되는 실패를 규칙으로 고칠 때 이 skill을 쓴다. "회고", "하네스 회고", "spec 회고해줘", "지난 작업 돌아보자", "같은 지적이 계속 나와", "검사관 오탐이 많아", "reviewer가 자꾸 되돌려", "피드백 반영해줘" 같은 요청이 해당한다. spec을 만들거나 실행하는 것은 `run`, 사용법 안내는 `guide`다.
---

# 회고

끝난 spec의 실행 기록에서 **반복되는 실패**를 찾아, 다음 spec이 같은 이유로 되돌아가지 않게 규칙을 고친다. 10 Stage의 단계가 아니며 게이트도 없다. 변경은 사용자 확인 뒤에만 반영하고, 이 확인은 메인 에이전트가 지킨다.

## 자리표시자

- **`<SPEC_ROOT>`** — `.spec-harness/config.json`의 `spec_root`, 없으면 `docs/specs`.
- **`<SKILL_DIR>`** — 이 skill의 base directory 절대경로.
- **`<PLUGIN_DIR>`** — `<SKILL_DIR>`에서 두 단계 위.

## 재료

| 재료 | 무엇을 알 수 있나 |
| --- | --- |
| `execution-history.json` | step별 시도와 결과, reviewer 지적, developer의 `struggles`, 실패한 AC 명령 |
| `analysis.json` | 검사관 발견, 사람의 처리와 반려 근거, 검사관 사이 이견 |
| PR 리뷰 코멘트 | reviewer가 통과시켰는데 사람이 잡은 결함 |
| `<SPEC_ROOT>/_retro/*.md` | 이전 회고에서 반영·보류한 것 |
| 사용자 피드백 | 기록에 남지 않은 불편 |

시도 결과(`outcome`) 값과 `runs`의 뜻은 `<PLUGIN_DIR>/skills/run/references/phase-files.md`의 phase `index.json` 절에 있다.

## 절차

### 1. 범위를 정하고 집계한다

사용자에게 범위를 묻는다. spec 하나로는 반복을 가를 수 없으므로 기본은 최근 5개다.

```bash
python3 "<SKILL_DIR>/scripts/collect.py" --archive-root <SPEC_ROOT> --last 5
```

Root Sync 전인 spec을 넣으려면 먼저 이력을 만든 뒤 폴더를 직접 넘긴다.

```bash
python3 "<PLUGIN_DIR>/skills/run/scripts/execute.py" export-history <SPEC_ROOT>/<spec-name>
python3 "<SKILL_DIR>/scripts/collect.py" <SPEC_ROOT>/<spec-name>
```

`missing`에 `execution_history: false`로 나온 spec은 `analysis.json`만으로 본다. 그 사실을 기록에 남긴다.

### 2. 집계 밖의 재료를 읽는다

- 아카이브 폴더 이름 `pr-<N>-<spec>`의 PR에서 리뷰 코멘트를 읽는다(`gh pr view <N> --comments`, 인라인 코멘트는 `gh api repos/{owner}/{repo}/pulls/<N>/comments`). `gh`를 쓸 수 없으면 건너뛰고 기록에 적는다.
- `<SPEC_ROOT>/_retro/`의 이전 기록을 읽는다.
- 사용자에게 덧붙일 피드백이 있는지 묻는다. 없으면 강요하지 않는다.

### 3. 신호를 찾는다

`review_retry`의 `detail`, `struggles`, 반려 근거, PR 코멘트는 문장이라 같은 원인끼리 직접 묶는다. **서로 다른 step이나 spec에서 2회 이상** 나온 원인만 신호로 본다. 1회는 관찰로 기록만 한다.

| 신호 | 뜻하는 것 | 반영처 |
| --- | --- | --- |
| 같은 취지의 `review_retry`가 반복된다 | developer가 모르는 저장소 규칙이 있다 | 인스턴스: `rule_docs` |
| 같은 ADR·규칙과의 충돌이 `struggles`에 반복된다 | 그 결정이 현실과 어긋난다 | 인스턴스: ADR 갱신을 사람에게 제안 |
| 같은 명령의 `ac_failed`가 반복된다 | AC 작성이나 실행 환경이 맞지 않는다 | 인스턴스: 설정·환경 / 엔진: Steps 지침 |
| 같은 category의 발견이 반복해서 반려된다 | 검사관 오탐 | 엔진: 해당 `analyzer-*` |
| 반려한 발견이 나중에 실행 실패나 PR 지적으로 돌아온다 | 반려 판단이 틀렸다 | 기록: 그 category를 반려할 때의 기준 |
| PR 리뷰가 잡은 결함을 reviewer가 승인했다 | reviewer의 사각 | 엔진: `reviewer` |
| `*_format`이 반복된다 | 반환 계약이 지켜지지 않는다 | 엔진: 해당 agent 정의 또는 모델 선택 |
| 같은 이유의 `*_blocked`가 반복된다 | 명세 묶음에서 확정했어야 할 것이 넘어왔다 | 엔진: Clarify 점검 항목 / 인스턴스: `rule_docs` |

인스턴스 반영처로 `rule_docs`를 먼저 고르는 이유: 한 곳에 적으면 developer(구현), `analyzer-rules`(Analyze), reviewer(검토)가 모두 읽는다.

### 4. 반영안을 만든다

신호마다 근거(spec·step·발견 id), 원인, 고칠 규칙 한 문장과 그 이유, 반영처를 적는다.

- **사례가 아니라 원인을 고친다.** "이 API에 페이지네이션 테스트가 빠졌다"가 반복되면 "목록 API는 경계값 테스트를 넣는다"처럼 원리로 적는다.
- **이유를 함께 적는다.** 이유가 있어야 예외 상황에서도 판단이 선다.
- **이전 회고와 상충하면 알린다.** 지난번에 줄인 것을 이번에 늘리자는 식이면 사용자에게 보이고, 둘 다 만족하는 기준을 찾는다.

### 5. 사용자 확인 뒤 하나씩 반영한다

- **인스턴스**: 저장소 문서를 고친다. 새 규칙 문서를 만들면 `.spec-harness/config.json`의 `rule_docs`에도 추가한다. 추가하지 않으면 아무 에이전트도 읽지 않는다. 커밋은 저장소의 커밋 규칙을 따르고 사용자 확인 뒤에 한다.
- **엔진**: `<PLUGIN_DIR>` 아래 파일은 고치지 않는다. 설치 캐시라 업데이트 때 덮이고 팀에 공유되지 않는다. 대상 파일과 제안 문장을 기록의 "엔진 변경안"에 남겨 플러그인 저장소로 가져가게 한다.

### 6. 기록한다

`<SPEC_ROOT>/_retro/<YYYY-MM-DD>.md`에 남긴다. 다음 회고가 이것을 읽어 같은 판단을 되풀이하지 않는다.

```markdown
# 회고 <YYYY-MM-DD>

범위: <아카이브 폴더 목록> · 이력 없음: <폴더 목록>

## 반영한 것
| 신호 | 근거 | 바꾼 것 | 이유 |
| --- | --- | --- | --- |

## 엔진 변경안
| 대상 파일 | 근거 | 제안 |
| --- | --- | --- |

## 반영하지 않은 것
| 신호 | 이유 |
| --- | --- |

## 관찰 (1회)
- <다음 회고에서 반복되는지 볼 것>
```

### 7. 보고한다

사용자에게 다음을 알린다: 본 범위, 찾은 신호, 반영한 것과 바꾼 파일, 엔진 변경안, 반영하지 않은 것과 그 이유, 기록 경로.
