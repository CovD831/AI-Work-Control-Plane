# AI Work Control Plane Runtime Bridge Phase 0: Baseline

## Goal

Start the Runtime Bridge Fidelity Track after Live Recovery and pin the product boundary before implementation.

## Baseline

- Live Recovery already provides Recovery Timeline, Runtime Event Stream, Recovery Recommendation, workspace recovery dashboard fields, recovery-backed memory candidates, and dogfood evidence.
- The remaining runtime gap is not "build a full bridge"; it is session fidelity: liveness, operation receipts, continuation/attach support, degraded reasons, and recovery-safe next commands.
- Existing `CommandJobRuntime`, `FileJobRuntime`, job records, and control-plane runtime events are the implementation base.

## Boundaries

- No full Codex/Claude bridge product.
- No persistent session manager.
- No direct-API patch engine or local tool loop.
- No React Flow editor.
- No provider ping-pong loop.

## Targeted Tests

```bash
pytest tests/test_docs_process.py tests/test_planning_support.py -q
```
