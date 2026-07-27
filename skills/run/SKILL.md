---
name: run
description: SDD 하네스 진입점. 탐색→Specify→Clarify→Plan→Analyze→Execution→PR→RootSync를 이끈다. 활성 방법론(ddd 등)의 검사·agent·템플릿을 조합해 적용하며, 방법론은 방법론 무관 코어 프로세스 위에 opt-in으로 얹힌다.
---

# SDD 하네스 (엔진)

명세를 먼저 확정하고, 확정된 명세가 구현을 끌고 가는 SDD 워크플로우의 진입점이다.
이 skill과 그 agent·workflow는 **방법론 무관 코어**다 — 특정 설계·검증 방법론을 전제하지 않는다.

## 단계 파이프라인
탐색 → Specify → Clarify → Plan+Tasks → Analyze → Execution → PR → Root Sync.

<!-- 각 단계의 상세 절차·게이트 정의가 여기 들어간다 (phase/step/AC 계약은 references/phase-files.md). -->

## 방법론 적용 (opt-in)
1. 이 repo의 **활성 방법론 목록**을 읽는다(인스턴스 설정. 없으면 코어만).
2. 각 활성 방법론의 `methodologies/<name>/manifest.yaml`을 읽어 조합한다:
   - `requires_in_spec` → Specify/Clarify에서 그 산출물을 요구.
   - `templates` → Plan에서 사용 가능하게.
   - `agents` → consult(설계 단계 대화)·review(Analyze 검토)로 소환.
   - `adds_checks` → Analyze에 추가.
   - `requires`/`conflicts_with` → 활성 목록끼리 충돌 검증.
3. `enforcement: instance-defined`인 검사는 **이 repo의 바인딩**(강제 도구)에 위임한다. 플러그인은 "무엇을"만 정하고 "어떻게"는 repo가 정한다.

## 강제 범위
- **코어 게이트**(경계·구조·정합성)는 방법론과 무관하게 항상 적용.
- **방법론 게이트**는 그 방법론이 활성일 때만. 방법론은 게이트를 추가·완화만 하며 코어를 끄지 못한다.
