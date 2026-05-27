# AI Work Control Plane Real-Task Dogfood Phase 2: Case Matrix

## Goal

Expand the committed evidence case source from a small v1.x sample into a broader local dogfood matrix.

## Work Items

- Keep existing standard, follow-up, high-risk, parallel, and CLI hardening cases.
- Add UI workflow, compliance blocking, runtime fidelity, and interruption recovery cases.
- Add risk profile, operator goal, expected signals, and runtime expectation metadata to each case.
- Update tests so the repository case source must include the expanded scenario set.

## Targeted Tests

```bash
pytest tests/test_evidence.py -q
```

## Exit Criteria

- `docs/process/evidence-cases.json` contains at least eight real-task cases.
- Each case has label, requirement, scenario type, mode, risk profile, operator goal, expected signals, and runtime expectation.
- Evidence tests pass.
