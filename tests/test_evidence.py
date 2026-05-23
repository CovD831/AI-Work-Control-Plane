# DEPS: agent_orchestrator, json, pathlib
# RESPONSIBILITY: Verify workflow evidence harness output and persisted artifact shape.
# MODULE: tests
# ---

from __future__ import annotations

import json

from agent_orchestrator.evidence import capture_workflow_evidence
from test_support import write_minimal_process_docs


def test_capture_workflow_evidence_records_team_advantages_and_writes_json(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    output_path = tmp_path / "evidence" / "workflow.json"

    payload = capture_workflow_evidence(
        ["Build a persisted plan artifact"],
        project_root=tmp_path,
        output_path=output_path,
    )

    assert output_path.exists()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written == payload
    assert payload["summary"]["case_count"] == 1
    assert payload["summary"]["team_cases_with_execution_run"] == 1
    case = payload["cases"][0]
    assert "approved_plan_artifact" in case["comparison"]["team_advantages"]
    assert "execution_provenance" in case["comparison"]["team_advantages"]
    assert "recovery_guidance" in case["comparison"]["team_advantages"]
    assert "no_approved_plan_artifact" in case["comparison"]["direct_limitations"]
    assert case["team_workflow"]["approved_plan_source"] == "approved_plan_session"

