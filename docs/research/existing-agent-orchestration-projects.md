# Existing Agent Orchestration Projects

This note summarizes what we should learn from nearby Claude/Codex orchestration projects before evolving this repository beyond the MVP mock adapters.

## Projects Reviewed

- `openai/codex-plugin-cc`: brings Codex review/rescue/delegation into Claude Code.
- `pejmanjohn/cc-plugin-codex`: brings Claude Code review/rescue/delegation into Codex.
- `kingbootoshi/codex-orchestrator`: lets Claude Code spawn and manage parallel Codex CLI jobs through tmux.

## Key Lessons

The plugin projects are mostly **bidirectional tool bridges**:

- They expose review, adversarial review, rescue, setup, status, result, and cancel commands.
- They separate read-only review from mutating rescue/delegation.
- They persist background job state so follow-up commands can resume, inspect, or cancel work.
- They preserve helper output instead of silently rewriting it into the caller's voice.

`codex-orchestrator` is closer to a **parallel execution runtime**:

- Jobs run in detached tmux sessions.
- Each job has an id, prompt, model, reasoning effort, sandbox, cwd, timestamps, status, and captured output.
- The runtime supports send, capture, output, attach, kill, jobs JSON, and turn-complete notifications.
- It treats Codex sessions as long-running conversations that can be redirected instead of killed and respawned.

Our framework should sit above both shapes:

```text
strategy core + task contract
  -> execution plugins for Claude/Codex tools
  -> optional durable job/runtime backends
  -> structured review/rescue results
```

That means we should learn from these projects without trying to absorb their entire product surface. Bridge behavior, background job handling, tmux sessions, and provider-native continuation are important integration points, but they should remain plugin concerns around our core strategy engine.

## Design Implications For This Repo

### 1. Add A Separate Job Runtime

Do not overload the task state machine with process/session lifecycle. A task can be `running` while its external job has richer states such as `pending`, `running`, `idle`, `completed`, `failed`, or `cancelled`.

Recommended job fields:

```json
{
  "id": "job-123",
  "task_id": "work-123",
  "provider": "codex | claude",
  "kind": "review | adversarial_review | rescue | implementation | research",
  "status": "pending | running | idle | completed | failed | cancelled",
  "phase": "starting | working | reviewing | done | failed",
  "prompt": "agent prompt",
  "model": "model name",
  "reasoning_effort": "low | medium | high | xhigh",
  "sandbox": "read-only | workspace-write | danger-full-access",
  "cwd": "workspace root",
  "session_id": "external session id",
  "thread_id": "external thread id",
  "created_at": "ISO timestamp",
  "started_at": "ISO timestamp",
  "completed_at": "ISO timestamp",
  "summary": "short result summary",
  "raw_output": "captured output",
  "parsed_payload": {}
}
```

### 2. Preserve Review Output Boundaries

Both plugin directions treat review output as structured findings. We should add a common review result schema with:

- `verdict`: `approve` or `needs_attention`
- `summary`
- `findings`
- `next_steps`

Each finding should include severity, title, body, file, line range, confidence, and recommendation.

The orchestrator must not auto-fix review findings unless policy explicitly routes the issue into a rescue work unit.

### 3. Keep Read-Only Review Separate From Mutating Rescue

Review jobs should default to read-only sandbox. Rescue and implementation jobs may use workspace-write. This boundary is important for safety, auditability, and user trust.

Recommended mapping:

- `review`: read-only
- `adversarial_review`: read-only
- `research`: read-only
- `implementation`: workspace-write
- `rescue`: workspace-write, unless only diagnosing

### 4. Support Background Job Management Commands

The adapters should expose a shared lifecycle rather than one-shot `execute()` only:

- `start(job_request) -> job`
- `status(job_id) -> job`
- `result(job_id) -> job_result`
- `send(job_id, message) -> job`
- `cancel(job_id) -> job`

This allows long-running Claude/Codex jobs, course correction, and partial progress capture.

This is still an integration boundary, not the core value of the repository. We should support it through pluggable runtime interfaces rather than make background execution completeness the roadmap's main success condition.

### 5. Add Recursion And Delegation Guards

Because `codex-plugin-cc` and `cc-plugin-codex` can point at each other, our policy router needs explicit loop prevention:

- Track delegation chain as provider/kind pairs.
- Enforce `max_depth`.
- Forbid automatic provider ping-pong unless the next step is a different kind of work.
- Require a concrete failure reason before escalating from worker to rescue.

### 6. Use Context Maps When Available

`codex-orchestrator` highlights the value of a `docs/CODEBASE_MAP.md` context map. Our task contract should support optional shared context artifacts, and Codex-style workers should receive them when present.

## What Not To Rebuild

These projects already validate several lower-level concerns:

- bidirectional bridge commands
- background job persistence and session control
- provider-specific continuation flows
- tmux-backed orchestration runtime mechanics

Our repository should avoid repeating those as primary roadmap goals. The differentiated layer should be:

- strategy inputs
- route/review/rescue/replay/reroute decisions
- explainability for why a decision happened
- policy guardrails such as ping-pong, recursion, and budget control

## Recommended Next Implementation Step

Upgrade the strategy-first MVP in this order:

1. Formalize strategy inputs: task, risk, dependency, failure, and budget signals.
2. Formalize strategy outputs: route, review level, rescue mode, replay scope, reroute policy, and stop reason.
3. Add structured explanation fields so runs can justify why a route or escalation happened.
4. Stabilize plugin interfaces for providers, bridges, and job runtimes.
5. Add guardrail tests for depth, ping-pong prevention, and budget-aware stopping.
6. Benchmark `auto` strategy against fixed modes on real task samples.
