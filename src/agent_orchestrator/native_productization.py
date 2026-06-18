"""Operator-facing native productization posture and smoke helpers."""
from __future__ import annotations

# DEPS: __future__, json, pathlib, typing
# RESPONSIBILITY: Build productization-ready operator posture, setup diagnosis, daily-driver smoke, and evidence consumption summaries.
# MODULE: productization
# ---

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


PRODUCT_POSTURE_VERSION = "agent_orchestrator.native_product_posture.v1"
SETUP_DIAGNOSIS_VERSION = "agent_orchestrator.native_product_setup_diagnosis.v1"
SMOKE_RESULT_VERSION = "agent_orchestrator.native_product_smoke_result.v1"
EVIDENCE_CONSUMPTION_VERSION = "agent_orchestrator.native_product_evidence_consumption.v1"
PRODUCT_UX_SNAPSHOT_VERSION = "agent_orchestrator.native_product_ux_snapshot.v1"
RUNTIME_READINESS_MATRIX_VERSION = "agent_orchestrator.runtime_readiness_matrix.v1"
RELEASE_CANDIDATE_REPORT_VERSION = "agent_orchestrator.native_release_candidate_report.v1"
RC_VALIDATION_RUN_VERSION = "agent_orchestrator.native_rc_validation_run.v1"
RELEASE_OPERATOR_BUNDLE_VERSION = "agent_orchestrator.native_release_operator_bundle.v1"



def _safe_load_json(path: str | Path) -> dict[str, object]:
    candidate = Path(path)
    if not candidate.exists():
        return {}
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _latest_run_status(runs_root: str | Path) -> dict[str, object]:
    root = Path(runs_root)
    if not root.exists():
        return {"state": "no_runs", "latest_run_id": None, "status": "not_started", "reason": "runs_root_missing"}
    candidates = sorted([p for p in root.glob("*.json") if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return {"state": "no_runs", "latest_run_id": None, "status": "not_started", "reason": "no_run_artifacts"}
    payload = _safe_load_json(candidates[0])
    return {
        "state": "available",
        "latest_run_id": payload.get("id") or payload.get("run_id") or candidates[0].stem,
        "status": payload.get("status") or payload.get("state") or "unknown",
        "artifact": str(candidates[0]),
        "reason": "latest_run_artifact_available",
    }



def _direct_api_auth_by_provider(provider_health_snapshot: dict[str, object]) -> dict[str, dict[str, object]]:
    auth_entries = provider_health_snapshot.get("direct_api_auth", []) if isinstance(provider_health_snapshot.get("direct_api_auth"), list) else []
    return {
        str(item.get("provider")): item
        for item in auth_entries
        if isinstance(item, dict) and item.get("provider")
    }


def _runtime_smoke_command(runtime_id: str) -> str:
    if runtime_id == "mock":
        return "agent-orchestrator product smoke --format json"
    if runtime_id in {"codex", "claude"}:
        return f"agent-orchestrator health --format json && agent-orchestrator start 'Provider smoke' --runtime command --provider {runtime_id}"
    if runtime_id.startswith("direct_api"):
        return "agent-orchestrator health --format json"
    return "agent-orchestrator product diagnose --format json"


def _build_runtime_readiness_matrix(
    provider_health_snapshot: dict[str, object],
    provider_summaries: list[dict[str, object]],
) -> dict[str, object]:
    auth_by_provider = _direct_api_auth_by_provider(provider_health_snapshot)
    providers_by_name = {str(item.get("provider")): item for item in provider_summaries if item.get("provider")}
    rows: list[dict[str, object]] = []
    for name in ("mock", "codex", "claude"):
        provider = providers_by_name.get(name, {})
        available = bool(provider.get("available"))
        command_available = bool(available if name != "mock" else True)
        auth_status = "not_applicable" if name == "mock" else "cli_inherited_or_not_checked" if command_available else "unavailable"
        readiness = "ready" if available else "degraded"
        rows.append({
            "runtime_id": name,
            "runtime_type": "local_mock" if name == "mock" else "provider_cli",
            "command_available": command_available,
            "auth_config_status": auth_status,
            "available": available,
            "degraded_mode": not available,
            "fallback": provider.get("recommended_fallback") or (None if name == "mock" else "mock"),
            "readiness": readiness,
            "fix_hint": provider.get("fix_hint") or ("ready" if available else f"install/authenticate {name} or use mock fallback"),
            "smoke_command": _runtime_smoke_command(name),
        })
    direct_ready = 0
    for provider_name in ("codex", "claude"):
        auth = auth_by_provider.get(provider_name, {})
        auth_available = bool(auth.get("available"))
        if auth_available:
            direct_ready += 1
        runtime_id = f"direct_api_{provider_name}"
        rows.append({
            "runtime_id": runtime_id,
            "runtime_type": "direct_api",
            "command_available": True,
            "auth_config_status": auth.get("status") or ("available" if auth_available else "auth_required"),
            "available": auth_available,
            "degraded_mode": not auth_available,
            "fallback": "mock",
            "readiness": "ready" if auth_available else "degraded",
            "fix_hint": "ready" if auth_available else f"set {auth.get('key_name') or provider_name.upper() + '_API_KEY'} for direct API mode",
            "smoke_command": _runtime_smoke_command(runtime_id),
        })
    mock_ready = bool(providers_by_name.get("mock", {}).get("available"))
    cli_ready_count = sum(1 for row in rows if row.get("runtime_type") == "provider_cli" and row.get("available"))
    degraded_count = sum(1 for row in rows if row.get("degraded_mode"))
    if mock_ready and cli_ready_count:
        verdict = "release_candidate_ready_with_external_cli"
        can_enter = True
    elif mock_ready:
        verdict = "release_candidate_ready_with_mock_only"
        can_enter = True
    else:
        verdict = "not_release_candidate_ready"
        can_enter = False
    return {
        "format": RUNTIME_READINESS_MATRIX_VERSION,
        "rows": rows,
        "summary": {
            "runtime_count": len(rows),
            "ready_runtime_count": sum(1 for row in rows if row.get("available")),
            "degraded_runtime_count": degraded_count,
            "provider_cli_ready_count": cli_ready_count,
            "direct_api_ready_count": direct_ready,
            "mock_ready": mock_ready,
        },
        "release_candidate_verdict": verdict,
        "install_release_candidate_ready": can_enter,
    }


def _fix_plan_from_matrix(matrix: dict[str, object]) -> list[dict[str, object]]:
    rows = matrix.get("rows", []) if isinstance(matrix.get("rows"), list) else []
    plan = []
    for row in rows:
        if not isinstance(row, dict) or row.get("available"):
            continue
        plan.append({
            "runtime_id": row.get("runtime_id"),
            "fix_hint": row.get("fix_hint"),
            "fallback": row.get("fallback"),
            "smoke_command_after_fix": row.get("smoke_command"),
        })
    return plan

def build_setup_diagnosis(provider_health_snapshot: dict[str, object] | None) -> dict[str, object]:
    provider_health_snapshot = provider_health_snapshot if isinstance(provider_health_snapshot, dict) else {}
    providers = provider_health_snapshot.get("providers", []) if isinstance(provider_health_snapshot.get("providers"), list) else []
    provider_summaries: list[dict[str, object]] = []
    for provider in providers:
        if not isinstance(provider, dict):
            continue
        available = bool(provider.get("available"))
        name = str(provider.get("provider") or "unknown")
        provider_summaries.append(
            {
                "provider": name,
                "available": available,
                "binary": provider.get("binary"),
                "detail": provider.get("detail"),
                "degraded_mode": not available,
                "fix_hint": "ready" if available else f"install/authenticate {name} or use mock fallback",
                "recommended_fallback": provider.get("recommended_fallback") or "mock",
            }
        )
    if not any(item.get("provider") == "mock" for item in provider_summaries):
        provider_summaries.append(
            {
                "provider": "mock",
                "available": True,
                "binary": None,
                "detail": "mock provider is always available",
                "degraded_mode": False,
                "fix_hint": "ready",
                "recommended_fallback": None,
            }
        )
    unavailable = [item for item in provider_summaries if not item.get("available")]
    matrix = _build_runtime_readiness_matrix(provider_health_snapshot, provider_summaries)
    fix_plan = _fix_plan_from_matrix(matrix)
    smoke_commands = list(dict.fromkeys(str(row.get("smoke_command")) for row in matrix.get("rows", []) if isinstance(row, dict) and row.get("smoke_command")))
    return {
        "format": SETUP_DIAGNOSIS_VERSION,
        "local_mock": next((item for item in provider_summaries if item.get("provider") == "mock"), {}),
        "providers": provider_summaries,
        "runtime_modes": provider_health_snapshot.get("runtime_modes", []),
        "direct_api_auth": provider_health_snapshot.get("direct_api_auth", []),
        "readiness_matrix": matrix,
        "release_candidate_verdict": matrix.get("release_candidate_verdict"),
        "install_release_candidate_ready": matrix.get("install_release_candidate_ready"),
        "fix_plan": fix_plan,
        "smoke_commands": smoke_commands,
        "overall_posture": "ready_with_degraded_external_runtime" if unavailable or fix_plan else "ready",
        "secret_redaction": "only availability/detail/binary names and env var names are reported; secret values are not emitted",
        "fix_hints": [str(item.get("fix_hint")) for item in fix_plan] or ["no setup fixes required for mock smoke path"],
    }


def build_evidence_consumption_summary(
    *,
    project_root: str | Path = ".",
    authoritative_report_path: str | Path | None = None,
) -> dict[str, object]:
    project_root = Path(project_root)
    authoritative_report = _safe_load_json(authoritative_report_path) if authoritative_report_path else {}
    if not authoritative_report:
        default_report = project_root / ".agent_orchestrator" / "external-opencode-authoritative" / "authoritative-report.json"
        authoritative_report = _safe_load_json(default_report)
    if authoritative_report:
        instrumentation = authoritative_report.get("instrumentation_closure", {}) if isinstance(authoritative_report.get("instrumentation_closure"), dict) else {}
        decision = authoritative_report.get("operator_decision", {}) if isinstance(authoritative_report.get("operator_decision"), dict) else {}
        case_count = authoritative_report.get("case_result_count", 0)
        opencode_summary = {
            "state": "available",
            "case_result_count": case_count,
            "instrumentation_closure": instrumentation.get("status"),
            "operator_decision": decision.get("decision") or decision.get("recommended_path"),
            "reason": decision.get("reason"),
            "next_moves": decision.get("next_moves", []),
        }
    else:
        from agent_orchestrator.opencode_harness import build_external_opencode_harness_bundle

        bundle = build_external_opencode_harness_bundle()
        instrumentation = bundle.get("instrumentation_closure", {}) if isinstance(bundle.get("instrumentation_closure"), dict) else {}
        decision = bundle.get("operator_decision", {}) if isinstance(bundle.get("operator_decision"), dict) else {}
        opencode_summary = {
            "state": "fallback_bundle",
            "case_result_count": bundle.get("authoritative_comparative_report", {}).get("case_result_count") if isinstance(bundle.get("authoritative_comparative_report"), dict) else 0,
            "instrumentation_closure": instrumentation.get("status"),
            "operator_decision": decision.get("decision") or decision.get("recommended_path"),
            "reason": decision.get("reason"),
            "next_moves": decision.get("next_moves", []),
        }
    return {
        "format": EVIDENCE_CONSUMPTION_VERSION,
        "daily_driver_repeatability": {
            "state": "available",
            "summary": "native daily-driver repeatability has a fixed five-family evidence/case surface",
            "family_count": 5,
            "operator_readable": True,
        },
        "authoritative_opencode_comparison": opencode_summary,
        "native_productization_next_step": opencode_summary.get("operator_decision") or "native_productization_next",
        "operator_can_decide_without_raw_json": True,
    }



def _doc_status(project_root: Path) -> dict[str, object]:
    required = [
        "docs/process/native-productization-after-instrumentation-install-release.md",
        "docs/process/native-operator-ux-tui-deepening.md",
        "docs/process/provider-runtime-readiness-hardening.md",
        "docs/process/native-install-release-candidate-hardening.md",
    ]
    rows = []
    for rel in required:
        exists = (project_root / rel).exists()
        rows.append({"path": rel, "state": "available" if exists else "missing", "required": True})
    missing = [row["path"] for row in rows if row["state"] == "missing"]
    return {"state": "available" if not missing else "missing", "required": rows, "missing": missing}


def _test_status() -> dict[str, object]:
    commands = [
        "pytest -q tests/test_native_productization.py",
        "pytest -q tests/test_cli.py -k product",
        "pytest -q tests/test_ui_service.py -k native_product_ux",
        "pytest -q tests/test_control_plane.py -k native_product_ux",
        "pytest -q tests/test_docs_process.py -k native",
    ]
    return {
        "state": "declared_not_run",
        "reason": "release candidate gate declares focused validation commands; CLI rc-report does not execute tests by default",
        "commands": commands,
    }


def _evidence_gate_status(evidence: dict[str, object]) -> dict[str, object]:
    comparison = evidence.get("authoritative_opencode_comparison", {}) if isinstance(evidence.get("authoritative_opencode_comparison"), dict) else {}
    closure = comparison.get("instrumentation_closure")
    cases = comparison.get("case_result_count")
    if closure == "closed" and cases == 5:
        status = "pass"
        reason = "authoritative OpenCode comparison closed for the fixed five-family case pack"
    elif closure in {"closed", "partially_closed"}:
        status = "degraded"
        reason = "authoritative comparison exists but is partial or case count is not exactly five"
    else:
        status = "fail"
        reason = "instrumentation evidence is still blocking or unavailable"
    return {
        "status": status,
        "instrumentation_closure": closure or "missing",
        "case_result_count": cases if cases is not None else "missing",
        "operator_decision": comparison.get("operator_decision"),
        "reason": reason,
    }


def build_release_candidate_gate(
    *,
    provider_health_snapshot: dict[str, object] | None = None,
    runs_root: str | Path = ".agent_orchestrator/runs",
    project_root: str | Path = ".",
    authoritative_report_path: str | Path | None = None,
) -> dict[str, object]:
    """Aggregate product/runtime/evidence/docs surfaces into an RC pass/degraded/fail gate."""
    root = Path(project_root)
    posture = build_native_product_posture(
        provider_health_snapshot=provider_health_snapshot,
        runs_root=runs_root,
        project_root=root,
        authoritative_report_path=authoritative_report_path,
    )
    setup = posture.get("provider_runtime_posture", {}) if isinstance(posture.get("provider_runtime_posture"), dict) else {}
    evidence = posture.get("evidence_summary", {}) if isinstance(posture.get("evidence_summary"), dict) else {}
    docs = _doc_status(root)
    tests = _test_status()
    evidence_gate = _evidence_gate_status(evidence)
    runtime_ready = bool(setup.get("install_release_candidate_ready"))
    degraded_runtimes = []
    matrix = setup.get("readiness_matrix", {}) if isinstance(setup.get("readiness_matrix"), dict) else {}
    for row in matrix.get("rows", []) if isinstance(matrix.get("rows"), list) else []:
        if isinstance(row, dict) and row.get("degraded_mode"):
            degraded_runtimes.append({
                "runtime_id": row.get("runtime_id"),
                "fallback": row.get("fallback"),
                "fix_hint": row.get("fix_hint"),
            })
    blockers: list[str] = []
    warnings: list[str] = []
    if not runtime_ready:
        blockers.append("no install release candidate runtime path is available")
    if evidence_gate["status"] == "fail":
        blockers.append(str(evidence_gate["reason"]))
    elif evidence_gate["status"] == "degraded":
        warnings.append(str(evidence_gate["reason"]))
    if docs.get("missing"):
        blockers.append("missing required RC docs: " + ", ".join(str(item) for item in docs.get("missing", [])))
    if degraded_runtimes:
        warnings.append("one or more non-mock runtimes are degraded; mock fallback remains authoritative for local RC if available")
    if blockers:
        verdict = "fail"
    elif warnings:
        verdict = "degraded"
    else:
        verdict = "pass"
    smoke_commands = setup.get("smoke_commands", []) if isinstance(setup.get("smoke_commands"), list) else []
    return {
        "format": RELEASE_CANDIDATE_REPORT_VERSION,
        "gate_type": "native_install_release_candidate",
        "verdict": verdict,
        "install_release_candidate_ready": runtime_ready and not blockers,
        "product_posture": posture.get("product_posture"),
        "checks": {
            "product_posture": {"status": "pass" if posture.get("product_posture") else "fail", "value": posture.get("product_posture")},
            "runtime_matrix": {
                "status": "pass" if runtime_ready and not degraded_runtimes else "degraded" if runtime_ready else "fail",
                "release_candidate_verdict": setup.get("release_candidate_verdict"),
                "degraded_runtimes": degraded_runtimes,
            },
            "evidence_closure": evidence_gate,
            "docs": docs,
            "tests": tests,
            "smoke_commands": {"status": "pass" if smoke_commands else "fail", "commands": smoke_commands},
        },
        "blockers": blockers,
        "warnings": warnings,
        "next_actions": blockers or warnings or ["run the focused RC smoke and test commands before tagging a local release candidate"],
    }


def build_release_candidate_report(
    *,
    provider_health_snapshot: dict[str, object] | None = None,
    runs_root: str | Path = ".agent_orchestrator/runs",
    project_root: str | Path = ".",
    authoritative_report_path: str | Path | None = None,
) -> dict[str, object]:
    gate = build_release_candidate_gate(
        provider_health_snapshot=provider_health_snapshot,
        runs_root=runs_root,
        project_root=project_root,
        authoritative_report_path=authoritative_report_path,
    )
    checks = gate.get("checks", {}) if isinstance(gate.get("checks"), dict) else {}
    runtime = checks.get("runtime_matrix", {}) if isinstance(checks.get("runtime_matrix"), dict) else {}
    smoke = checks.get("smoke_commands", {}) if isinstance(checks.get("smoke_commands"), dict) else {}
    tests = checks.get("tests", {}) if isinstance(checks.get("tests"), dict) else {}
    return {
        **gate,
        "artifact_kind": "native_release_candidate_report",
        "operator_summary": {
            "outcome": gate.get("verdict"),
            "verify_or_stop": "verify" if gate.get("verdict") in {"pass", "degraded"} else "stop",
            "next_action": (gate.get("next_actions") or ["inspect release candidate gate"])[0],
            "readability": "operator_can_decide_without_raw_json",
        },
        "runtime_summary": {
            "release_candidate_verdict": runtime.get("release_candidate_verdict"),
            "degraded_paths": runtime.get("degraded_runtimes", []),
        },
        "validation_path": {
            "smoke_commands": smoke.get("commands", []),
            "test_commands": tests.get("commands", []),
        },
        "known_limitations": [
            "local RC only; no package registry release is performed",
            "provider marketplace, plugin ecosystem, and public release automation are out of scope",
            "external provider readiness may be degraded while mock fallback remains usable",
            "AiMaMi/local proxy configuration is not modified",
        ],
        "rollback_cleanup": [
            "remove generated .agent_orchestrator RC report artifacts if validation is abandoned",
            "rerun product diagnose after changing provider CLI/auth setup",
            "use mock runtime smoke path when external runtime repair is pending",
        ],
    }


def write_release_candidate_report(path: str | Path, report: dict[str, object]) -> dict[str, object]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"path": str(target), "state": "written", "bytes": target.stat().st_size}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _summarize_text(value: object, limit: int = 1200) -> str:
    text = "" if value is None else str(value)
    text = text.strip()
    return text if len(text) <= limit else text[:limit] + "…"


def _validation_commands_from_report(report: dict[str, object], *, include_smoke: bool = True, include_tests: bool = True) -> list[dict[str, object]]:
    validation = report.get("validation_path", {}) if isinstance(report.get("validation_path"), dict) else {}
    commands: list[dict[str, object]] = []
    if include_smoke:
        for command in validation.get("smoke_commands", []) if isinstance(validation.get("smoke_commands"), list) else []:
            commands.append({"kind": "smoke", "command": str(command), "required": True})
    if include_tests:
        for command in validation.get("test_commands", []) if isinstance(validation.get("test_commands"), list) else []:
            commands.append({"kind": "test", "command": str(command), "required": True})
    if not commands:
        commands.append({"kind": "diagnostic", "command": "agent-orchestrator product rc-report --format json", "required": True})
    return commands


def _execute_validation_command(command: str, *, project_root: Path, timeout_seconds: int) -> dict[str, object]:
    started = _now_iso()
    start = time.monotonic()
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=project_root,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
        )
        exit_status: int | str | None = result.returncode
        status = "pass" if result.returncode == 0 else "fail"
        stdout = result.stdout
        stderr = result.stderr
        reason = "command_completed" if result.returncode == 0 else "command_exit_nonzero"
    except subprocess.TimeoutExpired as exc:
        exit_status = "timeout"
        status = "fail"
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        reason = "command_timeout"
    except Exception as exc:  # pragma: no cover - defensive guard for unusual shells
        exit_status = "unavailable"
        status = "unavailable"
        stdout = ""
        stderr = str(exc)
        reason = "command_unavailable"
    ended = _now_iso()
    return {
        "command": command,
        "status": status,
        "exit_status": exit_status,
        "started_at": started,
        "ended_at": ended,
        "duration_ms": int((time.monotonic() - start) * 1000),
        "stdout_summary": _summarize_text(stdout),
        "stderr_summary": _summarize_text(stderr),
        "reason": reason,
    }


def run_release_candidate_validation(
    *,
    provider_health_snapshot: dict[str, object] | None = None,
    runs_root: str | Path = ".agent_orchestrator/runs",
    project_root: str | Path = ".",
    authoritative_report_path: str | Path | None = None,
    dry_run: bool = False,
    include_smoke: bool = True,
    include_tests: bool = True,
    timeout_seconds: int = 60,
    command_runner: Callable[[str], dict[str, object]] | None = None,
) -> dict[str, object]:
    root = Path(project_root)
    report = build_release_candidate_report(
        provider_health_snapshot=provider_health_snapshot,
        runs_root=runs_root,
        project_root=root,
        authoritative_report_path=authoritative_report_path,
    )
    commands = _validation_commands_from_report(report, include_smoke=include_smoke, include_tests=include_tests)
    started_at = _now_iso()
    start = time.monotonic()
    records: list[dict[str, object]] = []
    for item in commands:
        command = str(item.get("command"))
        if dry_run:
            timestamp = _now_iso()
            record = {
                **item,
                "status": "not_run",
                "exit_status": "not_applicable",
                "started_at": timestamp,
                "ended_at": timestamp,
                "duration_ms": 0,
                "stdout_summary": "",
                "stderr_summary": "",
                "reason": "dry_run_validation_not_executed",
            }
        elif command_runner is not None:
            custom = command_runner(command)
            record = {**item, **custom, "command": command}
            record.setdefault("status", "pass" if record.get("exit_status") == 0 else "fail")
            record.setdefault("started_at", _now_iso())
            record.setdefault("ended_at", record["started_at"])
            record.setdefault("duration_ms", 0)
            record.setdefault("reason", "custom_runner")
        else:
            record = {**item, **_execute_validation_command(command, project_root=root, timeout_seconds=timeout_seconds)}
        records.append(record)
    ended_at = _now_iso()
    statuses = {str(item.get("status")) for item in records}
    blockers: list[str] = []
    warnings = list(report.get("warnings", [])) if isinstance(report.get("warnings"), list) else []
    if report.get("verdict") == "fail":
        blockers.extend(str(item) for item in report.get("blockers", []) if item)
    if "fail" in statuses or "unavailable" in statuses:
        blockers.append("one or more RC validation commands failed or were unavailable")
    if dry_run or "not_run" in statuses:
        warnings.append("validation commands were declared but not executed")
    if blockers:
        verdict = "fail"
    elif dry_run or warnings:
        verdict = "degraded"
    else:
        verdict = "pass"
    return {
        "format": RC_VALIDATION_RUN_VERSION,
        "artifact_kind": "native_rc_validation_run",
        "dry_run": dry_run,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_ms": int((time.monotonic() - start) * 1000),
        "verdict": verdict,
        "release_candidate_report_verdict": report.get("verdict"),
        "command_count": len(records),
        "commands": records,
        "blockers": blockers,
        "warnings": warnings,
        "operator_summary": {
            "outcome": verdict,
            "verify_or_stop": "stop" if verdict == "fail" else "verify",
            "next_action": blockers[0] if blockers else warnings[0] if warnings else "bundle RC validation artifacts for operator handoff",
            "readability": "operator_can_decide_without_raw_transcript",
        },
    }


def write_release_candidate_validation(path: str | Path, validation: dict[str, object]) -> dict[str, object]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"path": str(target), "state": "written", "bytes": target.stat().st_size}


def build_release_operator_bundle(
    *,
    provider_health_snapshot: dict[str, object] | None = None,
    runs_root: str | Path = ".agent_orchestrator/runs",
    project_root: str | Path = ".",
    authoritative_report_path: str | Path | None = None,
    validation: dict[str, object] | None = None,
    validation_path: str | Path | None = None,
    dry_run_validation: bool = True,
) -> dict[str, object]:
    root = Path(project_root)
    report = build_release_candidate_report(
        provider_health_snapshot=provider_health_snapshot,
        runs_root=runs_root,
        project_root=root,
        authoritative_report_path=authoritative_report_path,
    )
    validation_payload = validation if isinstance(validation, dict) else {}
    if not validation_payload and validation_path:
        validation_payload = _safe_load_json(validation_path)
    if not validation_payload:
        default_validation = root / ".agent_orchestrator" / "release-candidate" / "validation.json"
        validation_payload = _safe_load_json(default_validation)
    if not validation_payload:
        validation_payload = run_release_candidate_validation(
            provider_health_snapshot=provider_health_snapshot,
            runs_root=runs_root,
            project_root=root,
            authoritative_report_path=authoritative_report_path,
            dry_run=dry_run_validation,
        )
    blockers: list[str] = []
    warnings: list[str] = []
    if report.get("verdict") == "fail":
        blockers.extend(str(item) for item in report.get("blockers", []) if item)
    elif report.get("verdict") == "degraded":
        warnings.extend(str(item) for item in report.get("warnings", []) if item)
    if validation_payload.get("verdict") == "fail":
        blockers.extend(str(item) for item in validation_payload.get("blockers", []) if item)
    elif validation_payload.get("verdict") == "degraded":
        warnings.extend(str(item) for item in validation_payload.get("warnings", []) if item)
    if blockers:
        verdict = "fail"
    elif warnings:
        verdict = "degraded"
    else:
        verdict = "pass"
    return {
        "format": RELEASE_OPERATOR_BUNDLE_VERSION,
        "artifact_kind": "native_release_operator_bundle",
        "verdict": verdict,
        "report": {
            "format": report.get("format"),
            "verdict": report.get("verdict"),
            "blockers": report.get("blockers", []),
            "warnings": report.get("warnings", []),
        },
        "validation": {
            "format": validation_payload.get("format"),
            "verdict": validation_payload.get("verdict"),
            "dry_run": validation_payload.get("dry_run"),
            "command_count": validation_payload.get("command_count"),
            "blockers": validation_payload.get("blockers", []),
            "warnings": validation_payload.get("warnings", []),
        },
        "validation_commands": validation_payload.get("commands", []),
        "docs": report.get("checks", {}).get("docs", {}) if isinstance(report.get("checks"), dict) else {},
        "smoke_commands": report.get("validation_path", {}).get("smoke_commands", []) if isinstance(report.get("validation_path"), dict) else [],
        "test_commands": report.get("validation_path", {}).get("test_commands", []) if isinstance(report.get("validation_path"), dict) else [],
        "known_limitations": report.get("known_limitations", []),
        "rollback_cleanup": report.get("rollback_cleanup", []),
        "blockers": blockers,
        "warnings": warnings,
        "operator_summary": {
            "outcome": verdict,
            "verify_or_stop": "stop" if verdict == "fail" else "verify",
            "next_action": blockers[0] if blockers else warnings[0] if warnings else "handoff local RC bundle to operator",
            "readability": "operator_can_decide_without_raw_transcript",
        },
    }


def write_release_operator_bundle(path: str | Path, bundle: dict[str, object]) -> dict[str, object]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"path": str(target), "state": "written", "bytes": target.stat().st_size}



RC_ADOPTION_RECORD_VERSION = "agent_orchestrator.native_rc_adoption_record.v1"
RC_ADOPTION_LEDGER_VERSION = "agent_orchestrator.native_rc_adoption_ledger.v1"
RC_ADOPTION_REPORT_VERSION = "agent_orchestrator.native_rc_adoption_report.v1"
RC_ADOPTION_SUMMARY_VERSION = "agent_orchestrator.native_rc_adoption_summary.v1"
RC_ADOPTION_LANES = ("repo_change_lane", "validation_lane", "recovery_lane")


def build_rc_adoption_case_pack() -> dict[str, object]:
    """Return the fixed local dogfood adoption lanes for a native RC bundle."""
    return {
        "format": "agent_orchestrator.native_rc_adoption_case_pack.v1",
        "lane_count": 3,
        "lanes": [
            {
                "lane": "repo_change_lane",
                "input_requirement": "Use the RC bundle to drive a small local code/docs change and leave an auditable workspace diff.",
                "success_signal": "workspace impact is reviewable and the operator can continue, stop, or degrade without reading raw transcripts",
            },
            {
                "lane": "validation_lane",
                "input_requirement": "Consume product rc-report / rc-validate / rc-bundle verdicts and decide whether handoff can continue.",
                "success_signal": "validation verdict and RC bundle verdict are referenced or their missing/unavailable reason is explicit",
            },
            {
                "lane": "recovery_lane",
                "input_requirement": "Exercise a pause/failure/degraded-runtime path and record a standardized recovery next action.",
                "success_signal": "pause/failure reason and recovery action are operator-readable",
            },
        ],
    }


def _artifact_ref(payload: dict[str, object], *, path: str | Path | None = None, kind: str = "artifact") -> dict[str, object]:
    if payload:
        return {
            "state": "available",
            "kind": kind,
            "path": str(path) if path else payload.get("artifact", {}).get("path") if isinstance(payload.get("artifact"), dict) else None,
            "format": payload.get("format"),
            "verdict": payload.get("verdict"),
            "dry_run": payload.get("dry_run"),
            "reason": "artifact_payload_available",
        }
    if path:
        return {"state": "missing", "kind": kind, "path": str(path), "format": None, "verdict": None, "reason": "artifact_path_missing_or_unreadable"}
    return {"state": "not_run", "kind": kind, "path": None, "format": None, "verdict": None, "reason": "artifact_not_provided"}


def _adoption_runtime_payload(command: str, *, dry_run: bool, action: str | None = None) -> dict[str, object]:
    stamp = _now_iso()
    return {
        "command": command,
        "action": action or command,
        "started_at": stamp,
        "ended_at": stamp,
        "duration_ms": 0,
        "status": "not_run" if dry_run else "available",
        "reason": "dry_run_adoption_not_executed" if dry_run else "adoption_action_recorded",
    }


def _workspace_impact(project_root: Path, *, dry_run: bool) -> dict[str, object]:
    if dry_run:
        return {"state": "not_run", "changed_files": [], "no_change": True, "reason": "dry_run_workspace_not_modified"}
    try:
        result = subprocess.run(["git", "status", "--short"], cwd=project_root, text=True, capture_output=True, timeout=10)
    except Exception as exc:  # pragma: no cover - defensive
        return {"state": "unavailable", "changed_files": [], "no_change": None, "reason": f"git_status_unavailable: {exc}"}
    if result.returncode != 0:
        return {"state": "unavailable", "changed_files": [], "no_change": None, "reason": _summarize_text(result.stderr) or "git_status_failed"}
    changed = [line[3:] if len(line) > 3 else line for line in result.stdout.splitlines() if line.strip()]
    return {"state": "available", "changed_files": changed, "no_change": not changed, "reason": "git_status_available"}


def _record_decision(lane: str, *, dry_run: bool, bundle_verdict: object, validation_verdict: object) -> tuple[str, str, str]:
    if bundle_verdict == "fail" or validation_verdict == "fail":
        return "stop", "stop_before_dogfood", "RC bundle or validation failed"
    if dry_run:
        return "degrade", "rerun rc-adopt without --dry-run for " + lane, "dry_run_not_executed"
    if bundle_verdict == "degraded" or validation_verdict == "degraded":
        return "degrade", "continue with mock/local fallback and capture friction", "degraded_rc_consumed"
    return "continue", "continue local dogfood lane", "none"


def run_rc_adoption(
    *,
    provider_health_snapshot: dict[str, object] | None = None,
    runs_root: str | Path = ".agent_orchestrator/runs",
    project_root: str | Path = ".",
    authoritative_report_path: str | Path | None = None,
    validation_path: str | Path | None = None,
    bundle_path: str | Path | None = None,
    dry_run: bool = True,
) -> dict[str, object]:
    """Build a reusable local dogfood adoption ledger from the current RC bundle surfaces."""
    root = Path(project_root)
    started_at = _now_iso()
    start = time.monotonic()
    validation = _safe_load_json(validation_path) if validation_path else {}
    if not validation:
        default_validation = root / ".agent_orchestrator" / "release-candidate" / "validation.json"
        validation = _safe_load_json(default_validation)
        validation_path = default_validation if validation else validation_path
    if not validation:
        validation = run_release_candidate_validation(
            provider_health_snapshot=provider_health_snapshot,
            runs_root=runs_root,
            project_root=root,
            authoritative_report_path=authoritative_report_path,
            dry_run=True,
        )
    bundle = _safe_load_json(bundle_path) if bundle_path else {}
    if not bundle:
        default_bundle = root / ".agent_orchestrator" / "release-candidate" / "bundle.json"
        bundle = _safe_load_json(default_bundle)
        bundle_path = default_bundle if bundle else bundle_path
    if not bundle:
        bundle = build_release_operator_bundle(
            provider_health_snapshot=provider_health_snapshot,
            runs_root=runs_root,
            project_root=root,
            authoritative_report_path=authoritative_report_path,
            validation=validation,
            dry_run_validation=True,
        )
    report_ref = bundle.get("report", {}) if isinstance(bundle.get("report"), dict) else {}
    validation_ref_payload = bundle.get("validation", {}) if isinstance(bundle.get("validation"), dict) else {}
    case_pack = build_rc_adoption_case_pack()
    workspace = _workspace_impact(root, dry_run=dry_run)
    records: list[dict[str, object]] = []
    commands = {
        "repo_change_lane": "operator uses RC bundle to make a small reviewable repo change",
        "validation_lane": "agent-orchestrator product rc-validate --dry-run --format json",
        "recovery_lane": "operator inspects degraded/pause state and records recovery action",
    }
    for index, case in enumerate(case_pack["lanes"], start=1):
        lane = str(case["lane"])
        lane_started = _now_iso()
        lane_start = time.monotonic()
        decision, next_action, pause_reason = _record_decision(
            lane,
            dry_run=dry_run,
            bundle_verdict=bundle.get("verdict"),
            validation_verdict=validation.get("verdict"),
        )
        recovery_action = "none"
        if lane == "recovery_lane":
            recovery_action = "use mock fallback, preserve RC artifact refs, and rerun failed lane after setup repair"
            if pause_reason == "none":
                pause_reason = "simulated_recovery_checkpoint"
        runtime_payload = _adoption_runtime_payload(commands[lane], dry_run=dry_run, action=f"adoption:{lane}")
        lane_ended = _now_iso()
        records.append({
            "format": RC_ADOPTION_RECORD_VERSION,
            "case_id": f"native_rc_adoption_{index}_{lane}",
            "lane": lane,
            "started_at": lane_started,
            "ended_at": lane_ended,
            "duration_ms": int((time.monotonic() - lane_start) * 1000),
            "input_requirement": case.get("input_requirement"),
            "runtime_choice": {"runtime": "mock", "mode": "dry_run" if dry_run else "local", "status": runtime_payload["status"], "reason": runtime_payload["reason"]},
            "commands_or_actions": [runtime_payload],
            "workspace_impact": workspace if lane == "repo_change_lane" else {"state": "not_applicable", "changed_files": [], "no_change": True, "reason": "lane_does_not_modify_workspace"},
            "rc_bundle_ref": _artifact_ref(bundle, path=bundle_path, kind="native_release_operator_bundle"),
            "validation_ref": _artifact_ref({**validation_ref_payload, "format": validation.get("format") or validation_ref_payload.get("format"), "verdict": validation.get("verdict") or validation_ref_payload.get("verdict"), "dry_run": validation.get("dry_run")}, path=validation_path, kind="native_rc_validation_run"),
            "outcome": decision,
            "pause_or_failure_reason": pause_reason,
            "recovery_action": recovery_action,
            "operator_decision": {"decision": decision, "reason": pause_reason},
            "next_action": next_action,
            "operator_friction": "dry_run_requires_real_operator_execution" if dry_run else "none",
        })
    report = build_rc_adoption_report({
        "format": RC_ADOPTION_LEDGER_VERSION,
        "artifact_kind": "native_rc_adoption_ledger",
        "case_pack": case_pack,
        "started_at": started_at,
        "ended_at": _now_iso(),
        "duration_ms": int((time.monotonic() - start) * 1000),
        "dry_run": dry_run,
        "records": records,
        "record_count": len(records),
        "rc_bundle_ref": _artifact_ref(bundle, path=bundle_path, kind="native_release_operator_bundle"),
        "validation_ref": _artifact_ref(validation, path=validation_path, kind="native_rc_validation_run"),
    })
    ledger = {**report["ledger"], "summary": report["summary"]}
    return ledger


def build_rc_adoption_report(ledger: dict[str, object]) -> dict[str, object]:
    if ledger.get("format") == RC_ADOPTION_REPORT_VERSION and isinstance(ledger.get("ledger"), dict):
        ledger_payload = ledger["ledger"]
    else:
        ledger_payload = ledger
    records = ledger_payload.get("records", []) if isinstance(ledger_payload.get("records"), list) else []
    decisions = [str(item.get("outcome")) for item in records if isinstance(item, dict)]
    if any(item == "stop" for item in decisions):
        verdict = "fail"
    elif any(item == "degrade" for item in decisions):
        verdict = "degraded"
    else:
        verdict = "pass"
    dry_run = bool(ledger_payload.get("dry_run"))
    bundle_ref = ledger_payload.get("rc_bundle_ref", {}) if isinstance(ledger_payload.get("rc_bundle_ref"), dict) else {}
    validation_ref = ledger_payload.get("validation_ref", {}) if isinstance(ledger_payload.get("validation_ref"), dict) else {}
    blocker = "none"
    blockers: list[str] = []
    if bundle_ref.get("state") in {"missing", "unavailable"} or validation_ref.get("state") in {"missing", "unavailable"}:
        blocker = "instrumentation_evidence"
        blockers.append("RC bundle or validation artifact is missing/unavailable")
    elif bundle_ref.get("verdict") == "fail" or validation_ref.get("verdict") == "fail":
        blocker = "product_thickness"
        blockers.append("RC bundle or validation verdict failed")
    elif dry_run:
        blocker = "operator_workflow_friction"
    lane_summaries = []
    drift = False
    for item in records:
        if not isinstance(item, dict):
            continue
        outcome = item.get("outcome")
        bundle_verdict = item.get("rc_bundle_ref", {}).get("verdict") if isinstance(item.get("rc_bundle_ref"), dict) else None
        if (bundle_verdict == "pass" and outcome == "stop") or (bundle_verdict in {"degraded", "fail"} and outcome == "continue"):
            drift = True
        impact = item.get("workspace_impact", {}) if isinstance(item.get("workspace_impact"), dict) else {}
        lane_summaries.append({
            "lane": item.get("lane"),
            "decision": outcome,
            "next_action": item.get("next_action"),
            "workspace_reviewable": impact.get("state") in {"available", "not_run", "not_applicable"},
            "pause_or_failure_reason": item.get("pause_or_failure_reason"),
        })
    summary = {
        "format": RC_ADOPTION_SUMMARY_VERSION,
        "verdict": verdict,
        "lane_count": len(records),
        "completed_lane_count": sum(1 for item in records if isinstance(item, dict) and item.get("outcome") == "continue"),
        "dry_run": dry_run,
        "gap_classification": blocker,
        "blockers": blockers,
        "lane_summaries": lane_summaries,
        "workspace_impact_reviewable": all(item.get("workspace_reviewable") for item in lane_summaries) if lane_summaries else False,
        "validation_drift": {"drift": drift, "rc_bundle_verdict": bundle_ref.get("verdict"), "validation_verdict": validation_ref.get("verdict")},
        "next_action": blockers[0] if blockers else "run rc-adopt without --dry-run for repo_change_lane" if dry_run else "continue local dogfood adoption loop",
        "operator_can_decide_without_raw_transcript": True,
    }
    return {
        "format": RC_ADOPTION_REPORT_VERSION,
        "artifact_kind": "native_rc_adoption_report",
        "ledger": ledger_payload,
        "summary": summary,
        "operator_report": {
            "supports_local_dogfood": verdict in {"pass", "degraded"},
            "continue_stop_degrade": {"continue": decisions.count("continue"), "stop": decisions.count("stop"), "degrade": decisions.count("degrade")},
            "gap_classification": blocker,
            "workspace_impact_reviewable": summary["workspace_impact_reviewable"],
            "rc_bundle_adoption_drift": summary["validation_drift"],
            "next_action": summary["next_action"],
        },
    }


def write_rc_adoption_ledger(path: str | Path, payload: dict[str, object]) -> dict[str, object]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"path": str(target), "state": "written", "bytes": target.stat().st_size}


def write_rc_adoption_report(path: str | Path, payload: dict[str, object]) -> dict[str, object]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"path": str(target), "state": "written", "bytes": target.stat().st_size}

def build_native_product_posture(
    *,
    provider_health_snapshot: dict[str, object] | None = None,
    runs_root: str | Path = ".agent_orchestrator/runs",
    project_root: str | Path = ".",
    authoritative_report_path: str | Path | None = None,
) -> dict[str, object]:
    setup = build_setup_diagnosis(provider_health_snapshot)
    evidence = build_evidence_consumption_summary(project_root=project_root, authoritative_report_path=authoritative_report_path)
    run_status = _latest_run_status(runs_root)
    closure = (evidence.get("authoritative_opencode_comparison", {}) or {}).get("instrumentation_closure") if isinstance(evidence.get("authoritative_opencode_comparison"), dict) else None
    decision = evidence.get("native_productization_next_step")
    blocker = "none"
    if setup.get("overall_posture") == "ready_with_degraded_external_runtime":
        blocker = "external_runtime_degraded_but_mock_available"
    return {
        "format": PRODUCT_POSTURE_VERSION,
        "product_posture": "daily_driver_candidate" if closure in {"closed", "partially_closed", "still_blocking"} else "productization_surface_ready",
        "active_goal": "native_productization_after_instrumentation_closure",
        "run_status": run_status,
        "provider_runtime_posture": setup,
        "evidence_summary": evidence,
        "authoritative_comparison_summary": evidence.get("authoritative_opencode_comparison"),
        "blocker_recovery": {
            "blocker": blocker,
            "recovery_reason": "use mock smoke path while external provider/runtime setup is repaired" if blocker != "none" else "none",
        },
        "next_action": decision or "run product smoke and inspect evidence summary",
        "recommended_commands": [
            "agent-orchestrator product posture --format json",
            "agent-orchestrator product smoke --format json",
            "agent-orchestrator product diagnose --format json",
            "agent-orchestrator product rc-report --format pretty --output .agent_orchestrator/release-candidate/report.json",
            "agent-orchestrator product rc-validate --dry-run --format pretty --output .agent_orchestrator/release-candidate/validation.json",
            "agent-orchestrator product rc-bundle --format pretty --output .agent_orchestrator/release-candidate/bundle.json",
        ],
    }


def run_product_smoke(
    *,
    requirement: str = "Productization smoke: prove native operator surface can start and summarize a daily-driver task.",
    runner: Callable[[str], Any] | None = None,
    project_root: str | Path = ".",
) -> dict[str, object]:
    if runner is not None:
        result = runner(requirement)
        payload = getattr(result, "payload", result)
        if not isinstance(payload, dict):
            payload = {"result": str(payload)}
        status = str(payload.get("status") or getattr(result, "status", "completed"))
        run_id = payload.get("run_id") or getattr(result, "run_id", None)
    else:
        from agent_orchestrator.evidence import capture_workflow_evidence

        payload = capture_workflow_evidence(
            [requirement],
            project_root=Path(project_root),
        )
        status = "completed"
        run_id = None
    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    return {
        "format": SMOKE_RESULT_VERSION,
        "requirement": requirement,
        "status": status,
        "run_id": run_id,
        "evidence_summary": summary,
        "operator_summary": {
            "outcome": status,
            "verify_or_stop": "verify" if status in {"completed", "accepted", "pass"} else "stop",
            "next_action": "inspect product posture" if status in {"completed", "accepted", "pass"} else "inspect blocker and rerun smoke",
            "readability": "clear",
        },
    }


def build_product_ux_snapshot(
    *,
    provider_health_snapshot: dict[str, object] | None = None,
    runs_root: str | Path = ".agent_orchestrator/runs",
    project_root: str | Path = ".",
    authoritative_report_path: str | Path | None = None,
) -> dict[str, object]:
    """Return a compact read-only product posture snapshot for CLI/UI/control-plane surfaces."""
    posture = build_native_product_posture(
        provider_health_snapshot=provider_health_snapshot,
        runs_root=runs_root,
        project_root=project_root,
        authoritative_report_path=authoritative_report_path,
    )
    run_status = posture.get("run_status", {}) if isinstance(posture.get("run_status"), dict) else {}
    setup = posture.get("provider_runtime_posture", {}) if isinstance(posture.get("provider_runtime_posture"), dict) else {}
    comparison = posture.get("authoritative_comparison_summary", {}) if isinstance(posture.get("authoritative_comparison_summary"), dict) else {}
    blocker = posture.get("blocker_recovery", {}) if isinstance(posture.get("blocker_recovery"), dict) else {}
    provider_count = len(setup.get("providers", [])) if isinstance(setup.get("providers"), list) else 0
    degraded_provider_count = sum(
        1 for item in setup.get("providers", [])
        if isinstance(item, dict) and item.get("degraded_mode")
    ) if isinstance(setup.get("providers"), list) else 0
    rc_gate = build_release_candidate_gate(
        provider_health_snapshot=provider_health_snapshot,
        runs_root=runs_root,
        project_root=project_root,
        authoritative_report_path=authoritative_report_path,
    )
    rc_bundle = build_release_operator_bundle(
        provider_health_snapshot=provider_health_snapshot,
        runs_root=runs_root,
        project_root=project_root,
        authoritative_report_path=authoritative_report_path,
        dry_run_validation=True,
    )
    adoption_ledger = run_rc_adoption(
        provider_health_snapshot=provider_health_snapshot,
        runs_root=runs_root,
        project_root=project_root,
        authoritative_report_path=authoritative_report_path,
        dry_run=True,
    )
    adoption_report = build_rc_adoption_report(adoption_ledger)
    adoption_summary = adoption_report.get("summary", {}) if isinstance(adoption_report.get("summary"), dict) else {}
    return {
        "format": PRODUCT_UX_SNAPSHOT_VERSION,
        "read_only": True,
        "product_posture": posture.get("product_posture"),
        "active_goal": posture.get("active_goal"),
        "run_status": {
            "status": run_status.get("status"),
            "latest_run_id": run_status.get("latest_run_id"),
            "reason": run_status.get("reason"),
        },
        "provider_runtime": {
            "overall_posture": setup.get("overall_posture"),
            "release_candidate_verdict": setup.get("release_candidate_verdict"),
            "install_release_candidate_ready": setup.get("install_release_candidate_ready"),
            "provider_count": provider_count,
            "degraded_provider_count": degraded_provider_count,
            "fix_hints": setup.get("fix_hints", []),
            "smoke_commands": setup.get("smoke_commands", []),
        },
        "evidence": {
            "instrumentation_closure": comparison.get("instrumentation_closure"),
            "operator_decision": comparison.get("operator_decision"),
            "case_result_count": comparison.get("case_result_count"),
        },
        "blocker_recovery": blocker,
        "next_action": posture.get("next_action"),
        "recommended_commands": posture.get("recommended_commands", []),
        "release_candidate": {
            "format": rc_gate.get("format"),
            "verdict": rc_gate.get("verdict"),
            "install_release_candidate_ready": rc_gate.get("install_release_candidate_ready"),
            "blockers": rc_gate.get("blockers", []),
            "warnings": rc_gate.get("warnings", []),
            "next_actions": rc_gate.get("next_actions", []),
        },
        "release_bundle": {
            "format": rc_bundle.get("format"),
            "verdict": rc_bundle.get("verdict"),
            "blockers": rc_bundle.get("blockers", []),
            "warnings": rc_bundle.get("warnings", []),
            "operator_summary": rc_bundle.get("operator_summary", {}),
        },
        "native_rc_adoption": adoption_summary,
        "operator_can_decide_without_raw_json": bool(
            posture.get("evidence_summary", {}).get("operator_can_decide_without_raw_json")
            if isinstance(posture.get("evidence_summary"), dict) else False
        ),
    }
