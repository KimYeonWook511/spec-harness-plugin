# PR Review

Execution(8, 실행)에서 오픈한 PR에 달린 review를 처리한다.

이 단계는 기본적으로 **사용자가 PR을 검토하는 단계**다. 메인 에이전트는 Execution(8)에서 PR을 연 뒤 멈추고 사용자의 검토 완료 신호를 기다린다(사용자가 요청하면 agent가 검토·반영을 위임받을 수 있다).

**Root Sync(10, 루트 문서 반영) 진입 게이트** — 아래를 분명히 구분한다.

- **리뷰 코멘트가 없다는 것은 PR Review 완료가 아니다.** 리뷰가 뒤늦게 코드를 바꾸면 미리 만든 Root Sync 산출물이 어긋난다.
- **Stage 9(PR Review) 완료**는 다음 둘 중 하나다. (1) 사용자가 검토를 종료했다고 알린 경우(코멘트 처리 완료 포함), (2) 사용자가 명시적으로 agent에 검토를 위임했고 그에 따른 반영이 끝난 경우.
- Stage 9(PR Review) 완료가 확인되기 **전에는** Stage 10(Root Sync)을 시작하지 않는다. 완료가 확인된 뒤에야 Root Sync(10)를 진행하며, 그 단계는 메인 에이전트가 자동으로 처리해도 된다. Root Sync가 끝나면 harness는 종료하고, merge는 사람이 수동으로 한다.

review 처리 방식:

- 사람이 review 코멘트(예: GitHub에 연결한 코드리뷰 봇, 또는 다른 리뷰어)를 보고 항목별 처리 방향(accept / reject / modify)을 **결정**한다.
- 결정에 따른 코드 수정·답변·thread resolve는 **사람이 이 단계에서 직접 수행**한다(실행 워크플로 바깥). 수정 커밋·push는 Stage 8(Execution)에서 오픈한 같은 브랜치/같은 PR에 쌓는다. committer는 Stage 8에서 실행 워크플로가 부르는 에이전트라 이 Stage에 관여하지 않는다.
- review 수정이 API/구조/결정을 바꿨다면 Stage 10(Root Sync)에서 그 변경을 루트에 반영한다. 내부 구현만 바뀐 경우 루트 동기화가 불필요할 수 있다.
