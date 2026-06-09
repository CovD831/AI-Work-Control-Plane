# Agent Evolution Phase 2: Structured Collaboration

## Goal

Upgrade the current handoff-centric message flow into a structured collaboration layer.

This phase keeps the existing workflow intact, but makes key collaboration objects explicit so later phases can build better review, recovery, and semi-autonomous coordination on top of them.

## Scope

- add structured collaboration payloads for key collaboration object types
- keep current `handoff`, `review_request`, and `review_result` flows compatible
- expose collaboration metadata through stored messages and work-graph-derived views
- keep all additions backward-compatible

## Non-Goals

- no new routing logic
- no review committee logic yet
- no recovery search tree yet
- no role autonomy changes yet

## Implementation Steps

1. Add a normalized collaboration object payload shape to the message layer.
2. Add helper builders for `proposal`, `critique`, `verdict`, `blocker`, `recovery_option`, and `reflection`.
3. Make existing review/handoff flows emit compatible structured collaboration metadata.
4. Surface collaboration summaries in work-graph-derived views and tests.

## Acceptance Criteria

- messages can persist structured collaboration payloads with a stable format marker
- review requests and review results carry collaboration metadata compatible with the new shape
- new collaboration object types can be created through the message router
- work-graph-derived views expose collaboration-related message context without breaking existing consumers
- targeted tests for messages, work graph, and team flow pass without changing existing operator behavior

## Targeted Tests

```bash
pytest tests/test_messages.py tests/test_work_graph.py tests/test_team.py -q
```

## Exit Condition

Advance to Phase 3 only after targeted tests pass and collaboration payloads are visible in persisted session messages.
