export const meta = {
  name: 'execute',
  description: 'phase 오케스트레이션 — step별 dev→AC→review→commit→record, 끝에 finalize',
  phases: [
    { title: 'Implement', detail: 'step마다 구현→검증→검토→커밋→기록' },
    { title: 'Finalize', detail: 'completed_at·spec index 동기화·push' },
  ],
};

// spec-harness:execute — phase 오케스트레이터 (dynamic workflow)
//
// 한 번 기동으로 phase를 끝까지 완주한다: 미완 step부터 순차로 developer→(AC확인)→reviewer
// →committer→recorder 를 돌리고, 모든 step이 끝나면 finalizer로 phase를 닫는다.
// 실제 shell/git/fs 작업은 전부 agent가 execute.py 서브커맨드를 통해 한다. 이 스크립트는 조율만.
//
// 입력(args): execute.py preflight가 만든 객체.
//   { phase_dir, phase_relpath, phase, execute,
//     steps: [{step, name, status}], execution: {developer_model, reviewer_model, committer_model, push} }
// 결과: return 으로 outcome 객체를 돌려준다.

// 한 step의 시도 상한. 형식 오류·AC 미통과·재검토 요청을 합쳐 센다.
const MAX_RETRIES = 3;

// agent 호출 래퍼 — opts(agentType/model/label/phase)를 여기 한 곳에서 조립.
// 반환 형식은 각 agent 문서의 계약 + parseAgentJson으로만 보장한다.
async function callAgent(agentType, model, prompt, label, phaseName) {
  const opts = { agentType };
  if (model) opts.model = model;
  if (label) opts.label = label;
  if (phaseName) opts.phase = phaseName;
  return await agent(prompt, opts);
}

// agent 반환을 객체로. 이미 객체면 그대로, 문자열이면 코드펜스·앞뒤설명 벗겨 JSON.parse.
function parseAgentJson(raw) {
  if (raw && typeof raw === 'object') return raw;
  if (typeof raw !== 'string') return null;
  let text = raw.trim();
  const fence = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (fence) text = fence[1].trim();
  const first = text.indexOf('{');
  const last = text.lastIndexOf('}');
  if (first !== -1 && last !== -1 && last > first) text = text.slice(first, last + 1);
  try { return JSON.parse(text); } catch { return null; }
}

// ── 프롬프트 빌더 ───────────────────────────────────────────────
function commonVars(a, step, attempt) {
  return [
    `EXECUTE: ${a.execute}`,
    `PHASE_DIR: ${a.phase_dir}`,
    `STEP: ${step.step}`,
    `ATTEMPT: ${attempt}`,
  ].join('\n');
}

function developerPrompt(a, step, attempt, prevError) {
  let p = `${commonVars(a, step, attempt)}\n\n`
    + `step ${step.step}(${step.name})을 구현하라. 위 EXECUTE/PHASE_DIR/STEP/ATTEMPT 값을 사용한다.\n`
    + `먼저 build-context로 컨텍스트를 로드하고, 구현을 마친 뒤 verify-ac로 AC를 검증한 다음, `
    + `약속된 JSON 한 개만 반환하라.`;
  if (prevError) {
    p += `\n\n## 이전 시도 실패\n${prevError}\n같은 실패를 반복하지 않도록 원인을 해결한 뒤 진행하라.`;
  }
  return p;
}

function reviewerPrompt(a, step, attempt, dev) {
  return `${commonVars(a, step, attempt)}\n\n`
    + `step ${step.step}(${step.name})의 변경을 read-only로 검토하라.\n\n`
    // 워크플로는 파일을 못 읽으므로 reviewer가 직접 열게 한다.
    + `## 먼저 읽을 것 (판정 근거)\n`
    + `1. \`<PHASE_DIR>/step${step.step}.md\` — 이 step의 구현 지시·\`## 검증 대상\`·\`## Acceptance Criteria\`.\n`
    + `2. \`<PHASE_DIR>/step${step.step}-ac-output.json\` — AC 실행 결과 정본. 아래 developer 보고와 대조하라.\n`
    + `(PHASE_DIR는 위에 전달된 값이다.)\n\n`
    + `git status/diff로 변경 범위를 직접 파악하라.\n\n`
    + `## developer 보고\n`
    + `- summary: ${dev.summary || ''}\n`
    + `- struggles: ${dev.struggles || '(없음)'}\n`
    + `- ac.passed: ${dev.ac ? dev.ac.passed : '(없음)'}\n\n`
    + `약속된 판정 JSON 한 개만 반환하라.`;
}

function committerPrompt(a, step, attempt, dev) {
  return `${commonVars(a, step, attempt)}\n\n`
    + `reviewer가 승인한 step ${step.step}(${step.name})의 변경을 이 저장소의 커밋 규칙에 따라 목적별로 커밋하라.\n`
    + `developer summary: ${dev.summary || ''}\n`
    + `약속된 결과 JSON 한 개만 반환하라.`;
}

function recorderPrompt(a, step, status, summary, reason) {
  return `${commonVars(a, step, 0)}\n`
    + `STATUS: ${status}\nSUMMARY: ${summary || ''}\nREASON: ${reason || ''}\n\n`
    + `record-step으로 위 step의 상태를 phase index에 기록하라. 결과 JSON을 그대로 반환하라.`;
}

function finalizerPrompt(a) {
  return `EXECUTE: ${a.execute}\nPHASE_DIR: ${a.phase_dir}\n`
    + `NO_PUSH: ${a.execution && a.execution.push === false ? 'true' : 'false'}\n\n`
    + `phase의 모든 step이 끝났다. finalize로 phase를 마무리하라(completed_at·spec index 동기화·push). `
    + `결과 JSON을 그대로 반환하라.`;
}

// ── 한 step 처리: 성공이면 {ok}, blocked/error면 {stopped} 반환 ──
async function runStep(a, step) {
  const devModel = a.execution && a.execution.developer_model;
  const revModel = a.execution && a.execution.reviewer_model;
  const comModel = a.execution && a.execution.committer_model;
  let prevError = null;

  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    const tag = `step${step.step}`;

    // 1) developer
    const dev = parseAgentJson(await callAgent(
      'spec-harness:developer', devModel, developerPrompt(a, step, attempt, prevError), `${tag}:developer`, 'Implement'));
    if (!dev || !dev.status) {
      prevError = 'developer 반환 JSON 파싱 실패 — 약속된 JSON 한 개만 출력해야 한다.';
      continue;
    }
    if (dev.status === 'blocked' || dev.status === 'error') {
      return { stopped: dev.status, step: step.step, reason: dev.blocked_reason || 'developer가 중단 보고', summary: dev.summary };
    }
    if (!dev.ac || dev.ac.passed !== true) {
      const failed = dev.ac && Array.isArray(dev.ac.results)
        ? dev.ac.results.filter(r => !r.ok).map(r => `${r.command} (기대 ${r.expectExit}, 실제 ${r.actualExit})`).join('; ')
        : 'AC 미통과';
      prevError = `AC 미통과: ${failed}`;
      continue;
    }

    // 2) reviewer
    const rev = parseAgentJson(await callAgent(
      'spec-harness:reviewer', revModel, reviewerPrompt(a, step, attempt, dev), `${tag}:reviewer`, 'Implement'));
    if (!rev || !rev.decision) {
      prevError = 'reviewer 반환 JSON 파싱 실패.';
      continue;
    }
    if (rev.decision === 'blocked') {
      return { stopped: 'blocked', step: step.step, reason: rev.message || 'reviewer가 blocked 판정', summary: dev.summary };
    }
    if (rev.decision === 'retryable_error') {
      prevError = `reviewer 재시도 요청: ${rev.message || ''}`;
      continue;
    }
    if (rev.decision !== 'approved') {
      prevError = `알 수 없는 reviewer 판정(${rev.decision}) — 자동 승인하지 않는다.`;
      continue;
    }

    // 3) committer (결과 신뢰, 엄격 검증 없음)
    const com = parseAgentJson(await callAgent(
      'spec-harness:committer', comModel, committerPrompt(a, step, attempt, dev), `${tag}:committer`, 'Implement')) || { committed: false, commits: [] };

    // 4) recorder — 정본 index에 completed 기록
    const rec = parseAgentJson(await callAgent('spec-harness:recorder', null,
      recorderPrompt(a, step, 'completed', dev.summary, null), `${tag}:recorder`, 'Implement'));
    if (!rec || rec.ok !== true) {
      // 기록이 안 되면 재실행 시 이미 구현된 step을 다시 돈다. 커밋은 이미 남았으므로 사람이 확인해야 한다.
      return {
        stopped: 'error', step: step.step, summary: dev.summary,
        reason: `step ${step.step}의 커밋은 끝났지만 phase index 기록이 실패했다`
          + `(${(rec && rec.error) || 'recorder 반환을 파싱하지 못했다'}). `
          + `index.json의 step ${step.step} status를 확인하고 필요하면 record-step으로 직접 기록하라.`,
      };
    }

    return { ok: true, step: step.step, summary: dev.summary, commits: com.commits || [] };
  }

  return { stopped: 'error', step: step.step, reason: `${MAX_RETRIES}회 시도 후 실패: ${prevError || ''}` };
}

// ── 본문 (top-level) ────────────────────────────────────────────
// 실측(trial): args는 이 런타임에서 JSON '문자열'로 주입된다(객체가 아님).
// 문자열이면 parse, 이미 객체면 그대로. 깨진 입력은 명확히 실패시킨다.
let a;
if (typeof args === 'string') {
  try { a = JSON.parse(args); }
  catch (e) { return { outcome: 'error', reason: `args JSON 파싱 실패: ${e.message}`, raw_args: args }; }
} else if (args && typeof args === 'object') {
  a = args;
} else {
  return { outcome: 'error', reason: `args가 비어 있거나 형식이 잘못됨(type=${typeof args}).` };
}
if (!a || !Array.isArray(a.steps)) {
  return { outcome: 'error', reason: 'args.steps가 배열이 아니다. preflight 출력(JSON)을 args로 넘겼는지 확인하라.', got_keys: a ? Object.keys(a) : null };
}

const results = [];

phase('Implement');
let stopped = null;
for (const step of a.steps) {
  // pending인 step만 실행한다. completed는 건너뛰고, blocked/error는 사람의 reset-step을 기다리며 멈춘다.
  if (step.status === 'completed') {
    results.push({ step: step.step, skipped: true });
    continue;
  }
  if (step.status !== 'pending') {
    // blocked / error 등 — 사람의 reset을 기다리는 상태. 여기서 멈춘다.
    stopped = {
      stopped: step.status,            // 'blocked' | 'error' | 기타
      step: step.step,
      reason: `step ${step.step}이(가) '${step.status}' 상태다. 원인을 고친 뒤 `
        + `\`execute.py reset-step <PHASE_DIR> --step ${step.step}\`로 pending으로 되돌리고 재실행하라. `
        + `(고치지 않은 채 재실행하면 같은 실패가 반복되므로 자동 재개하지 않는다.)`,
      needs_reset: true,
    };
    break;
  }
  const r = await runStep(a, step);
  results.push(r);
  if (r.stopped) {
    // 이번 실행에서 blocked/error 발생 → 그 상태를 정본에 기록하고 중단
    await callAgent('spec-harness:recorder', null,
      recorderPrompt(a, { step: r.step }, r.stopped, r.summary || '', r.reason),
      `step${r.step}:recorder`, 'Implement');
    stopped = r;
    break;
  }
}

if (stopped) {
  return {
    outcome: stopped.stopped,            // 'blocked' | 'error'
    stopped_at_step: stopped.step,
    reason: stopped.reason,
    needs_reset: stopped.needs_reset || false,
    completed_steps: results.filter(x => x.ok || x.skipped).map(x => x.step),
  };
}

// 모든 step 완주 → finalize
phase('Finalize');
const fin = parseAgentJson(await callAgent(
  'spec-harness:finalizer', null, finalizerPrompt(a), 'finalize', 'Finalize')) || {};

if (fin.ok !== true) {
  return {
    outcome: 'error',
    phase: a.phase,
    reason: `phase 마무리(finalize)가 실패했다: ${fin.error || 'finalizer 반환을 파싱하지 못했다'}. `
      + `step은 모두 끝났으므로 원인을 고친 뒤 finalize만 다시 실행하면 된다.`,
    completed_steps: results.filter(x => x.ok || x.skipped).map(x => x.step),
    finalize: fin,
  };
}

return {
  outcome: 'completed',
  phase: a.phase,
  completed_steps: results.filter(x => x.ok || x.skipped).map(x => x.step),
  finalize: fin,
};
