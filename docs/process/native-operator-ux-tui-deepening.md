# Native Operator UX / TUI Deepening

This note records the post-productization operator UX projection. It does not introduce a full Desktop/Web product, provider marketplace, plugin ecosystem, or public release path.

## Stable Operator Surfaces

- CLI pretty posture: `agent-orchestrator product posture`
- CLI setup diagnosis: `agent-orchestrator product diagnose`
- CLI evidence summary: `agent-orchestrator product evidence`
- CLI smoke summary: `agent-orchestrator product smoke`
- Dashboard/service health: `DashboardService.health()["native_product_ux"]`
- Dashboard/session detail: `DashboardService.get_session(...)["native_product_ux"]`
- Operator summary: `operator_summary.native_product_ux`
- Evidence bundle: `build_evidence_bundle(...)["native_product_ux"]`

## Shared Fact Chain

All surfaces consume the same `agent_orchestrator.native_product_ux_snapshot.v1` contract. The snapshot includes:

- product posture and active goal
- latest run status
- provider/runtime posture and fix hints
- authoritative OpenCode instrumentation closure
- operator decision
- blocker / recovery reason
- next action and recommended commands

## Operator Decision Standard

An operator should be able to answer without reading raw JSON:

1. Is the native daily-driver candidate usable now?
2. Is provider/runtime setup ready or degraded?
3. Is instrumentation closed, partially closed, or still blocking?
4. What blocker/recovery reason is active?
5. What is the next product action?

## Non-Goals

- full Desktop/Web implementation
- provider marketplace
- plugin ecosystem
- public release automation
- expanding OpenCode harness schemas
