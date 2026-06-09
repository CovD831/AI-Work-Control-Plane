# Agent Evolution Phase 6: Retrieval Governance

## Goal

Add retrieval-quality governance to context assembly so the control plane records not only what context was selected, but also why it was considered good enough.

## Scope

- extend context packets with retrieval assessment
- record source freshness, authority, and relevance summaries
- record source conflict and evidence support summaries
- keep context packet assembly read-only and backward-compatible

## Non-Goals

- no new external retriever
- no dynamic re-query loop
- no role autonomy changes yet

## Implementation Steps

1. Add retrieval assessment fields to context packets.
2. Score selected docs and memory records using existing local metadata.
3. Add conflict/support summaries based on selected context sources.
4. Add tests for retrieval governance payload shape.

## Acceptance Criteria

- context packets include a retrieval assessment summary
- retrieval assessment records freshness, authority, and relevance summaries
- context packets include source conflict and evidence support summaries
- existing context packet output remains compatible
- targeted tests for control-plane context assembly and docs/process checks pass

## Targeted Tests

```bash
pytest tests/test_control_plane.py tests/test_docs_process.py tests/test_cli.py -q
```

## Exit Condition

Advance to Phase 7 only after targeted tests pass and retrieval governance fields are visible in context packets.
