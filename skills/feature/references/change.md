# 기능 변경

동결된 기능 spec을 고친다. 결과는 새 버전이다. 구현 저장소에서 기능 spec을 몰래 고치지 않고 반드시 이 흐름을 거친다 — 한쪽만 바뀌면 플랫폼 사이가 어긋난다.

## 무엇이 바뀌나에 따라 시작 단계가 다르다

| 바뀌는 것 | 예 | 시작 단계 | 버전 |
| --- | --- | --- | --- |
| 요구·완료 기준·시나리오 | 결정 변경, spec이 정하지 않은 경우가 버그로 드러남 | Clarify (새 요구면 Specify) | major |
| 계약의 뜻 | 플랫폼마다 오류를 다르게 읽음, 상태값 추가 | Contract | major |
| openapi 형태만 (`contract.md` 그대로) | 구현 저장소가 설계하며 필드·경로를 확정 | Contract | minor |

## 진행

1. 변경 이유를 확인한다. 버그에서 시작했으면 "기능 spec이 이 경우를 뭐라고 하나"로 다시 가른다(`SKILL.md`). spec이 분명히 정했는데 코드가 다른 것이면 기능 변경이 아니라 구현 버그다.
2. 새 작업 공간을 만들고 `init-checklist <F> --workflow feature`로 checklist를 만든다.
3. 시작 단계 앞의 단계를 `completed`로 두고, 그렇게 둔 이유(이번 변경이 건드리지 않음)를 사용자에게 알린다.
4. 시작 단계부터 진행한다. 그 뒤의 검사는 다시 돌린다. Contract부터 시작했으면 Spec Review는 다시 돌리지 않아도 된다 — `spec.md`·`scenarios.md`가 그대로면 Contract Review가 닫힌다.
5. Freeze에서 CHANGELOG에 원인과 영향받는 플랫폼을 적는다.

## 구현 저장소가 올린 계약 확정 받기

구현 저장소가 `openapi.yaml` 형태를 확정해 PR로 올리면, `contract.md`와 같은 말을 하는지 대조한다. 같으면 위 표의 셋째 줄(minor)이고, `contract.md`까지 바꿔야 하면 둘째 줄(major)이다.
