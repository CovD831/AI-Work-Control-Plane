# ADR 0001: Documentation As Runtime Context

## Status

Accepted

## Context

Agent Orchestrator depends on agents that need current project knowledge during long-running work. Static docs are not enough when planning, execution, compliance, and recovery all need the same source of truth.

## Decision

Treat canonical documentation as runtime context. `team inspect-docs` and session-level docs context snapshots provide agent-ready context packages while preserving canonical docs as the source of truth.

## Consequences

- Agents can resume work with explicit document evidence instead of implicit memory.
- Session artifacts record which docs were used for a task.
- Full document content remains query output; persisted snapshots store ids, paths, freshness, relevance, and hashes.

## Related Commands

- `python -m agent_orchestrator.cli team inspect-docs --query "<task>"`
- `python -m agent_orchestrator.cli team check-compliance`
