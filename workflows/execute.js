// 실행 오케스트레이션 (엔진, 방법론 무관).
// 플러그인 안에서 meta.name 기준으로 /spec-harness:execute 로 실행된다.
// 번들된 agent는 네임스페이스가 붙는다: spec-harness:developer, spec-harness:reviewer, ...

export const meta = {
  name: 'execute',
  description: 'phase 오케스트레이션 — step별 dev→AC→review→commit→record, 끝에 finalize',
  phases: [{ title: 'Execute' }],
}

// phase의 각 step을 순서대로: developer → (AC 통과) → reviewer → committer → recorder
// 모든 step 완료 후 finalizer 1회.
//
// <!-- 상세 로직 자리표시. 핵심 골격만 표기: -->
//
// for (const step of steps) {
//   const dev = await agent(devPrompt(step),      { agentType: 'spec-harness:developer' })
//   if (dev.ac?.passed !== true) { /* 재시도 */ }
//   const rev = await agent(reviewPrompt(step),   { agentType: 'spec-harness:reviewer'  })
//   if (rev.verdict !== 'approved') { /* 재시도/중단 */ }
//   await agent(commitPrompt(step),               { agentType: 'spec-harness:committer' })
//   await agent(recordPrompt(step),               { agentType: 'spec-harness:recorder'  })
// }
// await agent(finalizePrompt(),                   { agentType: 'spec-harness:finalizer' })
//
// 방법론이 활성이면, 그 방법론의 검사·agent(예: spec-harness:domain-expert)는
// Analyze 단계(별도)에서 소환된다. 이 실행 루프 자체는 방법론 무관하다.
