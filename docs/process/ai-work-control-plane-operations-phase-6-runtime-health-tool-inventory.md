# AI Work Control Plane Operations Phase 6: Runtime Health + Tool Inventory

## Goal

Surface provider/runtime/tool health as control-plane input without implementing a new provider bridge.

## Work

- Add runtime health and tool inventory placeholders to StrategyDecision and EvidenceBundle.
- Preserve setup/degraded capability language and usage/cost placeholders.
- Keep `direct_api` records-only for tool intent/result/fallback/usage; it must not bypass approved-plan execution gates.

## Targeted Test

```bash
pytest tests/test_messages.py tests/test_control_plane.py tests/test_cli.py tests/test_team.py -q
```

## Result

Pending targeted validation.
