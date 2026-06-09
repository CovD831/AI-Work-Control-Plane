# Agent Evolution Master Plan

## Purpose

This plan evolves the repository from a governance-first orchestration runtime into a governance-first agent system with a stronger decision plane and richer execution collaboration.

The plan keeps one non-negotiable rule:

- the control plane remains the system of record for state, approvals, evidence, memory provenance, and recovery

Everything else is allowed to evolve in controlled phases.

## Execution Protocol

- Every phase must start with a short phase plan under `docs/process/`.
- Every phase plan must include scope, implementation steps, acceptance criteria, and targeted tests.
- Implement only the current phase.
- Run targeted tests for the current phase before advancing.
- Advance to the next phase only after targeted tests pass.
- Run full `pytest` and `team check-compliance` only at final convergence.
- Do not introduce a second state source outside control-plane artifacts.

## Architectural Direction

The repository will evolve toward four layers:

1. `Control Plane`
   durable state, approvals, evidence, memory provenance, recovery, auditability
2. `Decision Plane`
   routing, topology choice, candidate comparison, reroute, rescue, rejection reasons
3. `Execution Plane`
   planner / builder / reviewer / critic / reflector collaboration
4. `Interop Plane`
   future protocol adapters such as A2A-style envelopes and external agent integration

The near-term implementation focus is:

`Decision Plane + Execution Plane`, while preserving the current control-plane baseline.

## Phase Sequence

### Phase 0: Current-State Baseline

Define the current system precisely: governance-first workflow runtime with multi-role semantics, not a fully autonomous multi-agent system.

Targeted tests:

```bash
pytest tests/test_docs_process.py -q
```

### Phase 1: Decision Externalization

Expand routing, topology, and reroute/rescue output so the system records candidate options, selected decisions, and rejected alternatives.

Targeted tests:

```bash
pytest tests/test_routing.py tests/test_orchestrator.py tests/test_control_plane.py -q
```

### Phase 2: Structured Collaboration Objects

Upgrade handoff-centric communication into structured collaboration objects such as `proposal`, `critique`, `verdict`, `blocker`, `recovery_option`, and `reflection`.

Targeted tests:

```bash
pytest tests/test_messages.py tests/test_work_graph.py tests/test_team.py -q
```

### Phase 3: Multi-Role Review System

Split review into clearer roles and aggregate review output through structured verdicts and severity-aware findings.

Targeted tests:

```bash
pytest tests/test_review.py tests/test_team.py tests/test_cli.py -q
```

### Phase 4: Limited Multi-Path Reasoning

Introduce candidate generation and bounded consensus for judgment-heavy nodes such as strategy choice, review verdict, recovery recommendation, and root-cause diagnosis.

Targeted tests:

```bash
pytest tests/test_routing.py tests/test_orchestrator.py tests/test_team.py -q
```

### Phase 5: Recovery Search

Upgrade reroute/rescue from fixed branching into bounded recovery search with explicit branch evaluation.

Targeted tests:

```bash
pytest tests/test_orchestrator.py tests/test_control_plane.py tests/test_team.py -q
```

### Phase 6: Retrieval Governance

Add retrieval quality assessment, source conflict tracking, and fallback retrieval for docs, evidence, and memory-backed context assembly.

Targeted tests:

```bash
pytest tests/test_planning_support.py tests/test_evidence.py tests/test_docs_process.py -q
```

### Phase 7: Semi-Autonomous Role Contracts

Turn role slots into semi-autonomous units with structured inputs, outputs, blockers, alternatives, and requests for information.

Targeted tests:

```bash
pytest tests/test_team.py tests/test_messages.py tests/test_work_graph.py -q
```

### Phase 7.5: Surface Convergence

Converge the expanded decision/execution metadata into a narrower product boundary before adding any new runtime substrate.

Targeted tests:

```bash
pytest tests/test_docs_process.py -q
```

### Phase 8: LangGraph Execution Runtime Pilot

Pilot LangGraph only as a local execution runtime for a bounded subflow. The control plane remains the source of truth.

Targeted tests:

```bash
pytest tests/test_team.py tests/test_orchestrator.py tests/test_control_plane.py -q
```

### Phase 9: A2A-Style Interop Adapter

Add an adapter layer that maps internal control-plane contracts to external A2A-style envelopes without replacing the internal message system.

Targeted tests:

```bash
pytest tests/test_messages.py tests/test_control_plane.py tests/test_cli.py -q
```

### Final Convergence

Run final repository-wide gates, then refresh roadmap, runbook, architecture, and evidence docs to match the evolved system.

Final gates:

```bash
pytest
env PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
git status --short
```

## Completion Bar

The plan is complete when:

- the control plane still owns durable truth
- the decision plane exposes explicit alternatives and rationale
- the execution plane supports structured collaboration rather than only linear handoffs
- recovery and retrieval are evidence-backed and auditable
- role contracts, work-graph enrichments, and CLI summaries remain projections of canonical control-plane state rather than a second source of truth
- optional LangGraph and A2A-style integrations exist only as bounded adapters, not as competing system cores
