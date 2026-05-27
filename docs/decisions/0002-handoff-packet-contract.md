# ADR 0002: Handoff Packet Contract

## Status

Accepted

## Context

Long-running agent work needs compact handoffs between lead, reviewer, builder, runtime, and rescue roles. Free-form summaries are useful for people but hard to validate or reuse.

## Decision

Every structured handoff uses `agent_orchestrator.handoff_packet.v1` with summary, changes, evidence, risks, blockers, docs context snapshot id, recommended commands, and timestamps.

## Consequences

- Handoffs become inspectable through CLI and message artifacts.
- Operator output can stay compact while preserving full packet details in JSON.
- Compliance can distinguish legacy handoffs from execution handoffs that must carry structured context.

## Related Commands

- `python -m agent_orchestrator.cli team inspect-handoff <session_id>`
- `python -m agent_orchestrator.cli team runbook <session_id>`
