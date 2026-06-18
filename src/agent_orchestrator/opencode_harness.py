"""Same-contract external OpenCode harness records for daily-driver comparison."""
from __future__ import annotations

# DEPS: __future__, dataclasses, json, pathlib, typing
# RESPONSIBILITY: Build portable same-contract case packs, OpenCode runner records, comparative reports, and operator decisions.
# MODULE: decision_core
# ---

import json
import shlex
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CASE_PACK_VERSION = "external_opencode_same_contract.v1"
OPENCODE_RUN_RECORD_VERSION = "opencode_external_runner_record.v1"
NATIVE_RUN_RECORD_VERSION = "native_external_runner_record.v1"
COMPARATIVE_REPORT_VERSION = "native_vs_opencode_comparative_evidence.v1"
NORMALIZED_RECORD_VERSION = "external_opencode_authoritative_normalized_record.v1"
AUTHORITATIVE_REPORT_VERSION = "native_vs_opencode_authoritative_comparative_evidence.v1"
OPERATOR_DECISION_PATHS = {
    "continue_opencode_ecosystem_chase",
    "native_productization_next",
    "instrumentation_first",
    "mixed_strategy",
}
REQUIRED_EVIDENCE_SURFACE = [
    "runtime_payload",
    "workspace_index_summary",
    "operator_summary",
    "failure_pause_recovery_reason",
]
TASK_FAMILIES = [
    "docs_update",
    "single_file_repair",
    "multi_file_operator_surface",
    "test_driven_small_feature",
    "failure_clarify_approval_path",
]


@dataclass(frozen=True, slots=True)
class SameContractCase:
    case_id: str
    task_family: str
    repo_state_ref: str
    input_prompt: str
    expected_touch_scope: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    verify_command: str | None
    manual_verify_contract: tuple[str, ...]
    stop_condition: str
    pause_condition: str
    failure_condition: str
    native_runner_entry: str
    opencode_runner_entry: str
    comparison_notes: str

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "task_family": self.task_family,
            "repo_state_ref": self.repo_state_ref,
            "input_prompt": self.input_prompt,
            "expected_touch_scope": list(self.expected_touch_scope),
            "expected_outputs": list(self.expected_outputs),
            "verify_command": self.verify_command,
            "manual_verify_contract": list(self.manual_verify_contract),
            "stop_condition": self.stop_condition,
            "pause_condition": self.pause_condition,
            "failure_condition": self.failure_condition,
            "required_evidence_surface": list(REQUIRED_EVIDENCE_SURFACE),
            "native_runner_entry": self.native_runner_entry,
            "opencode_runner_entry": self.opencode_runner_entry,
            "comparison_notes": self.comparison_notes,
        }


def build_same_contract_case_pack(*, repo_state_ref: str = "current_daily_driver_repeatability_baseline") -> dict[str, object]:
    """Return the fixed 5-family case contract runnable by native and OpenCode adapters."""
    cases = [
        SameContractCase(
            case_id="docs_update_001",
            task_family="docs_update",
            repo_state_ref=repo_state_ref,
            input_prompt=(
                "Update the goal summary/detail docs so P0-P3 status, evidence baseline, "
                "and next operator action remain consistent."
            ),
            expected_touch_scope=("docs/process/**",),
            expected_outputs=("summary updated", "detail updated", "cross-link intact"),
            verify_command="pytest tests/test_docs_process.py -q",
            manual_verify_contract=("summary references detail", "P0-P3 sections present", "non-goals preserved"),
            stop_condition="verify passes or an explicit doc-level stop reason is recorded",
            pause_condition="missing source evidence or write approval is required",
            failure_condition="docs disagree, no verify evidence, or no stop reason",
            native_runner_entry="agent-orchestrator evidence capture --case-file docs/process/external-opencode-same-contract-cases.json --output native-run.json",
            opencode_runner_entry="agent-orchestrator evidence opencode-run --case-pack docs/process/external-opencode-same-contract-cases.json --output opencode-run.json",
            comparison_notes="same prompt, doc touch scope, and verify/stop standard for both runners",
        ),
        SameContractCase(
            case_id="single_file_repair_001",
            task_family="single_file_repair",
            repo_state_ref=repo_state_ref,
            input_prompt=(
                "Perform a one-file behavior repair and prove it with a focused test or explicit stop reason."
            ),
            expected_touch_scope=("src/agent_orchestrator/**", "tests/**"),
            expected_outputs=("single implementation file repaired", "focused verification recorded"),
            verify_command="pytest tests/test_coding_agent_runtime.py -q",
            manual_verify_contract=("touch scope is bounded", "repair reason is visible", "verification or stop is recorded"),
            stop_condition="focused verification passes or repair cannot proceed with a semantic stop reason",
            pause_condition="ambiguous target behavior or approval boundary blocks the edit",
            failure_condition="multiple unrelated files changed, no verification, or recovery reason missing",
            native_runner_entry="agent-orchestrator evidence capture --case-file docs/process/external-opencode-same-contract-cases.json --output native-run.json",
            opencode_runner_entry="agent-orchestrator evidence opencode-run --case-pack docs/process/external-opencode-same-contract-cases.json --output opencode-run.json",
            comparison_notes="same one-file repair contract and verify/stop gate",
        ),
        SameContractCase(
            case_id="multi_file_operator_surface_001",
            task_family="multi_file_operator_surface",
            repo_state_ref=repo_state_ref,
            input_prompt=(
                "Update a multi-file operator surface so runtime payload, workspace index, "
                "and CLI/operator summary describe the same fact chain."
            ),
            expected_touch_scope=("src/agent_orchestrator/**", "tests/**", "docs/process/**"),
            expected_outputs=("runtime payload aligned", "workspace index aligned", "CLI/operator summary aligned"),
            verify_command="pytest tests/test_evidence.py tests/test_cli.py -q",
            manual_verify_contract=("fact chain visible on at least two surfaces", "operator summary has next action"),
            stop_condition="surface verification passes or mismatch is stopped with evidence pointers",
            pause_condition="approval needed for broad multi-file surface changes",
            failure_condition="surfaces diverge, no next action, or no workspace index summary",
            native_runner_entry="agent-orchestrator evidence capture --case-file docs/process/external-opencode-same-contract-cases.json --output native-run.json",
            opencode_runner_entry="agent-orchestrator evidence opencode-run --case-pack docs/process/external-opencode-same-contract-cases.json --output opencode-run.json",
            comparison_notes="same multi-surface consistency contract for both runners",
        ),
        SameContractCase(
            case_id="test_driven_small_feature_001",
            task_family="test_driven_small_feature",
            repo_state_ref=repo_state_ref,
            input_prompt=(
                "Add a small test-driven contract feature, update the minimal implementation, and record verification."
            ),
            expected_touch_scope=("src/agent_orchestrator/**", "tests/**"),
            expected_outputs=("test added or updated", "implementation updated", "verification recorded"),
            verify_command="pytest tests/test_evidence.py -q",
            manual_verify_contract=("test fails without feature", "implementation is minimal", "verification evidence is linked"),
            stop_condition="test passes or stop reason explains why feature cannot be safely implemented",
            pause_condition="test intent is ambiguous or requires operator choice",
            failure_condition="implementation lacks a test, verify missing, or failure has no next step",
            native_runner_entry="agent-orchestrator evidence capture --case-file docs/process/external-opencode-same-contract-cases.json --output native-run.json",
            opencode_runner_entry="agent-orchestrator evidence opencode-run --case-pack docs/process/external-opencode-same-contract-cases.json --output opencode-run.json",
            comparison_notes="same test-first expected output and verify/stop gate",
        ),
        SameContractCase(
            case_id="failure_clarify_approval_path_001",
            task_family="failure_clarify_approval_path",
            repo_state_ref=repo_state_ref,
            input_prompt=(
                "Exercise a failure, clarify, approval pause, resume, or stop path and record the semantic recovery reason."
            ),
            expected_touch_scope=("docs/process/**", "src/agent_orchestrator/**", "tests/**"),
            expected_outputs=("pause or stop reason", "recovery next action", "operator-readable summary"),
            verify_command=None,
            manual_verify_contract=("pause/failure/stop reason is semantic", "resume expectation is explicit", "workspace is not damaged"),
            stop_condition="explicit stop reason with next action is recorded",
            pause_condition="approval, missing context, or unsafe change boundary is reached",
            failure_condition="blocked state has no reason, no next action, or workspace integrity is unclear",
            native_runner_entry="agent-orchestrator evidence capture --case-file docs/process/external-opencode-same-contract-cases.json --output native-run.json",
            opencode_runner_entry="agent-orchestrator evidence opencode-run --case-pack docs/process/external-opencode-same-contract-cases.json --output opencode-run.json",
            comparison_notes="same boundary-semantics contract; stop is acceptable when verify is not applicable",
        ),
    ]
    return {
        "contract_version": CASE_PACK_VERSION,
        "case_family_count": len(TASK_FAMILIES),
        "required_task_families": list(TASK_FAMILIES),
        "required_evidence_surface": list(REQUIRED_EVIDENCE_SURFACE),
        "runner_contract": {
            "native": NATIVE_RUN_RECORD_VERSION,
            "opencode": OPENCODE_RUN_RECORD_VERSION,
            "comparative_report": COMPARATIVE_REPORT_VERSION,
        },
        "cases": [case.to_dict() for case in cases],
    }


def load_case_pack(path: str | Path | None = None) -> dict[str, object]:
    if path is None:
        return build_same_contract_case_pack()
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("case pack must be a JSON object")
    return payload


def write_case_pack(path: str | Path, case_pack: dict[str, object] | None = None) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(case_pack or build_same_contract_case_pack(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output



def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _summarize_stream(value: str, *, limit: int = 4000) -> dict[str, object]:
    text = value or ""
    return {
        "available": True,
        "line_count": len(text.splitlines()),
        "truncated": len(text) > limit,
        "text": text[:limit],
    }


def _git_workspace_snapshot(workspace_dir: str | Path | None) -> dict[str, object]:
    cwd = Path(workspace_dir or Path.cwd())
    try:
        completed = subprocess.run(
            ["git", "status", "--short"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except Exception as exc:  # pragma: no cover - defensive for non-git or sandbox edge cases
        return {"state": "unavailable", "files": [], "reason": f"git_status_unavailable:{exc.__class__.__name__}"}
    if completed.returncode != 0:
        return {
            "state": "unavailable",
            "files": [],
            "reason": (completed.stderr or completed.stdout or "git_status_failed").strip()[:300],
        }
    files: list[str] = []
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:] if len(line) > 3 else line.strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return {"state": "available", "files": sorted(dict.fromkeys(files)), "reason": "git_status_available"}


def _workspace_delta(before: dict[str, object], after: dict[str, object]) -> dict[str, object]:
    if before.get("state") != "available" or after.get("state") != "available":
        return {
            "state": "unavailable",
            "changed_files": [],
            "reason": after.get("reason") or before.get("reason") or "workspace_snapshot_unavailable",
        }
    before_files = set(str(item) for item in before.get("files", []) if item)
    after_files = set(str(item) for item in after.get("files", []) if item)
    changed = sorted(after_files.symmetric_difference(before_files))
    return {
        "state": "available",
        "changed_files": changed,
        "reason": "workspace_changed" if changed else "no_change_detected",
    }


def _default_opencode_command(case: dict[str, object], workspace_dir: str | Path | None = None) -> str:
    prompt = str(case.get("input_prompt") or "")
    quoted_prompt = shlex.quote(prompt)
    dir_arg = f" --dir {shlex.quote(str(workspace_dir))}" if workspace_dir else ""
    return f"opencode run --format json{dir_arg} {quoted_prompt}"

def _unavailable(reason: str) -> dict[str, str]:
    return {"value": "unavailable", "reason": reason}



def _semantic_failure_reason(exit_status: object, stderr_summary: object) -> str:
    if exit_status in (0, "0", None):
        return "none"
    text = ""
    if isinstance(stderr_summary, dict):
        text = str(stderr_summary.get("text") or "")
    lowered = text.lower()
    if "models.dev" in lowered or "unable to connect" in lowered:
        return "opencode_provider_catalog_unreachable"
    if "provider" in lowered or "auth" in lowered or "credential" in lowered:
        return "opencode_provider_or_auth_unavailable"
    if "pragma wal_checkpoint" in lowered or "database" in lowered or "sqlite" in lowered:
        return "opencode_runtime_storage_failure"
    if exit_status == "timeout":
        return "opencode_command_timeout"
    return f"opencode_command_exit_{exit_status}"


def _is_product_or_ecosystem_failure(record: dict[str, object]) -> bool:
    reasons = record.get("failure_pause_recovery_reason", {}) if isinstance(record.get("failure_pause_recovery_reason"), dict) else {}
    reason = str(reasons.get("failure_reason") or "")
    return reason in {
        "opencode_provider_catalog_unreachable",
        "opencode_provider_or_auth_unavailable",
        "opencode_runtime_storage_failure",
        "opencode_command_timeout",
    }

def _case_status(case: dict[str, object], *, simulate_status: str) -> str:
    if simulate_status in {"pass", "pause", "fail", "stop"}:
        return simulate_status
    return "stop" if not case.get("verify_command") else "pass"


def build_opencode_run_record(
    case: dict[str, object],
    *,
    status: str | None = None,
    command: str | None = None,
    command_template: str | None = None,
    authoritative_runner: bool = False,
    changed_files: list[str] | None = None,
    workspace_dir: str | Path | None = None,
    timeout_seconds: int = 120,
    unavailable_reason: str = "minimal_adapter_does_not_claim_full_opencode_product_integration",
) -> dict[str, object]:
    """Build an OpenCode run record, optionally executing an authoritative command per case."""
    run_status = _case_status(case, simulate_status=status or "auto")
    unavailable_fields = ["model", "provider", "cost", "tokens"]
    verify_command = case.get("verify_command")
    executed_command = command or case.get("opencode_runner_entry") or "opencode run <same-contract-case>"
    started_at: str | dict[str, str] = _unavailable(unavailable_reason)
    ended_at: str | dict[str, str] = _unavailable(unavailable_reason)
    duration_ms: int | dict[str, str] = _unavailable(unavailable_reason)
    exit_status: int | str = 0 if run_status in {"pass", "stop"} else "unavailable"
    stdout_summary: dict[str, object] | dict[str, str] = _unavailable("command_not_executed")
    stderr_summary: dict[str, object] | dict[str, str] = _unavailable("command_not_executed")
    execution_blocker: dict[str, object] | None = None
    workspace_before = _git_workspace_snapshot(workspace_dir)
    workspace_after = workspace_before
    workspace_delta = {"state": "unavailable", "changed_files": [], "reason": "command_not_executed"}
    should_execute = bool(command_template or command or authoritative_runner)
    if command_template:
        executed_command = command_template.format(
            case_id=case.get("case_id"),
            task_family=case.get("task_family"),
            input_prompt=str(case.get("input_prompt") or "").replace('"', '\"'),
        )
    elif authoritative_runner and not command:
        executed_command = _default_opencode_command(case, workspace_dir)
    if should_execute:
        started_at = _utc_now()
        start = time.perf_counter()
        try:
            completed = subprocess.run(
                executed_command,
                shell=True,
                cwd=Path(workspace_dir) if workspace_dir else None,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_seconds,
            )
            exit_status = completed.returncode
            stdout_summary = _summarize_stream(completed.stdout)
            stderr_summary = _summarize_stream(completed.stderr)
            run_status = status or ("pass" if completed.returncode == 0 else "fail")
        except subprocess.TimeoutExpired as exc:
            exit_status = "timeout"
            stdout_summary = _summarize_stream(exc.stdout if isinstance(exc.stdout, str) else "")
            stderr_summary = _summarize_stream(exc.stderr if isinstance(exc.stderr, str) else "")
            run_status = status or "blocked"
            execution_blocker = {
                "blocker_type": "timeout",
                "unavailable_reason": f"command_timed_out_after_{timeout_seconds}s",
                "blocks_capability_comparison": True,
                "next_action_required": "rerun with a working authoritative OpenCode environment or a longer timeout",
            }
        except FileNotFoundError:
            exit_status = "unavailable"
            run_status = status or "blocked"
            execution_blocker = {
                "blocker_type": "missing_binary",
                "unavailable_reason": "opencode_command_not_found",
                "blocks_capability_comparison": True,
                "next_action_required": "install or expose OpenCode CLI before authoritative comparison",
            }
        duration_ms = int((time.perf_counter() - start) * 1000)
        ended_at = _utc_now()
        workspace_after = _git_workspace_snapshot(workspace_dir)
        workspace_delta = _workspace_delta(workspace_before, workspace_after)
    else:
        unavailable_fields.extend(["started_at", "ended_at", "duration_ms"])
    changed_files = list(changed_files or [])
    if not changed_files and workspace_delta.get("state") == "available":
        changed_files = [str(item) for item in workspace_delta.get("changed_files", [])]
    diff_summary = workspace_delta.get("reason") or "minimal_adapter_summary_available"
    workspace_reason = workspace_delta.get("reason") or "workspace_summary_available"
    if not changed_files and not should_execute:
        scopes = case.get("expected_touch_scope", [])
        changed_files = [str(scopes[0])] if isinstance(scopes, list) and scopes else []
    semantic_failure_reason = _semantic_failure_reason(exit_status, stderr_summary)
    return {
        "run_record_version": OPENCODE_RUN_RECORD_VERSION,
        "runner": "opencode",
        "case_id": case.get("case_id"),
        "task_family": case.get("task_family"),
        "status": run_status,
        "runner_authority": {
            "authoritative": authoritative_runner,
            "reason": "explicit_authoritative_runner" if authoritative_runner else "smoke_command_or_minimal_adapter_not_authoritative",
        },
        "runtime_payload": {
            "command": executed_command,
            "model": _unavailable(unavailable_reason),
            "provider": _unavailable(unavailable_reason),
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_ms": duration_ms,
            "exit_status": exit_status,
            "stdout_summary": stdout_summary,
            "stderr_summary": stderr_summary,
            "cost": _unavailable(unavailable_reason),
            "tokens": _unavailable(unavailable_reason),
        },
        "workspace_index_summary": {
            "changed_files": changed_files,
            "created_artifacts": [],
            "verify_commands": [verify_command] if isinstance(verify_command, str) and verify_command else [],
            "diff_summary": diff_summary,
            "workspace_before": workspace_before,
            "workspace_after": workspace_after,
            "artifact_pointer": None,
            "reason": workspace_reason,
            "repo_state_ref": case.get("repo_state_ref"),
        },
        "operator_summary": {
            "outcome": f"{run_status}: {case.get('case_id')}",
            "verification": verify_command or "manual_verify_contract_or_stop_condition",
            "next_action": "compare_against_native_run_record",
            "readability_notes": "same_contract_operator_summary_equivalent",
        },
        "failure_pause_recovery_reason": {
            "failure_reason": semantic_failure_reason if run_status not in {"pass", "stop"} else "none",
            "pause_reason": str(case.get("pause_condition")) if run_status == "pause" else "none",
            "recovery_reason": "repair_opencode_runtime_or_compare_native_and_opencode_evidence_surface" if semantic_failure_reason != "none" else "compare_native_and_opencode_evidence_surface",
            "stop_reason": str(case.get("stop_condition")) if run_status == "stop" else "none",
            "unavailable_fields": unavailable_fields,
            "unavailable_reason": execution_blocker.get("unavailable_reason") if execution_blocker else "none",
            "blocker_type": execution_blocker.get("blocker_type") if execution_blocker else "none",
            "blocks_capability_comparison": execution_blocker.get("blocks_capability_comparison") if execution_blocker else False,
            "next_action_required": execution_blocker.get("next_action_required") if execution_blocker else "none",
        },
    }


def build_native_run_record(case: dict[str, object], *, status: str = "pass") -> dict[str, object]:
    verify_command = case.get("verify_command")
    return {
        "run_record_version": NATIVE_RUN_RECORD_VERSION,
        "runner": "native",
        "case_id": case.get("case_id"),
        "task_family": case.get("task_family"),
        "status": status,
        "runtime_payload": {
            "command": case.get("native_runner_entry"),
            "model": "native_control_plane",
            "provider": "local",
            "started_at": "available_in_runtime_payload",
            "ended_at": "available_in_runtime_payload",
            "duration_ms": "available_in_runtime_payload",
            "exit_status": 0 if status in {"pass", "stop"} else 1,
        },
        "workspace_index_summary": {
            "changed_files": list(case.get("expected_touch_scope", [])) if isinstance(case.get("expected_touch_scope"), list) else [],
            "created_artifacts": ["runtime_payload", "workspace_index", "cli_summary"],
            "verify_commands": [verify_command] if isinstance(verify_command, str) and verify_command else [],
            "diff_summary": "native_daily_driver_repeatability_baseline",
            "repo_state_ref": case.get("repo_state_ref"),
        },
        "operator_summary": {
            "outcome": f"{status}: {case.get('case_id')}",
            "verification": verify_command or "manual_verify_contract_or_stop_condition",
            "next_action": "compare_against_opencode_run_record",
            "readability_notes": "native_operator_summary_available",
        },
        "failure_pause_recovery_reason": {
            "failure_reason": "none" if status in {"pass", "stop"} else "native_execution_failed",
            "pause_reason": "none",
            "recovery_reason": "workspace_index_cli_summary_runtime_payload_aligned",
            "stop_reason": str(case.get("stop_condition")) if status == "stop" else "none",
            "unavailable_fields": [],
        },
    }


def build_opencode_run_records(
    case_pack: dict[str, object],
    *,
    status_by_case: dict[str, str] | None = None,
    command_template: str | None = None,
    authoritative_runner: bool = False,
    workspace_dir: str | Path | None = None,
    timeout_seconds: int = 120,
) -> dict[str, object]:
    cases = case_pack.get("cases", []) if isinstance(case_pack.get("cases"), list) else []
    status_by_case = status_by_case or {}
    return {
        "run_record_set_version": OPENCODE_RUN_RECORD_VERSION,
        "runner": "opencode",
        "case_pack_version": case_pack.get("contract_version"),
        "records": [
            build_opencode_run_record(
                case,
                status=status_by_case.get(str(case.get("case_id"))),
                command_template=command_template,
                authoritative_runner=authoritative_runner,
                workspace_dir=workspace_dir,
                timeout_seconds=timeout_seconds,
            )
            for case in cases
            if isinstance(case, dict)
        ],
    }


def build_native_run_records(case_pack: dict[str, object], *, status_by_case: dict[str, str] | None = None) -> dict[str, object]:
    cases = case_pack.get("cases", []) if isinstance(case_pack.get("cases"), list) else []
    status_by_case = status_by_case or {}
    return {
        "run_record_set_version": NATIVE_RUN_RECORD_VERSION,
        "runner": "native",
        "case_pack_version": case_pack.get("contract_version"),
        "records": [build_native_run_record(case, status=status_by_case.get(str(case.get("case_id")), "pass")) for case in cases if isinstance(case, dict)],
    }


def _records_by_case(record_set: dict[str, object]) -> dict[str, dict[str, object]]:
    records = record_set.get("records", []) if isinstance(record_set.get("records"), list) else []
    return {str(record.get("case_id")): record for record in records if isinstance(record, dict) and record.get("case_id")}


def _has_unavailable(record: dict[str, object]) -> bool:
    reasons = record.get("failure_pause_recovery_reason", {}) if isinstance(record, dict) else {}
    if isinstance(reasons, dict) and reasons.get("unavailable_fields"):
        return True
    runtime = record.get("runtime_payload", {}) if isinstance(record.get("runtime_payload"), dict) else {}
    return any(isinstance(value, dict) and value.get("value") == "unavailable" for value in runtime.values())


def _delta(native_record: dict[str, object], opencode_record: dict[str, object], dimension: str) -> str:
    native_status = native_record.get("status")
    opencode_status = opencode_record.get("status")
    if native_status == opencode_status:
        if dimension in {"evidence", "cost_latency"} and _has_unavailable(opencode_record):
            return "native_better"
        return "equivalent"
    if native_status == "pass" and opencode_status != "pass":
        return "native_better"
    if opencode_status == "pass" and native_status != "pass":
        return "opencode_better"
    return "inconclusive"


def classify_gap(native_record: dict[str, object], opencode_record: dict[str, object]) -> list[str]:
    gaps: list[str] = []
    if native_record.get("status") != opencode_record.get("status"):
        gaps.append("agent_capability_gap")
    if _has_unavailable(opencode_record):
        gaps.append("instrumentation_gap")
    gaps.extend(["product_thickness_gap", "ecosystem_gap"])
    return list(dict.fromkeys(gaps))


def build_operator_decision(case_results: list[dict[str, object]]) -> dict[str, object]:
    gap_counts: dict[str, int] = {}
    for result in case_results:
        gaps = result.get("gap_classification", []) if isinstance(result.get("gap_classification"), list) else []
        for gap in gaps:
            gap_counts[str(gap)] = gap_counts.get(str(gap), 0) + 1
    agent_gap = gap_counts.get("agent_capability_gap", 0)
    instrumentation_gap = gap_counts.get("instrumentation_gap", 0)
    product_gap = gap_counts.get("product_thickness_gap", 0)
    ecosystem_gap = gap_counts.get("ecosystem_gap", 0)
    if instrumentation_gap and instrumentation_gap >= max(agent_gap, 1):
        recommended = "instrumentation_first"
        reason = "OpenCode fields are unavailable often enough that evidence-surface equivalence must improve before capability judgment."
        next_moves = ["harden OpenCode run-record export", "rerun the same-contract case pack", "then decide between ecosystem chase and native productization"]
        non_moves = ["do not claim agent capability superiority from missing telemetry"]
    elif agent_gap > product_gap + ecosystem_gap:
        recommended = "continue_opencode_ecosystem_chase"
        reason = "Same-contract case outcomes show a material task-completion gap."
        next_moves = ["inspect failed native cases", "compare OpenCode recovery traces", "prioritize capability repair"]
        non_moves = ["do not mask capability gaps as UI work"]
    elif product_gap or ecosystem_gap:
        recommended = "native_productization_next"
        reason = "Same-contract execution is comparable; the remaining delta is mainly product thickness and ecosystem scale."
        next_moves = ["productize native operator surface", "prioritize TUI/provider/install release", "keep same-contract regression pack"]
        non_moves = ["do not build full OpenCode clone inside this harness goal"]
    else:
        recommended = "mixed_strategy"
        reason = "No single gap class dominates across task families."
        next_moves = ["split decisions by task family", "expand only inconclusive evidence", "keep common contract stable"]
        non_moves = ["do not average away per-family gaps"]
    return {"recommended_path": recommended, "reason": reason, "gap_counts": gap_counts, "next_moves": next_moves[:3], "non_moves": non_moves}


def build_comparative_evidence_report(case_pack: dict[str, object], native_records: dict[str, object], opencode_records: dict[str, object]) -> dict[str, object]:
    native_by_case = _records_by_case(native_records)
    opencode_by_case = _records_by_case(opencode_records)
    case_results: list[dict[str, object]] = []
    cases = case_pack.get("cases", []) if isinstance(case_pack.get("cases"), list) else []
    for case in cases:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id"))
        native_record = native_by_case.get(case_id, {})
        opencode_record = opencode_by_case.get(case_id, {})
        gap_classification = classify_gap(native_record, opencode_record)
        case_results.append({
            "case_id": case_id,
            "task_family": case.get("task_family"),
            "native_status": native_record.get("status", "fail"),
            "opencode_status": opencode_record.get("status", "fail"),
            "verify_or_stop_consistent": bool(case.get("verify_command") or case.get("stop_condition")),
            "recovery_quality_delta": _delta(native_record, opencode_record, "recovery"),
            "evidence_completeness_delta": _delta(native_record, opencode_record, "evidence"),
            "operator_readability_delta": _delta(native_record, opencode_record, "operator"),
            "cost_latency_availability_delta": _delta(native_record, opencode_record, "cost_latency"),
            "gap_classification": gap_classification,
            "evidence_pointers": [f"native.records[{case_id}]", f"opencode.records[{case_id}]", f"case_pack.cases[{case_id}]"],
        })
    decision = build_operator_decision(case_results)
    return {
        "report_version": COMPARATIVE_REPORT_VERSION,
        "case_pack_version": case_pack.get("contract_version"),
        "summary_verdict": decision["reason"],
        "case_result_count": len(case_results),
        "case_results": case_results,
        "gap_taxonomy": ["agent_capability_gap", "product_thickness_gap", "ecosystem_gap", "instrumentation_gap"],
        "operator_decision": decision,
    }



def _state(value: object, *, reason: str | None = None, not_applicable: bool = False) -> dict[str, object]:
    if not_applicable:
        return {"state": "not_applicable", "value": None, "reason": reason or "not_applicable"}
    if isinstance(value, dict) and value.get("value") == "unavailable":
        return {"state": "unavailable", "value": None, "reason": value.get("reason") or reason or "unavailable"}
    if value is None:
        return {"state": "missing", "value": None, "reason": reason or "missing"}
    if value == "unavailable":
        return {"state": "unavailable", "value": None, "reason": reason or "unavailable"}
    return {"state": "available", "value": value}


def normalize_run_record(record: dict[str, object], *, case: dict[str, object] | None = None) -> dict[str, object]:
    """Normalize native/OpenCode raw records into the authoritative comparison schema."""
    case = case if isinstance(case, dict) else {}
    runtime = record.get("runtime_payload", {}) if isinstance(record.get("runtime_payload"), dict) else {}
    workspace = record.get("workspace_index_summary", {}) if isinstance(record.get("workspace_index_summary"), dict) else {}
    operator = record.get("operator_summary", {}) if isinstance(record.get("operator_summary"), dict) else {}
    reasons = record.get("failure_pause_recovery_reason", {}) if isinstance(record.get("failure_pause_recovery_reason"), dict) else {}
    verify_commands = workspace.get("verify_commands", []) if isinstance(workspace.get("verify_commands"), list) else []
    changed_files = workspace.get("changed_files", []) if isinstance(workspace.get("changed_files"), list) else []
    workspace_state = "available" if changed_files or verify_commands or workspace.get("diff_summary") else "unavailable"
    workspace_reason = "workspace_summary_available" if workspace_state == "available" else "workspace_summary_missing"
    verify_or_stop = "verify" if verify_commands or case.get("verify_command") else "stop"
    unavailable_fields = reasons.get("unavailable_fields", []) if isinstance(reasons.get("unavailable_fields"), list) else []
    runner_authority = record.get("runner_authority", {}) if isinstance(record.get("runner_authority"), dict) else {}
    runner_authoritative = record.get("runner") == "native" or runner_authority.get("authoritative") is True
    runtime_payload = {
        "command": _state(runtime.get("command")),
        "exit_status": _state(runtime.get("exit_status")),
        "started_at": _state(runtime.get("started_at")),
        "ended_at": _state(runtime.get("ended_at")),
        "duration_ms": _state(runtime.get("duration_ms")),
        "model": _state(runtime.get("model")),
        "provider": _state(runtime.get("provider")),
        "cost": _state(runtime.get("cost"), reason="cost_not_reported_by_runner"),
        "tokens": _state(runtime.get("tokens"), reason="tokens_not_reported_by_runner"),
    }
    available_required = all(
        runtime_payload[key].get("state") == "available"
        for key in ("command", "exit_status", "started_at", "ended_at", "duration_ms")
    )
    return {
        "normalized_record_version": NORMALIZED_RECORD_VERSION,
        "runner": record.get("runner"),
        "case_id": record.get("case_id"),
        "task_family": record.get("task_family"),
        "status": record.get("status") or "blocked",
        "runtime_payload": runtime_payload,
        "workspace_index_summary": {
            "state": workspace_state,
            "changed_files": changed_files,
            "created_artifacts": list(workspace.get("created_artifacts", [])) if isinstance(workspace.get("created_artifacts"), list) else [],
            "verify_commands": verify_commands,
            "artifact_pointer": workspace.get("artifact_pointer"),
            "reason": workspace.get("reason") or workspace_reason,
        },
        "operator_summary": {
            "outcome": operator.get("outcome") or record.get("status") or "unknown",
            "verify_or_stop": verify_or_stop,
            "next_action": operator.get("next_action") or "review_normalized_record",
            "readability": "clear" if operator.get("outcome") and operator.get("next_action") else "partial",
        },
        "failure_pause_recovery_reason": {
            "failure_reason": reasons.get("failure_reason") or "none",
            "pause_reason": reasons.get("pause_reason") or "none",
            "recovery_reason": reasons.get("recovery_reason") or "none",
            "stop_reason": reasons.get("stop_reason") or "none",
            "unavailable_fields": unavailable_fields,
        },
        "authoritative_execution": {
            "required_runtime_fields_available": available_required,
            "command_executed": runtime_payload["command"].get("state") == "available" and runtime_payload["exit_status"].get("state") == "available",
            "runner_authoritative": runner_authoritative,
            "runner_authority_reason": runner_authority.get("reason") or ("native_baseline" if record.get("runner") == "native" else "missing_runner_authority"),
            "blocks_capability_comparison": (not available_required) or (not runner_authoritative),
        },
    }


def normalize_run_records(record_set: dict[str, object], case_pack: dict[str, object]) -> dict[str, object]:
    cases = case_pack.get("cases", []) if isinstance(case_pack.get("cases"), list) else []
    cases_by_id = {str(case.get("case_id")): case for case in cases if isinstance(case, dict)}
    records = record_set.get("records", []) if isinstance(record_set.get("records"), list) else []
    normalized = [
        normalize_run_record(record, case=cases_by_id.get(str(record.get("case_id")), {}))
        for record in records
        if isinstance(record, dict)
    ]
    return {
        "normalized_record_set_version": NORMALIZED_RECORD_VERSION,
        "runner": record_set.get("runner"),
        "case_pack_version": case_pack.get("contract_version"),
        "records": normalized,
    }


def _normalized_by_case(record_set: dict[str, object]) -> dict[str, dict[str, object]]:
    records = record_set.get("records", []) if isinstance(record_set.get("records"), list) else []
    return {str(record.get("case_id")): record for record in records if isinstance(record, dict) and record.get("case_id")}


def _availability_score(record: dict[str, object]) -> int:
    runtime = record.get("runtime_payload", {}) if isinstance(record.get("runtime_payload"), dict) else {}
    workspace = record.get("workspace_index_summary", {}) if isinstance(record.get("workspace_index_summary"), dict) else {}
    operator = record.get("operator_summary", {}) if isinstance(record.get("operator_summary"), dict) else {}
    score = sum(1 for value in runtime.values() if isinstance(value, dict) and value.get("state") == "available")
    score += 2 if workspace.get("state") == "available" else 0
    score += 2 if operator.get("readability") == "clear" else 0
    return score


def _instrumentation_closure(case_results: list[dict[str, object]]) -> dict[str, object]:
    total = len(case_results)
    if total == 0:
        return {"status": "still_blocking", "comparable_case_count": 0, "blocked_case_count": 0, "reason": "no_cases"}
    blocked = [item for item in case_results if item.get("instrumentation_blocking")]
    if not blocked:
        status = "closed"
    elif len(blocked) < total:
        status = "partially_closed"
    else:
        status = "still_blocking"
    return {
        "status": status,
        "comparable_case_count": total - len(blocked),
        "blocked_case_count": len(blocked),
        "blocked_case_ids": [item.get("case_id") for item in blocked],
        "reason": "required_runtime_fields_available" if status == "closed" else "some_required_runtime_or_workspace_fields_unavailable",
    }


def build_authoritative_comparative_report(
    case_pack: dict[str, object],
    native_records: dict[str, object],
    opencode_records: dict[str, object],
) -> dict[str, object]:
    """Build a normalized authoritative report with explicit instrumentation closure."""
    native_normalized = normalize_run_records(native_records, case_pack)
    opencode_normalized = normalize_run_records(opencode_records, case_pack)
    native_by_case = _normalized_by_case(native_normalized)
    opencode_by_case = _normalized_by_case(opencode_normalized)
    cases = case_pack.get("cases", []) if isinstance(case_pack.get("cases"), list) else []
    case_results: list[dict[str, object]] = []
    for case in cases:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id"))
        native = native_by_case.get(case_id, {})
        opencode = opencode_by_case.get(case_id, {})
        native_status = native.get("status") or "blocked"
        opencode_status = opencode.get("status") or "blocked"
        native_auth = native.get("authoritative_execution", {}) if isinstance(native.get("authoritative_execution"), dict) else {}
        opencode_auth = opencode.get("authoritative_execution", {}) if isinstance(opencode.get("authoritative_execution"), dict) else {}
        instrumentation_blocking = bool(opencode_auth.get("blocks_capability_comparison"))
        gap_classification: list[str] = []
        opencode_product_or_ecosystem_failure = _is_product_or_ecosystem_failure(opencode)
        if native_status != opencode_status and not instrumentation_blocking and not opencode_product_or_ecosystem_failure:
            gap_classification.append("agent_capability_gap")
        if instrumentation_blocking:
            gap_classification.append("instrumentation_gap")
        gap_classification.extend(["product_thickness_gap", "ecosystem_gap"])
        case_results.append({
            "case_id": case_id,
            "task_family": case.get("task_family"),
            "native_status": native_status,
            "opencode_status": opencode_status,
            "verify_or_stop_consistent": bool(case.get("verify_command") or case.get("stop_condition")),
            "command_execution_evidence": {
                "native": native_auth.get("command_executed"),
                "opencode": opencode_auth.get("command_executed"),
            },
            "workspace_evidence": {
                "native_state": (native.get("workspace_index_summary", {}) or {}).get("state") if isinstance(native.get("workspace_index_summary"), dict) else "missing",
                "opencode_state": (opencode.get("workspace_index_summary", {}) or {}).get("state") if isinstance(opencode.get("workspace_index_summary"), dict) else "missing",
            },
            "instrumentation_blocking": instrumentation_blocking,
            "opencode_product_or_ecosystem_failure": opencode_product_or_ecosystem_failure,
            "recovery_quality_delta": "equivalent" if native_status == opencode_status else "native_better" if native_status == "pass" else "opencode_better",
            "evidence_completeness_delta": "native_better" if _availability_score(native) > _availability_score(opencode) else "opencode_better" if _availability_score(opencode) > _availability_score(native) else "equivalent",
            "operator_readability_delta": "equivalent" if (native.get("operator_summary", {}) or {}).get("readability") == (opencode.get("operator_summary", {}) or {}).get("readability") else "inconclusive",
            "cost_latency_availability_delta": "native_better" if instrumentation_blocking else "equivalent",
            "gap_classification": list(dict.fromkeys(gap_classification)),
            "evidence_pointers": [f"native.normalized[{case_id}]", f"opencode.normalized[{case_id}]", f"case_pack.cases[{case_id}]"],
        })
    instrumentation = _instrumentation_closure(case_results)
    operator_decision = build_authoritative_operator_decision(case_results, instrumentation)
    return {
        "report_version": AUTHORITATIVE_REPORT_VERSION,
        "case_pack_version": case_pack.get("contract_version"),
        "normalized_record_version": NORMALIZED_RECORD_VERSION,
        "native_normalized_records": native_normalized,
        "opencode_normalized_records": opencode_normalized,
        "case_result_count": len(case_results),
        "case_results": case_results,
        "instrumentation_closure": instrumentation,
        "gap_taxonomy": ["agent_capability_gap", "product_thickness_gap", "ecosystem_gap", "instrumentation_gap"],
        "operator_decision": operator_decision,
    }


def build_authoritative_operator_decision(
    case_results: list[dict[str, object]],
    instrumentation_closure: dict[str, object],
) -> dict[str, object]:
    status = instrumentation_closure.get("status")
    gap_counts: dict[str, int] = {}
    for result in case_results:
        gaps = result.get("gap_classification", []) if isinstance(result.get("gap_classification"), list) else []
        for gap in gaps:
            gap_counts[str(gap)] = gap_counts.get(str(gap), 0) + 1
    if status == "still_blocking":
        decision = "instrumentation_still_blocking"
        reason = "All OpenCode cases still lack authoritative required runtime/workspace fields for capability comparison."
        next_moves = ["wire real OpenCode CLI invocation", "persist stdout/stderr artifacts", "capture workspace before/after summaries"]
        non_moves = ["do not claim agent capability gap while instrumentation blocks comparison"]
    elif status == "partially_closed":
        decision = "instrumentation_partially_closed_mixed_strategy"
        reason = "Some task families are comparable, but others still have instrumentation blockers."
        next_moves = ["compare only closed cases", "repair blocked family instrumentation", "rerun authoritative report"]
        non_moves = ["do not average closed and blocked task families into one capability verdict"]
    elif gap_counts.get("agent_capability_gap", 0) > 0:
        decision = "instrumentation_closed_continue_opencode_ecosystem_chase"
        reason = "Instrumentation is closed and same-contract status deltas show real capability differences."
        next_moves = ["inspect failing case transcripts", "prioritize capability repair", "keep same-contract regression"]
        non_moves = ["do not relabel execution failures as product-thickness gaps"]
    else:
        decision = "instrumentation_closed_native_productization_next"
        reason = "Instrumentation is closed; execution is comparable, so remaining gaps are product thickness or ecosystem scale."
        next_moves = ["advance native operator UX", "prioritize TUI/provider/install release", "keep authoritative comparison regression"]
        non_moves = ["do not continue expanding harness schema without a productization need"]
    return {
        "decision": decision,
        "recommended_path": decision,
        "reason": reason,
        "gap_counts": gap_counts,
        "next_moves": next_moves[:3],
        "non_moves": non_moves,
        "instrumentation_closure_status": status,
    }

def build_external_opencode_harness_bundle() -> dict[str, object]:
    case_pack = build_same_contract_case_pack()
    native_records = build_native_run_records(case_pack)
    opencode_records = build_opencode_run_records(case_pack)
    comparative_report = build_comparative_evidence_report(case_pack, native_records, opencode_records)
    authoritative_report = build_authoritative_comparative_report(case_pack, native_records, opencode_records)
    return {
        "bundle_version": "external_opencode_harness_bundle.v1",
        "case_pack": case_pack,
        "native_run_records": native_records,
        "opencode_run_records": opencode_records,
        "comparative_evidence_report": comparative_report,
        "authoritative_comparative_report": authoritative_report,
        "native_normalized_records": authoritative_report["native_normalized_records"],
        "opencode_normalized_records": authoritative_report["opencode_normalized_records"],
        "instrumentation_closure": authoritative_report["instrumentation_closure"],
        "operator_decision": authoritative_report["operator_decision"],
    }
