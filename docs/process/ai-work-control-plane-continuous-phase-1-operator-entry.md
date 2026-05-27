# AI Work Control Plane Continuous Phase 1: Operator Entry

## Goal

Make `team summary`, `team next`, and `team runbook` read as control-plane guidance before team choreography.

## Implementation Plan

- Add control-plane focus metadata to strategy decisions.
- Keep workspace, context, topology, approval, and evidence commands stable.
- Keep UI read-only for control-plane artifacts.

## Targeted Tests

- `pytest tests/test_cli.py tests/test_cli_presenters.py tests/test_ui_service.py tests/test_control_plane.py -q`
