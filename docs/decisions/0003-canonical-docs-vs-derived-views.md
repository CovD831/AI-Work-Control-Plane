# ADR 0003: Canonical Docs Vs Derived Views

## Status

Accepted

## Context

The repository now produces process docs, context packages, evidence reports, knowledge records, and planned index views. Without clear ownership, derived outputs can drift into competing sources of truth.

## Decision

Canonical docs remain in README, process docs, architecture docs, module manifests, file-header contracts, and ADRs. Context snapshots, docs index results, evidence reports, and handoff packets are derived views or artifacts.

## Consequences

- `team refresh-docs` may update managed process docs but must not overwrite ADR content.
- Derived views can be regenerated and inspected without becoming the canonical product narrative.
- Compliance should protect links between canonical docs and derived artifacts.

## Related Commands

- `python -m agent_orchestrator.cli team refresh-docs`
- `python -m agent_orchestrator.cli team docs-index --query "<task>"`
