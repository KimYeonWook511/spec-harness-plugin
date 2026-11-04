# 검사 범위 (Design Review · Analyze)

검사관 프롬프트에 공통 계약 경로와 함께 아래 블록을 넣는다.

## Design Review

```
검사 범위: 구현 설계 (Design Review)
읽을 문서: <S>/upstream/ 전체(읽기만), <S>/spec.md, <S>/verification.md, <S>/plan.md와 작성된 설계 문서
보지 않는 것: step·AC (아직 없다), 상위 요구 자체의 옳고 그름 (docs 저장소의 몫)
```

| 검사관 | 질문 |
| --- | --- |
| traceability | 이번 범위의 상위 시나리오가 `verification.md`에 모두 매핑됐나. 매핑된 검증이 설계로 실제 확인 가능한가 |
| domain | 설계가 `upstream/domain/`의 상태·전이·불변식을 깨지 않나. `불변` 시나리오를 만족할 수 있나 |
| access | 설계가 계약의 엔드포인트별 "누가"를 그대로 지키나 |
| concurrency | (서버) 계약의 요청 규칙(멱등·재시도·반영 지연)을 설계가 지킬 수 있나. (앱) 재시도 때 계약이 정한 키·순서를 지키나 |
| rules | 저장소 규칙 문서 위반. 플랫폼 요구(`P-FR`)가 상위 요구를 바꾸거나 약하게 만들지 않나 |
| clarity | (서버) 계약의 모든 오류·상태값을 낼 수 있나. (앱) 계약의 모든 오류·상태값에 화면 반응이 있나 |

상위 요구 자체가 틀렸다고 보이면 발견으로 올리되 `recommendation`은 "docs 저장소에 기능 변경 요청"으로 쓴다. 이 저장소에서 고치라고 권하지 않는다.

## Analyze에 더하는 것

run의 Analyze 검사 범위에 아래를 더한다.

- traceability: 사슬의 출발점은 상위 요구다. **상위 요구 → 상위 시나리오 → `verification.md` → step `## 검증 대상` → AC**가 끊긴 곳을 본다. 플랫폼 시나리오(`P-SCN`)도 step에 대응해야 한다.
- 읽을 문서에 `<S>/upstream/`과 `verification.md`를 넣는다.
