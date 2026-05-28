# AI Work Control Plane v1 Final Externalization Hardening

## Goal

Close the gap between local control-plane visibility and external governance review.

The target is not a provider-native bridge. The target is a portable, read-only governance artifact that can be exported from the workspace and inspected offline without mutating plans, resuming work, or claiming ownership of provider sessions.

## Implementation

- Add `agent_orchestrator.governance_bundle.v1`.
- Add `agent_orchestrator.governance_bundle_inspection.v1`.
- Add `team governance-bundle export --output <path>`.
- Add `team governance-bundle inspect <bundle_path>`.
- Bundle the current read-only governance surfaces:
  - workspace index;
  - context packet;
  - evidence bundle;
  - approval queue;
  - provider evidence summary.
- Include an artifact manifest and explicit externalization/boundary statements.

## Boundary

- Bundle export is read-only.
- Bundle inspection is read-only.
- Provider-owned refs remain evidence only.
- Token/cost remains placeholder unless a provider reports usage directly.
- The bundle does not imply plugin marketplace distribution support.

## Validation

Targeted validation already run for the implementation pass:

```bash
pytest tests/test_control_plane.py::test_governance_bundle_exports_portable_externalized_artifacts tests/test_cli.py::test_team_governance_bundle_export_and_inspect_json tests/test_docs_process.py::test_control_plane_artifact_contracts_document_stable_formats tests/test_docs_process.py::test_release_readiness_mentions_provider_evidence_summary -q
pytest tests/test_control_plane.py tests/test_cli.py tests/test_docs_process.py -q
```

Observed targeted validation:

- Focused governance bundle tests: 4 passed.
- `pytest tests/test_control_plane.py tests/test_cli.py tests/test_docs_process.py -q`: 127 passed.

Real CLI validation:

```bash
PYTHONPATH=src python -m agent_orchestrator.cli team governance-bundle export --output .agent_orchestrator/governance/v1-final-externalization-bundle.json --query "v1 final externalization hardening" --changed-file src/agent_orchestrator/control_plane.py --changed-file src/agent_orchestrator/cli.py --format json
PYTHONPATH=src python -m agent_orchestrator.cli team governance-bundle inspect .agent_orchestrator/governance/v1-final-externalization-bundle.json --format json
```

Observed inspect result:

- `format`: `agent_orchestrator.governance_bundle_inspection.v1`
- `bundle_format`: `agent_orchestrator.governance_bundle.v1`
- `complete`: true
- `auditable`: true
- `blocking`: false
- `blocking_reasons`: []
- `warnings`: []

The exported bundle reflects the current uncommitted working tree during this validation pass. That is acceptable for implementation validation; release evidence should be regenerated after the final commit if a clean committed bundle is needed.

## Final Gate

Run before calling this hardening pass closed:

```bash
pytest tests/test_control_plane.py tests/test_cli.py tests/test_docs_process.py -q
pytest
PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
git status --short
```

## Result

Final validation passed on 2026-05-28:

- `pytest tests/test_control_plane.py tests/test_cli.py tests/test_docs_process.py -q`: 127 passed.
- `PYTHONPATH=src python -m agent_orchestrator.cli team governance-bundle export --output .agent_orchestrator/governance/v1-final-externalization-bundle.json --query "v1 final externalization hardening" --changed-file src/agent_orchestrator/control_plane.py --changed-file src/agent_orchestrator/cli.py --format json`: exit 0.
- `PYTHONPATH=src python -m agent_orchestrator.cli team governance-bundle inspect .agent_orchestrator/governance/v1-final-externalization-bundle.json --format json`: complete true, auditable true, blocking false.
- `pytest`: 423 passed.
- `PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance`: status passed, blocking false.

The project now has an externalized governance path:

```text
current workspace governance state
  -> portable governance bundle
  -> offline inspection verdict
  -> explicit boundary summary
```

This reaches the externalized governance target for v1 when paired with passing full tests and compliance. It still intentionally stops short of provider-native session orchestration.
