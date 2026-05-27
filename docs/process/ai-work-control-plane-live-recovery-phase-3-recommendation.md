# AI Work Control Plane Live Recovery Phase 3: Recovery Recommendation

## Goal

Add a read-only recovery recommendation builder and expose it through `team next --format json`.

## Work Items

- Add a recovery recommendation payload that explains current blocking reason, safest next operator command, required approval or evidence, recoverable artifact refs, resume eligibility, human-decision requirement, and compliance-first requirement.
- Keep the recommendation read-only; it never executes recovery.
- Keep `team approvals resolve` records-only.
- Add `--format json` support to `team next` without changing the pretty output contract.

## Targeted Tests

```bash
pytest tests/test_control_plane.py tests/test_cli.py tests/test_planning_support.py tests/test_team.py -q
```

## Result

Pending targeted validation.
