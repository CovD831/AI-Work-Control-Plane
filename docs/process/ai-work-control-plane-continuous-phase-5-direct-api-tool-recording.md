# AI Work Control Plane Continuous Phase 5: Direct API Tool Recording

## Goal

Record direct-api tool-loop intent and results without adding a local patch engine.

## Implementation Plan

- Add a stable direct-api tool trace message payload.
- Record intent, result, fallback, and usage/cost placeholders.
- Keep actual execution behind approved-plan gates and existing runtimes.

## Targeted Tests

- `pytest tests/test_messages.py tests/test_team.py tests/test_cli.py -q`
