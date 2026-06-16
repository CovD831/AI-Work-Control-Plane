# 治理控制台操作手册

## Operations Track

- Operations Track
- Comparative Proof Strength
- repeatability posture
- evidence compare
- current_version_assessment

## Happy Path

- `team start`
- `team status`
- `team summary`
- `team next`
- `team runbook`
- `team resume`
- `team roles`
- `team chat`
- `team draft-ready`
- `team revise`
- `team approve`
- `team execute`
- `team inspect-execution`
- `team inspect-blockers`
- `team inspect-docs`
- `team inspect-handoff`
- `team inspect-knowledge`
- `team workspace-status`
- `team context-packet`
- `team topology inspect`
- `team task next`
- `team task list`
- `team submit-review`
- `team approvals list`
- `team approvals resolve`
- `team evidence-gates`
- `team check-compliance`
- `team setup`

## Recovery

- `team retry-review`
- `team retry-adversarial-review`
- approval_state
- required outputs
- topology_reason
- fallback_reason
- fallback_detail
- operator projection 不是新的 durable state
- 不要直接编辑底层 JSON

## Roles

- `lead`: `team summary`, `team next`, `team runbook`
- `planner`: `team chat`, `team draft-ready`, `team task next`
- `builder`: `team execute`, `team inspect-execution`
- `reviewer`: `team submit-review`, `team retry-review`, `team task list`
- `adversarial_reviewer`: `team submit-review`, `team retry-adversarial-review`
- `validator`: `team task next`, `team inspect-blockers`
- `rescue`: `team inspect-blockers`, `team retry-review`, `team retry-adversarial-review`
- `approval_gate`: `team approvals list`, `team approvals resolve`
- `runtime`: `team inspect-execution`, `team workspace-status`
- `state_keeper`: `team status`, `team context-packet`
- `strategist`: `team summary`, `team topology inspect`
- `topology_compiler`: `team topology inspect`, `team workspace-status`
- `evidence_recorder`: `team evidence-gates`, `team summary`
- `memory_curator`: `team inspect-knowledge`, `team context-packet`
- `context_compressor`: `team inspect-docs`, `team docs-index`

## 场景

- 场景 A：happy path from plan to execute
- 场景 B：approval / blocker / recovery
- 场景 C：evidence / workspace / docs / compliance convergence

## 相关文档

- `docs/process/native-coding-agent-dogfood-evidence.md`
- `docs/process/ai-work-control-plane-operations-dogfood-evidence.md`
- `docs/process/ai-work-control-plane-live-recovery-dogfood-evidence.md`
