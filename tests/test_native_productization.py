# DEPS: agent_orchestrator, pathlib
# RESPONSIBILITY: Verify native productization operator posture, setup diagnosis, smoke result, and evidence consumption surfaces.
# MODULE: tests
# ---

import json
from pathlib import Path

from agent_orchestrator.native_productization import (
    EVIDENCE_CONSUMPTION_VERSION,
    PRODUCT_POSTURE_VERSION,
    SETUP_DIAGNOSIS_VERSION,
    SMOKE_RESULT_VERSION,
    build_evidence_consumption_summary,
    RC_VALIDATION_RUN_VERSION,
    RELEASE_CANDIDATE_REPORT_VERSION,
    RELEASE_OPERATOR_BUNDLE_VERSION,
    build_native_product_posture,
    build_release_candidate_report,
    build_release_operator_bundle,
    build_setup_diagnosis,
    run_product_smoke,
    run_release_candidate_validation,
    write_release_candidate_report,
    write_release_candidate_validation,
    write_release_operator_bundle,
)


def _health_snapshot() -> dict[str, object]:
    return {
        "providers": [
            {"provider": "codex", "available": False, "binary": "codex", "detail": "auth missing", "recommended_fallback": "mock"},
            {"provider": "claude", "available": True, "binary": "claude", "detail": "ok", "recommended_fallback": None},
            {"provider": "mock", "available": True, "binary": None, "detail": "mock provider is always available"},
        ],
        "runtime_modes": [{"mode": "cli_inherit"}],
        "direct_api_auth": [{"provider": "codex", "status": "auth_required", "key_name": "OPENAI_API_KEY", "masked": None}],
    }


def test_setup_diagnosis_reports_degraded_external_runtime_without_secrets() -> None:
    payload = build_setup_diagnosis(_health_snapshot())

    assert payload["format"] == SETUP_DIAGNOSIS_VERSION
    assert payload["local_mock"]["available"] is True
    assert payload["overall_posture"] == "ready_with_degraded_external_runtime"
    codex = next(item for item in payload["providers"] if item["provider"] == "codex")
    assert codex["degraded_mode"] is True
    assert "install/authenticate codex" in codex["fix_hint"]
    assert payload["secret_redaction"].startswith("only availability")
    assert payload["readiness_matrix"]["format"] == "agent_orchestrator.runtime_readiness_matrix.v1"
    assert payload["readiness_matrix"]["summary"]["mock_ready"] is True
    assert payload["release_candidate_verdict"] == "release_candidate_ready_with_external_cli"
    assert payload["install_release_candidate_ready"] is True
    assert payload["fix_plan"]
    assert payload["smoke_commands"]
    assert "sk-" not in json.dumps(payload)


def test_evidence_consumption_reads_authoritative_report_without_raw_json_needed(tmp_path: Path) -> None:
    report = tmp_path / "authoritative-report.json"
    report.write_text(
        json.dumps(
            {
                "case_result_count": 5,
                "instrumentation_closure": {"status": "closed"},
                "operator_decision": {
                    "decision": "instrumentation_closed_native_productization_next",
                    "reason": "closed; productization next",
                    "next_moves": ["advance native operator UX"],
                },
            }
        ),
        encoding="utf-8",
    )

    payload = build_evidence_consumption_summary(project_root=tmp_path, authoritative_report_path=report)

    assert payload["format"] == EVIDENCE_CONSUMPTION_VERSION
    assert payload["daily_driver_repeatability"]["family_count"] == 5
    assert payload["authoritative_opencode_comparison"]["instrumentation_closure"] == "closed"
    assert payload["operator_can_decide_without_raw_json"] is True
    assert payload["native_productization_next_step"] == "instrumentation_closed_native_productization_next"


def test_native_product_posture_aggregates_run_provider_evidence_and_next_action(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    (runs_root / "run-1.json").write_text(json.dumps({"id": "run-1", "status": "completed"}), encoding="utf-8")
    report = tmp_path / "authoritative-report.json"
    report.write_text(
        json.dumps(
            {
                "case_result_count": 5,
                "instrumentation_closure": {"status": "closed"},
                "operator_decision": {"decision": "instrumentation_closed_native_productization_next", "reason": "ok"},
            }
        ),
        encoding="utf-8",
    )

    payload = build_native_product_posture(
        provider_health_snapshot=_health_snapshot(),
        runs_root=runs_root,
        project_root=tmp_path,
        authoritative_report_path=report,
    )

    assert payload["format"] == PRODUCT_POSTURE_VERSION
    assert payload["product_posture"] == "daily_driver_candidate"
    assert payload["run_status"]["status"] == "completed"
    assert payload["authoritative_comparison_summary"]["instrumentation_closure"] == "closed"
    assert payload["blocker_recovery"]["blocker"] == "external_runtime_degraded_but_mock_available"
    assert payload["provider_runtime_posture"]["release_candidate_verdict"] == "release_candidate_ready_with_external_cli"
    assert payload["provider_runtime_posture"]["install_release_candidate_ready"] is True
    assert payload["next_action"] == "instrumentation_closed_native_productization_next"
    assert payload["recommended_commands"]


def test_product_smoke_accepts_injected_runner_and_returns_operator_summary() -> None:
    def runner(requirement: str):
        return {"status": "completed", "run_id": "run-smoke", "summary": {"case_count": 1}, "requirement": requirement}

    payload = run_product_smoke(requirement="smoke task", runner=runner)

    assert payload["format"] == SMOKE_RESULT_VERSION
    assert payload["status"] == "completed"
    assert payload["run_id"] == "run-smoke"
    assert payload["operator_summary"]["verify_or_stop"] == "verify"
    assert payload["operator_summary"]["readability"] == "clear"


def test_product_ux_snapshot_compacts_posture_for_ui_and_control_plane(tmp_path: Path) -> None:
    report = tmp_path / "authoritative-report.json"
    report.write_text(
        json.dumps(
            {
                "case_result_count": 5,
                "instrumentation_closure": {"status": "closed"},
                "operator_decision": {"decision": "instrumentation_closed_native_productization_next", "reason": "ok"},
            }
        ),
        encoding="utf-8",
    )
    from agent_orchestrator.native_productization import PRODUCT_UX_SNAPSHOT_VERSION, build_product_ux_snapshot

    payload = build_product_ux_snapshot(
        provider_health_snapshot=_health_snapshot(),
        runs_root=tmp_path / "runs",
        project_root=tmp_path,
        authoritative_report_path=report,
    )

    assert payload["format"] == PRODUCT_UX_SNAPSHOT_VERSION
    assert payload["read_only"] is True
    assert payload["provider_runtime"]["degraded_provider_count"] == 1
    assert payload["provider_runtime"]["release_candidate_verdict"] == "release_candidate_ready_with_external_cli"
    assert payload["provider_runtime"]["install_release_candidate_ready"] is True
    assert payload["provider_runtime"]["smoke_commands"]
    assert payload["evidence"]["instrumentation_closure"] == "closed"
    assert payload["blocker_recovery"]["blocker"] == "external_runtime_degraded_but_mock_available"
    assert payload["operator_can_decide_without_raw_json"] is True


def test_release_candidate_report_aggregates_gate_validation_and_artifact(tmp_path: Path) -> None:
    (tmp_path / "docs/process").mkdir(parents=True)
    for name in [
        "native-productization-after-instrumentation-install-release.md",
        "native-operator-ux-tui-deepening.md",
        "provider-runtime-readiness-hardening.md",
        "native-install-release-candidate-hardening.md",
    ]:
        (tmp_path / "docs/process" / name).write_text("doc", encoding="utf-8")
    report = tmp_path / "authoritative-report.json"
    report.write_text(json.dumps({
        "case_result_count": 5,
        "instrumentation_closure": {"status": "closed"},
        "operator_decision": {"decision": "native_rc_next", "reason": "ok"},
    }), encoding="utf-8")

    payload = build_release_candidate_report(
        provider_health_snapshot=_health_snapshot(),
        project_root=tmp_path,
        runs_root=tmp_path / "runs",
        authoritative_report_path=report,
    )
    artifact = write_release_candidate_report(tmp_path / "rc/report.json", payload)

    assert payload["format"] == RELEASE_CANDIDATE_REPORT_VERSION
    assert payload["verdict"] == "degraded"
    assert payload["checks"]["evidence_closure"]["status"] == "pass"
    assert payload["operator_summary"]["verify_or_stop"] == "verify"
    assert payload["validation_path"]["smoke_commands"]
    assert payload["validation_path"]["test_commands"]
    assert payload["known_limitations"]
    assert artifact["state"] == "written"
    assert json.loads((tmp_path / "rc/report.json").read_text(encoding="utf-8"))["artifact_kind"] == "native_release_candidate_report"


def test_release_candidate_validation_dry_run_records_commands_and_bundle(tmp_path: Path) -> None:
    (tmp_path / "docs/process").mkdir(parents=True)
    for name in [
        "native-productization-after-instrumentation-install-release.md",
        "native-operator-ux-tui-deepening.md",
        "provider-runtime-readiness-hardening.md",
        "native-install-release-candidate-hardening.md",
    ]:
        (tmp_path / "docs/process" / name).write_text("doc", encoding="utf-8")
    authoritative = tmp_path / "authoritative-report.json"
    authoritative.write_text(json.dumps({"case_result_count": 5, "instrumentation_closure": {"status": "closed"}, "operator_decision": {"decision": "native_rc_next"}}), encoding="utf-8")

    validation = run_release_candidate_validation(
        provider_health_snapshot=_health_snapshot(),
        project_root=tmp_path,
        runs_root=tmp_path / "runs",
        authoritative_report_path=authoritative,
        dry_run=True,
    )
    validation_artifact = write_release_candidate_validation(tmp_path / "rc/validation.json", validation)
    bundle = build_release_operator_bundle(
        provider_health_snapshot=_health_snapshot(),
        project_root=tmp_path,
        runs_root=tmp_path / "runs",
        authoritative_report_path=authoritative,
        validation=validation,
    )
    bundle_artifact = write_release_operator_bundle(tmp_path / "rc/bundle.json", bundle)

    assert validation["format"] == RC_VALIDATION_RUN_VERSION
    assert validation["dry_run"] is True
    assert validation["verdict"] == "degraded"
    assert validation["commands"]
    assert validation["commands"][0]["command"]
    assert validation["commands"][0]["exit_status"] == "not_applicable"
    assert validation["commands"][0]["reason"] == "dry_run_validation_not_executed"
    assert validation_artifact["state"] == "written"
    assert bundle["format"] == RELEASE_OPERATOR_BUNDLE_VERSION
    assert bundle["verdict"] == "degraded"
    assert bundle["validation"]["dry_run"] is True
    assert bundle["validation_commands"]
    assert bundle["rollback_cleanup"]
    assert bundle_artifact["state"] == "written"


def test_release_candidate_validation_executes_injected_runner_and_can_pass(tmp_path: Path) -> None:
    (tmp_path / "docs/process").mkdir(parents=True)
    for name in [
        "native-productization-after-instrumentation-install-release.md",
        "native-operator-ux-tui-deepening.md",
        "provider-runtime-readiness-hardening.md",
        "native-install-release-candidate-hardening.md",
    ]:
        (tmp_path / "docs/process" / name).write_text("doc", encoding="utf-8")
    authoritative = tmp_path / "authoritative-report.json"
    authoritative.write_text(json.dumps({"case_result_count": 5, "instrumentation_closure": {"status": "closed"}, "operator_decision": {"decision": "native_rc_next"}}), encoding="utf-8")

    validation = run_release_candidate_validation(
        provider_health_snapshot={"providers": [{"provider": "mock", "available": True}, {"provider": "codex", "available": True}, {"provider": "claude", "available": True}], "runtime_modes": [], "direct_api_auth": [{"provider": "codex", "available": True, "status": "available"}, {"provider": "claude", "available": True, "status": "available"}]},
        project_root=tmp_path,
        runs_root=tmp_path / "runs",
        authoritative_report_path=authoritative,
        include_tests=False,
        command_runner=lambda command: {"status": "pass", "exit_status": 0, "stdout_summary": "ok", "stderr_summary": "", "duration_ms": 1},
    )

    assert validation["verdict"] == "pass"
    assert validation["commands"][0]["status"] == "pass"
    assert validation["operator_summary"]["verify_or_stop"] == "verify"


def test_rc_adoption_ledger_and_report_cover_three_lanes(tmp_path: Path) -> None:
    from agent_orchestrator.native_productization import (
        RC_ADOPTION_LEDGER_VERSION,
        RC_ADOPTION_REPORT_VERSION,
        build_rc_adoption_report,
        run_rc_adoption,
        write_rc_adoption_ledger,
    )

    ledger = run_rc_adoption(project_root=tmp_path, dry_run=True)
    artifact = write_rc_adoption_ledger(tmp_path / "adoption-ledger.json", ledger)
    report = build_rc_adoption_report(ledger)

    assert ledger["format"] == RC_ADOPTION_LEDGER_VERSION
    assert artifact["state"] == "written"
    assert [record["lane"] for record in ledger["records"]] == ["repo_change_lane", "validation_lane", "recovery_lane"]
    for record in ledger["records"]:
        assert record["case_id"]
        assert record["rc_bundle_ref"]["state"] in {"available", "missing", "not_run", "unavailable"}
        assert record["validation_ref"]["state"] in {"available", "missing", "not_run", "unavailable"}
        assert record["commands_or_actions"][0]["started_at"]
        assert record["commands_or_actions"][0]["ended_at"]
        assert "duration_ms" in record["commands_or_actions"][0]
        assert record["pause_or_failure_reason"] in {"dry_run_not_executed", "simulated_recovery_checkpoint", "RC bundle or validation failed"}
    assert report["format"] == RC_ADOPTION_REPORT_VERSION
    assert report["summary"]["lane_count"] == 3
    assert report["summary"]["gap_classification"] in {"operator_workflow_friction", "instrumentation_evidence", "product_thickness", "none"}
    counts = report["operator_report"]["continue_stop_degrade"]
    assert counts["degrade"] + counts["stop"] + counts["continue"] == 3
