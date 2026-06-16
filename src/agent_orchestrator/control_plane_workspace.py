"""Workspace state and index models for the control plane."""
from __future__ import annotations

# DEPS: __future__, agent_orchestrator, dataclasses, pathlib
# RESPONSIBILITY: Model workspace state snapshots and persist workspace index artifact references.
# MODULE: decision_core
# ---

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from agent_orchestrator.control_plane_artifacts import artifact_ref as _artifact_ref
from agent_orchestrator.control_plane_artifacts import atomic_write_json as _atomic_write_json
from agent_orchestrator.control_plane_artifacts import read_json_object as _read_json_object
from agent_orchestrator.control_plane_constants import CONTROL_PLANE_FORMATS
from agent_orchestrator.control_plane_posture import (
    derive_planner_closure_posture_summary,
    derive_session_continuity_outline_summary,
    derive_session_planner_decision_summary,
)
from agent_orchestrator.execution.models import (
    derive_adapter_capability_summary,
    derive_adapter_productization_surface,
)
from agent_orchestrator.jobs import now_iso
from agent_orchestrator.productization_surface import (
    build_comparative_adapter_summary,
    build_comparative_completion_summary,
    build_comparative_daily_driver_summary,
    build_comparative_native_closure_summary,
    build_comparative_native_tool_summary,
    build_comparative_planner_candidate_summary,
    build_comparative_planner_autonomy_summary,
    build_comparative_session_continuity_summary,
    build_comparative_session_posture_summary,
    build_runtime_comparative_benchmark_digest,
    build_comparative_daily_driver_benchmark,
    build_runtime_comparative_benchmark_summary,
    build_shared_productization_surface,
    derive_approval_boundary_digest,
    derive_clarify_boundary_digest,
    derive_operator_planner_digest,
    derive_operator_tool_digest,
    derive_native_tool_productization_surface,
)
from agent_orchestrator.session.productization import derive_session_productization_surface


@dataclass(frozen=True, slots=True)
class WorkspaceStateSnapshot:
    project_root: str
    plans: list[dict[str, object]]
    runs: list[dict[str, object]]
    jobs: list[dict[str, object]]
    evidence: dict[str, object]
    approvals: list[dict[str, object]]
    provider_health: dict[str, object] | None
    dirty_state: dict[str, object]
    memory_digest: dict[str, object]
    external_cache: dict[str, object]
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, object]:
        return {
            "format": CONTROL_PLANE_FORMATS["workspace_state"],
            "project_root": self.project_root,
            "plans": list(self.plans),
            "runs": list(self.runs),
            "jobs": list(self.jobs),
            "evidence": dict(self.evidence),
            "approvals": list(self.approvals),
            "provider_health": self.provider_health,
            "dirty_state": dict(self.dirty_state),
            "memory_digest": dict(self.memory_digest),
            "external_cache": dict(self.external_cache),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "WorkspaceStateSnapshot":
        return cls(
            project_root=str(data.get("project_root") or ""),
            plans=[dict(item) for item in data.get("plans", []) if isinstance(item, dict)],
            runs=[dict(item) for item in data.get("runs", []) if isinstance(item, dict)],
            jobs=[dict(item) for item in data.get("jobs", []) if isinstance(item, dict)],
            evidence=dict(data.get("evidence", {})) if isinstance(data.get("evidence"), dict) else {},
            approvals=[dict(item) for item in data.get("approvals", []) if isinstance(item, dict)],
            provider_health=dict(data.get("provider_health", {})) if isinstance(data.get("provider_health"), dict) else None,
            dirty_state=dict(data.get("dirty_state", {})) if isinstance(data.get("dirty_state"), dict) else {},
            memory_digest=dict(data.get("memory_digest", {})) if isinstance(data.get("memory_digest"), dict) else {},
            external_cache=dict(data.get("external_cache", {})) if isinstance(data.get("external_cache"), dict) else {},
            created_at=str(data.get("created_at") or now_iso()),
        )


@dataclass(slots=True)
class WorkspaceIndexStore:
    root: Path | str = ".agent_orchestrator/workspace"

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self.root / "index.json"

    def write(self, snapshot: WorkspaceStateSnapshot) -> dict[str, object]:
        existing = _read_json_object(self.path)
        artifacts = existing.get("artifacts", {}) if isinstance(existing.get("artifacts"), dict) else {}
        payload = workspace_index_payload(
            snapshot,
            artifacts={
                **artifacts,
                "workspace_state": _artifact_ref(snapshot.to_dict()),
            },
        )
        return _atomic_write_json(self.path, payload)

    def write_index(self, payload: dict[str, object]) -> dict[str, object]:
        return _atomic_write_json(self.path, payload)

    def payload(self) -> dict[str, object] | None:
        payload = _read_json_object(self.path)
        return payload or None

    def record_artifact(self, name: str, payload: dict[str, object]) -> dict[str, object]:
        existing = _read_json_object(self.path)
        artifacts = existing.get("artifacts", {}) if isinstance(existing.get("artifacts"), dict) else {}
        workspace_state = existing.get("workspace_state") if isinstance(existing.get("workspace_state"), dict) else None
        if workspace_state is None and existing.get("format") == CONTROL_PLANE_FORMATS["workspace_state"]:
            workspace_state = existing
        index_payload = {
            "format": CONTROL_PLANE_FORMATS["workspace_index"],
            "workspace_state": workspace_state,
            "artifacts": {
                **artifacts,
                name: _artifact_ref(payload),
            },
            "updated_at": now_iso(),
        }
        if isinstance(workspace_state, dict):
            index_payload.update(
                workspace_index_optional_sections(
                    WorkspaceStateSnapshot.from_dict(workspace_state),
                    artifacts=index_payload["artifacts"],
                )
            )
        return _atomic_write_json(self.path, index_payload)

    def read(self) -> WorkspaceStateSnapshot | None:
        if not self.path.exists():
            return None
        payload = _read_json_object(self.path)
        if not payload:
            return None
        if payload.get("format") == CONTROL_PLANE_FORMATS["workspace_index"]:
            workspace_state = payload.get("workspace_state")
            return WorkspaceStateSnapshot.from_dict(workspace_state) if isinstance(workspace_state, dict) else None
        return WorkspaceStateSnapshot.from_dict(payload) if isinstance(payload, dict) else None


def workspace_index_payload(
    snapshot: WorkspaceStateSnapshot,
    *,
    artifacts: dict[str, object],
) -> dict[str, object]:
    payload = {
        "format": CONTROL_PLANE_FORMATS["workspace_index"],
        "workspace_state": snapshot.to_dict(),
        "artifacts": artifacts,
        "updated_at": now_iso(),
    }
    payload.update(workspace_index_optional_sections(snapshot, artifacts=artifacts))
    return payload


def workspace_index_optional_sections(
    snapshot: WorkspaceStateSnapshot,
    *,
    artifacts: dict[str, object],
) -> dict[str, object]:
    plans = list(snapshot.plans)
    active_plans = [plan for plan in plans if str(plan.get("status")) not in {"completed", "cancelled", "failed"}]
    approvals = list(snapshot.approvals)
    open_approvals = [item for item in approvals if str(item.get("status")) == "pending"]
    recent_runs = list(snapshot.runs)[:10]
    memory_recent = (
        list(snapshot.memory_digest.get("recent", []))
        if isinstance(snapshot.memory_digest.get("recent", []), list)
        else []
    )
    provider_health = snapshot.provider_health or {
        "runtime_mode": "unknown",
        "available": None,
        "status": "not_checked",
        "degraded_reason": None,
    }
    execution_artifact_summary = _execution_artifact_summary(artifacts)
    execution_fact_chain = _execution_fact_chain_summary(execution_artifact_summary)
    operator_planner_digest = derive_operator_planner_digest(
        planner_decision=(
            execution_artifact_summary.get("planner_decision", {})
            if isinstance(execution_artifact_summary.get("planner_decision"), dict)
            else {}
        ),
        planner_closure_posture=(
            execution_artifact_summary.get("planner_closure_posture", {})
            if isinstance(execution_artifact_summary.get("planner_closure_posture"), dict)
            else {}
        ),
        continuity_outline=(
            execution_artifact_summary.get("continuity_outline", {})
            if isinstance(execution_artifact_summary.get("continuity_outline"), dict)
            else {}
        ),
    )
    comparative_session_posture_summary = build_comparative_session_posture_summary(
        session_productization_surface=(
            execution_artifact_summary.get("session_continuity", {})
            .get("session_productization_surface", {})
            if isinstance(execution_artifact_summary.get("session_continuity"), dict)
            and isinstance(
                execution_artifact_summary.get("session_continuity", {}).get(
                    "session_productization_surface"
                ),
                dict,
            )
            else {}
        ),
        planner_decision=(
            execution_artifact_summary.get("planner_decision", {})
            if isinstance(execution_artifact_summary.get("planner_decision"), dict)
            else {}
        ),
        continuity_outline=(
            execution_artifact_summary.get("continuity_outline", {})
            if isinstance(execution_artifact_summary.get("continuity_outline"), dict)
            else {}
        ),
    )
    planner_shared_contract = (
        execution_artifact_summary.get("planner_shared_contract", {})
        if isinstance(execution_artifact_summary.get("planner_shared_contract"), dict)
        else {}
    )
    clarify_boundary_digest = derive_clarify_boundary_digest(
        operator_planner_digest=operator_planner_digest,
        comparative_session_posture_summary=comparative_session_posture_summary,
        execution_fact_chain=execution_fact_chain,
        shared_evidence_surface=[
            "workspace_index.execution_fact_chain",
            "ui.operator_summary.execution_fact_chain",
            "cli.workspace_state.execution_fact_chain",
            "comparative_benchmark",
        ],
    )
    approval_boundary_digest = derive_approval_boundary_digest(
        operator_planner_digest=operator_planner_digest,
        comparative_session_posture_summary=comparative_session_posture_summary,
        execution_fact_chain=execution_fact_chain,
        shared_evidence_surface=[
            "workspace_index.execution_fact_chain",
            "ui.operator_summary.execution_fact_chain",
            "cli.workspace_state.execution_fact_chain",
            "comparative_benchmark",
        ],
    )
    comparative_benchmark = (
        execution_artifact_summary.get("comparative_benchmark", {})
        if isinstance(execution_artifact_summary.get("comparative_benchmark"), dict)
        else _comparative_benchmark_summary(execution_artifact_summary)
    )
    if clarify_boundary_digest and not comparative_benchmark.get("clarify_boundary_digest"):
        comparative_benchmark["clarify_boundary_digest"] = dict(clarify_boundary_digest)
    if approval_boundary_digest and not comparative_benchmark.get("approval_boundary_digest"):
        comparative_benchmark["approval_boundary_digest"] = dict(approval_boundary_digest)
    if "daily_driver_main_path_ready" not in comparative_benchmark:
        comparative_benchmark["daily_driver_main_path_ready"] = False
    comparative_benchmark_digest = _comparative_benchmark_digest(comparative_benchmark)
    execution_comparative_digest = (
        execution_artifact_summary.get("comparative_benchmark_digest", {})
        if isinstance(execution_artifact_summary.get("comparative_benchmark_digest"), dict)
        else {}
    )
    if _has_comparative_digest_signal(execution_comparative_digest):
        comparative_benchmark_digest = execution_comparative_digest
    proof_strength = (
        comparative_benchmark.get("comparison_proof_strength", {})
        if isinstance(comparative_benchmark.get("comparison_proof_strength"), dict)
        else {}
    )
    planner_shared_contract_summary = (
        execution_artifact_summary.get("planner_shared_contract_summary", {})
        if isinstance(execution_artifact_summary.get("planner_shared_contract_summary"), dict)
        else {}
    )
    comparative_planner_autonomy_summary = (
        comparative_benchmark.get("comparative_planner_autonomy_summary", {})
        if isinstance(comparative_benchmark.get("comparative_planner_autonomy_summary"), dict)
        else {}
    )
    if (
        not comparative_planner_autonomy_summary
        or comparative_planner_autonomy_summary.get("native_first") is None
    ):
        comparative_planner_autonomy_summary = build_comparative_planner_autonomy_summary(
            planner_shared_contract=planner_shared_contract_summary or planner_shared_contract,
            operator_planner_digest=operator_planner_digest,
            comparative_shared_evidence_surface=(
                comparative_benchmark.get("shared_evidence_surface", [])
                if isinstance(comparative_benchmark.get("shared_evidence_surface"), list)
                else []
            ),
        )
    comparative_planner_candidate_summary = (
        comparative_benchmark.get("comparative_planner_candidate_summary", {})
        if isinstance(comparative_benchmark.get("comparative_planner_candidate_summary"), dict)
        else {}
    )
    if not comparative_planner_candidate_summary:
        comparative_planner_candidate_summary = build_comparative_planner_candidate_summary(
            planner_shared_contract=planner_shared_contract_summary or planner_shared_contract,
            operator_planner_digest=operator_planner_digest,
            comparative_shared_evidence_surface=(
                comparative_benchmark.get("shared_evidence_surface", [])
                if isinstance(comparative_benchmark.get("shared_evidence_surface"), list)
                else []
            ),
        )
    comparative_session_continuity_summary = (
        comparative_benchmark.get("comparative_session_continuity_summary", {})
        if isinstance(comparative_benchmark.get("comparative_session_continuity_summary"), dict)
        else {}
    )
    if not comparative_session_continuity_summary:
        comparative_session_continuity_summary = build_comparative_session_continuity_summary(
            session_productization_surface=(
                execution_artifact_summary.get("session_continuity", {}).get("session_productization_surface", {})
                if isinstance(execution_artifact_summary.get("session_continuity"), dict)
                and isinstance(
                    execution_artifact_summary.get("session_continuity", {}).get("session_productization_surface"),
                    dict,
                )
                else {}
            ),
            continuity_outline=(
                execution_artifact_summary.get("continuity_outline", {})
                if isinstance(execution_artifact_summary.get("continuity_outline"), dict)
                else {}
            ),
            comparative_shared_evidence_surface=(
                comparative_benchmark.get("shared_evidence_surface", [])
                if isinstance(comparative_benchmark.get("shared_evidence_surface"), list)
                else []
            ),
        )
    comparative_native_closure_summary = (
        comparative_benchmark.get("comparative_native_closure_summary", {})
        if isinstance(comparative_benchmark.get("comparative_native_closure_summary"), dict)
        else {}
    )
    if not comparative_native_closure_summary:
        comparative_native_closure_summary = build_comparative_native_closure_summary(
            native_task_proof=(
                execution_artifact_summary.get("native_task_proof", {})
                if isinstance(execution_artifact_summary.get("native_task_proof"), dict)
                else {}
            ),
            verification=(
                execution_artifact_summary.get("session_continuity", {}).get("milestone_verification", {})
                if isinstance(execution_artifact_summary.get("session_continuity"), dict)
                and isinstance(
                    execution_artifact_summary.get("session_continuity", {}).get("milestone_verification"),
                    dict,
                )
                else {}
            ),
            recovery_summary=(
                execution_artifact_summary.get("session_continuity", {}).get("recovery_summary", {})
                if isinstance(execution_artifact_summary.get("session_continuity"), dict)
                and isinstance(execution_artifact_summary.get("session_continuity", {}).get("recovery_summary"), dict)
                else {}
            ),
            comparative_shared_evidence_surface=(
                comparative_benchmark.get("shared_evidence_surface", [])
                if isinstance(comparative_benchmark.get("shared_evidence_surface"), list)
                else []
            ),
        )
    return {
        "program": {
            "kind": "workspace_program",
            "name": Path(snapshot.project_root).name or "workspace",
            "project_root": snapshot.project_root,
            "active_plan_count": len(active_plans),
            "open_approval_count": len(open_approvals),
            "recent_run_count": len(recent_runs),
        },
        "active_artifacts": {
            "workspace_state": artifacts.get("workspace_state"),
            "context_packet": artifacts.get("context_packet"),
            "strategy_decision": artifacts.get("strategy_decision"),
            "topology_snapshot": artifacts.get("topology_snapshot"),
            "approval_queue": artifacts.get("approval_queue"),
            "run_ledger": artifacts.get("run_ledger"),
            "recovery_timeline": artifacts.get("recovery_timeline"),
            "runtime_event_stream": artifacts.get("runtime_event_stream"),
            "provider_session_snapshot": artifacts.get("provider_session_snapshot"),
            "recovery_recommendation": artifacts.get("recovery_recommendation"),
            "evidence_bundle": artifacts.get("evidence_bundle"),
        },
        "recent_artifacts": [
            {"name": name, "ref": ref}
            for name, ref in sorted(artifacts.items())
            if isinstance(name, str)
        ][-10:],
        "open_approvals": open_approvals,
        "recent_runs": recent_runs,
        "execution_artifact_summary": execution_artifact_summary,
        "execution_fact_chain": execution_fact_chain,
        "clarify_boundary_digest": clarify_boundary_digest,
        "approval_boundary_digest": approval_boundary_digest,
        "comparative_benchmark": comparative_benchmark,
        "comparative_benchmark_digest": comparative_benchmark_digest,
        "comparative_planner_closure_summary": _comparative_planner_closure_summary(comparative_benchmark_digest),
        "comparative_planner_autonomy_summary": comparative_planner_autonomy_summary,
        "comparative_planner_candidate_summary": comparative_planner_candidate_summary,
        "comparative_session_continuity_summary": comparative_session_continuity_summary,
        "comparative_native_closure_summary": comparative_native_closure_summary,
        "comparative_native_tool_summary": build_comparative_native_tool_summary(
            native_tool_productization_surface=(
                execution_artifact_summary.get("native_tool_productization_surface", {})
                if isinstance(execution_artifact_summary.get("native_tool_productization_surface"), dict)
                else {}
            ),
            native_tool_workflow_surface=(
                execution_artifact_summary.get("native_tool_workflow_surface", {})
                if isinstance(execution_artifact_summary.get("native_tool_workflow_surface"), dict)
                else {}
            ),
        ),
        "operator_tool_digest": derive_operator_tool_digest(
            native_tool_productization_surface=(
                execution_artifact_summary.get("native_tool_productization_surface", {})
                if isinstance(execution_artifact_summary.get("native_tool_productization_surface"), dict)
                else {}
            ),
            native_tool_workflow_surface=(
                execution_artifact_summary.get("native_tool_workflow_surface", {})
                if isinstance(execution_artifact_summary.get("native_tool_workflow_surface"), dict)
                else {}
            ),
        ),
        "operator_planner_digest": operator_planner_digest,
        "comparative_adapter_summary": build_comparative_adapter_summary(
            adapter_productization_surface=(
                execution_artifact_summary.get("adapter_productization_surface", {})
                if isinstance(execution_artifact_summary.get("adapter_productization_surface"), dict)
                else {}
            ),
            adapter_shared_contract=(
                execution_artifact_summary.get("adapter_shared_contract", {})
                if isinstance(execution_artifact_summary.get("adapter_shared_contract"), dict)
                else {}
            ),
            adapter_capability_surface=(
                execution_artifact_summary.get("adapter_capability_surface", {})
                if isinstance(execution_artifact_summary.get("adapter_capability_surface"), dict)
                else execution_artifact_summary.get("adapter_capability", {})
                if isinstance(execution_artifact_summary.get("adapter_capability"), dict)
                else {}
            ),
        ),
        "comparative_session_posture_summary": comparative_session_posture_summary,
        "operator_posture_digest": _operator_posture_digest(
            execution_artifact_summary.get("session_continuity", {}).get("session_productization_surface", {})
            if isinstance(execution_artifact_summary.get("session_continuity"), dict)
            else {}
        ),
        "comparative_daily_driver_summary": build_comparative_daily_driver_summary(
            proof_strength=(
                comparative_benchmark.get("comparison_proof_strength", {})
                if isinstance(comparative_benchmark.get("comparison_proof_strength"), dict)
                else {}
            ),
            benchmark_digest=comparative_benchmark_digest,
            comparative_benchmark=comparative_benchmark,
        ),
        "comparative_completion_summary": build_comparative_completion_summary(
            benchmark_digest=comparative_benchmark_digest,
            comparative_benchmark=comparative_benchmark,
        ),
        "comparative_daily_driver_benchmark": (
            build_comparative_daily_driver_benchmark(
                comparative_benchmark.get("comparison_proof_strength", {})
                if isinstance(comparative_benchmark.get("comparison_proof_strength"), dict)
                else {}
            )
            or _comparative_daily_driver_benchmark_from_digest(comparative_benchmark_digest)
        ),
        "memory_candidates": [
            {
                "record_type": record.get("record_type"),
                "namespace": record.get("namespace"),
                "summary": record.get("summary"),
                "provenance": record.get("provenance", {}),
                "source": "memory_digest",
            }
            for record in memory_recent
            if isinstance(record, dict)
        ],
        "provider_runtime_health": provider_health,
    }


def _execution_artifact_summary(artifacts: dict[str, object]) -> dict[str, object]:
    runtime_event_stream = artifacts.get("runtime_event_stream", {}) if isinstance(artifacts.get("runtime_event_stream"), dict) else {}
    summary = runtime_event_stream.get("summary", {}) if isinstance(runtime_event_stream.get("summary"), dict) else {}
    execution_artifacts = artifacts.get("execution_artifacts", {}) if isinstance(artifacts.get("execution_artifacts"), dict) else {}
    execution_artifact_summary = (
        execution_artifacts.get("summary", {})
        if isinstance(execution_artifacts.get("summary"), dict)
        else {}
    )
    compressed_context = (
        execution_artifact_summary.get("compressed_context", {})
        if isinstance(execution_artifact_summary.get("compressed_context"), dict)
        else {}
    )
    context_engineering_contract = (
        execution_artifact_summary.get("context_engineering_contract", {})
        if isinstance(execution_artifact_summary.get("context_engineering_contract"), dict)
        else {}
    )
    isolate_contract = (
        context_engineering_contract.get("isolate", {})
        if isinstance(context_engineering_contract.get("isolate"), dict)
        else {}
    )
    step_loop_contract = (
        execution_artifact_summary.get("step_loop_contract", {})
        if isinstance(execution_artifact_summary.get("step_loop_contract"), dict)
        else {}
    )
    native_tool_surface = (
        execution_artifact_summary.get("native_tool_surface", {})
        if isinstance(execution_artifact_summary.get("native_tool_surface"), dict)
        else {}
    )
    native_tool_trace = (
        execution_artifact_summary.get("native_tool_trace", {})
        if isinstance(execution_artifact_summary.get("native_tool_trace"), dict)
        else {}
    )
    native_task_proof = (
        execution_artifact_summary.get("native_task_proof", {})
        if isinstance(execution_artifact_summary.get("native_task_proof"), dict)
        else {}
    )
    native_repo_task_acceptance = (
        execution_artifact_summary.get("native_repo_task_acceptance", {})
        if isinstance(execution_artifact_summary.get("native_repo_task_acceptance"), dict)
        else {}
    )
    native_complex_repo_task_acceptance = (
        execution_artifact_summary.get("native_complex_repo_task_acceptance", {})
        if isinstance(execution_artifact_summary.get("native_complex_repo_task_acceptance"), dict)
        else {}
    )
    planner_shared_contract = (
        execution_artifact_summary.get("planner_shared_contract", {})
        if isinstance(execution_artifact_summary.get("planner_shared_contract"), dict)
        else {}
    )
    adapter_shared_contract = (
        execution_artifact_summary.get("adapter_shared_contract", {})
        if isinstance(execution_artifact_summary.get("adapter_shared_contract"), dict)
        else {}
    )
    adapter_contract = (
        execution_artifact_summary.get("adapter_contract", {})
        if isinstance(execution_artifact_summary.get("adapter_contract"), dict)
        else {}
    )
    adapter_capability_surface = (
        execution_artifact_summary.get("adapter_capability_surface", {})
        if isinstance(execution_artifact_summary.get("adapter_capability_surface"), dict)
        else {}
    )
    if not adapter_capability_surface:
        adapter_capability_surface = (
            adapter_contract.get("capability_surface", {})
            if isinstance(adapter_contract.get("capability_surface"), dict)
            else {}
        )
    normalized_adapter_capability = (
        derive_adapter_capability_summary(
            adapter_contract=adapter_contract,
            adapter_capability_surface=adapter_capability_surface,
        )
        or (
            execution_artifact_summary.get("adapter_capability", {})
            if isinstance(execution_artifact_summary.get("adapter_capability"), dict)
            else {}
        )
    )
    if isinstance(normalized_adapter_capability, dict) and normalized_adapter_capability.get("shared_evidence_surface"):
        adapter_capability_surface = {
            **adapter_capability_surface,
            "shared_evidence_surface": normalized_adapter_capability.get("shared_evidence_surface", []),
        }
    if adapter_contract and isinstance(adapter_contract, dict):
        shared_contract = (
            adapter_contract.get("capability_surface", {}).get("shared_contract", {})
            if isinstance(adapter_contract.get("capability_surface"), dict)
            and isinstance(adapter_contract.get("capability_surface", {}).get("shared_contract"), dict)
            else {}
        )
        adapter_shared_contract = {
            **adapter_shared_contract,
            "continuity_support": (
                dict(shared_contract.get("continuity_support", {}))
                if isinstance(shared_contract.get("continuity_support"), dict)
                else adapter_shared_contract.get("continuity_support", {})
            ),
            "shared_evidence_surface": (
                list(shared_contract.get("shared_evidence_surface", []))
                if isinstance(shared_contract.get("shared_evidence_surface"), list)
                and shared_contract.get("shared_evidence_surface")
                else adapter_shared_contract.get("shared_evidence_surface", [])
            ),
            "operator_visibility_contract": (
                dict(shared_contract.get("operator_visibility_contract", {}))
                if isinstance(shared_contract.get("operator_visibility_contract"), dict)
                and shared_contract.get("operator_visibility_contract")
                else adapter_shared_contract.get("operator_visibility_contract", {})
            ),
            "tooling_contract": (
                dict(shared_contract.get("tooling_contract", {}))
                if isinstance(shared_contract.get("tooling_contract"), dict)
                and shared_contract.get("tooling_contract")
                else adapter_shared_contract.get("tooling_contract", {})
            ),
        }
    continuity_contract = (
        execution_artifact_summary.get("session_continuity_contract", {})
        if isinstance(execution_artifact_summary.get("session_continuity_contract"), dict)
        else {}
    )
    resume_contract = (
        execution_artifact_summary.get("resume_contract", {})
        if isinstance(execution_artifact_summary.get("resume_contract"), dict)
        else {}
    )
    comparative_benchmark = (
        execution_artifact_summary.get("comparative_benchmark", {})
        if isinstance(execution_artifact_summary.get("comparative_benchmark"), dict)
        else _comparative_benchmark_summary(execution_artifact_summary)
    )
    comparative_benchmark_digest = (
        execution_artifact_summary.get("comparative_benchmark_digest", {})
        if isinstance(execution_artifact_summary.get("comparative_benchmark_digest"), dict)
        and _has_comparative_digest_signal(execution_artifact_summary.get("comparative_benchmark_digest", {}))
        else _comparative_benchmark_digest(comparative_benchmark)
    )
    comparative_daily_driver_readiness = (
        comparative_benchmark.get("daily_driver_readiness", {})
        if isinstance(comparative_benchmark.get("daily_driver_readiness"), dict)
        else {}
    )
    productization_surface = _session_productization_surface(
        {
            **continuity_contract,
            "comparative_benchmark_digest": comparative_benchmark_digest,
        }
    )
    program_continuity = (
        continuity_contract.get("program_continuity", {})
        if isinstance(continuity_contract.get("program_continuity"), dict)
        else {}
    )
    resume_context = (
        execution_artifact_summary.get("resume_context", {})
        if isinstance(execution_artifact_summary.get("resume_context"), dict)
        else {}
    )
    repo_report = (
        execution_artifact_summary.get("repo_report", {})
        if isinstance(execution_artifact_summary.get("repo_report"), dict)
        else {}
    )
    step_context_refs = (
        step_loop_contract.get("context_engineering_refs", {})
        if isinstance(step_loop_contract.get("context_engineering_refs"), dict)
        else {}
    )
    recent_execution_artifacts = [
        {"name": name, "ref": ref}
        for name, ref in sorted(artifacts.items())
        if isinstance(name, str) and "artifact" in name
    ]
    compressed_history = (
        compressed_context.get("summarized_history", {})
        if isinstance(compressed_context.get("summarized_history"), dict)
        else {}
    )
    tool_trace_entries = (
        native_tool_trace.get("trace", [])
        if isinstance(native_tool_trace.get("trace"), list)
        else []
    )
    planner_decision = (
        execution_artifact_summary.get("planner_decision", {})
        if isinstance(execution_artifact_summary.get("planner_decision"), dict)
        else {}
    )
    continuity_outline = (
        execution_artifact_summary.get("continuity_outline", {})
        if isinstance(execution_artifact_summary.get("continuity_outline"), dict)
        else {}
    )
    tool_productization_surface = _native_tool_productization_surface(
        native_tool_surface=native_tool_surface,
        native_tool_trace=native_tool_trace,
        execution_artifact_summary=execution_artifact_summary,
    )
    adapter_productization_surface = _adapter_productization_surface(
        execution_artifact_summary=execution_artifact_summary,
        adapter_shared_contract=adapter_shared_contract,
    )
    shared_productization_surface = build_shared_productization_surface(
        session_productization_surface=productization_surface,
        native_tool_productization_surface=tool_productization_surface,
        native_tool_workflow_surface=(
            execution_artifact_summary.get("native_tool_workflow_surface", {})
            if isinstance(execution_artifact_summary.get("native_tool_workflow_surface"), dict)
            else (
                native_tool_surface.get("workflow_surface", {})
                if isinstance(native_tool_surface.get("workflow_surface"), dict)
                else {}
            )
        ),
        adapter_productization_surface=adapter_productization_surface,
        planner_decision=planner_decision
        or _derived_session_planner_decision(
            execution_artifact_summary=execution_artifact_summary,
            adapter_shared_contract=adapter_shared_contract,
        )
        or {},
        continuity_outline=continuity_outline
        or _derived_session_continuity_outline(
            execution_artifact_summary=execution_artifact_summary,
        )
        or {},
        planner_closure_posture=(
            execution_artifact_summary.get("planner_closure_posture", {})
            if isinstance(execution_artifact_summary.get("planner_closure_posture"), dict)
            else derive_planner_closure_posture_summary(
                planner_decision=(
                    planner_decision
                    or _derived_session_planner_decision(
                        execution_artifact_summary=execution_artifact_summary,
                        adapter_shared_contract=adapter_shared_contract,
                    )
                    or {}
                ),
                continuity=(
                    continuity_outline
                    or _derived_session_continuity_outline(
                        execution_artifact_summary=execution_artifact_summary,
                    )
                    or {}
                ),
            )
        ),
        runtime_cost=(
            execution_artifact_summary.get("runtime_cost", {})
            if isinstance(execution_artifact_summary.get("runtime_cost"), dict)
            else {}
        ),
        native_tool_usage=(
            execution_artifact_summary.get("native_tool_usage", {})
            if isinstance(execution_artifact_summary.get("native_tool_usage"), dict)
            else {}
        ),
        adapter_capability_surface=(
            execution_artifact_summary.get("adapter_capability_surface", {})
            if isinstance(execution_artifact_summary.get("adapter_capability_surface"), dict)
            else {}
        ),
            comparative_shared_evidence_surface=[],
        )
    synthesized_session_continuity = {
        "resume_supported": continuity_contract.get("resume_supported", step_loop_contract.get("resume_supported")),
        "resume_kind": continuity_contract.get("resume_kind", resume_context.get("resume_kind")),
        "compaction_stage": continuity_contract.get("compaction_stage", compressed_history.get("compaction_stage")),
        "masked_observation_count": continuity_contract.get("masked_observation_count", compressed_history.get("masked_observation_count")),
        "summarization_triggered": continuity_contract.get("summarization_triggered", compressed_history.get("summarization_triggered")),
        "runtime_duration_seconds": continuity_contract.get("runtime_duration_seconds"),
        "usage_cost_measurement_status": continuity_contract.get("usage_cost_measurement_status"),
        "runtime_cost_provenance": continuity_contract.get("runtime_cost_provenance", {}),
        "shared_evidence_surface": list(continuity_contract.get("shared_evidence_surface", []))
        if isinstance(continuity_contract.get("shared_evidence_surface"), list)
        else [],
        "latest_recovery_hint": continuity_contract.get("latest_recovery_hint", compressed_context.get("latest_recovery_hint")),
        "continuity_pressure": continuity_contract.get("continuity_pressure", {}),
        "long_horizon_posture": continuity_contract.get("long_horizon_posture", {}),
        "program_posture": continuity_contract.get("program_posture", {}),
        "delegation_contract": continuity_contract.get("delegation_contract", {}),
        "program_continuity": continuity_contract.get("program_continuity", {}),
        "daily_driver_readiness": continuity_contract.get("daily_driver_readiness", {}),
        "milestone_verification": continuity_contract.get("milestone_verification", {}),
        "operator_control": continuity_contract.get("operator_control", {}),
        "continuity_snapshot": continuity_contract.get("continuity_snapshot", {}),
        "resume_contract": resume_contract,
        "session_productization_surface": productization_surface,
    }
    synthesized_runtime_cost = {
        "duration_seconds": continuity_contract.get(
            "runtime_duration_seconds",
            _duration_seconds_from_artifacts(recent_execution_artifacts),
        ),
        "usage_cost_measurement_status": continuity_contract.get("usage_cost_measurement_status", "placeholder"),
        "runtime_cost_provenance": continuity_contract.get("runtime_cost_provenance", {}),
        "measurement_policy": "local runtime duration is measured from artifact timestamps when available; provider cost remains placeholder unless reported",
    }
    synthesized_native_tool_usage = {
        "tool_count": len(native_tool_surface.get("tools", [])) if isinstance(native_tool_surface.get("tools"), list) else 0,
        "trace_count": len(tool_trace_entries),
        "recent_tools": [
            item.get("tool")
            for item in tool_trace_entries[-5:]
            if isinstance(item, dict) and item.get("tool")
        ],
    }
    comparative_benchmark_source = {
        **execution_artifact_summary,
        "session_continuity": synthesized_session_continuity,
        "native_tool_productization_surface": tool_productization_surface,
        "adapter_productization_surface": adapter_productization_surface,
        "planner_decision": planner_decision
        or _derived_session_planner_decision(
            execution_artifact_summary=execution_artifact_summary,
            adapter_shared_contract=adapter_shared_contract,
        ),
        "continuity_outline": continuity_outline
        or _derived_session_continuity_outline(
            execution_artifact_summary=execution_artifact_summary,
        ),
        "runtime_cost": synthesized_runtime_cost,
        "native_tool_usage": synthesized_native_tool_usage,
    }
    comparative_benchmark = (
        execution_artifact_summary.get("comparative_benchmark", {})
        if isinstance(execution_artifact_summary.get("comparative_benchmark"), dict)
        else _comparative_benchmark_summary(comparative_benchmark_source)
    )
    comparative_benchmark_digest = (
        execution_artifact_summary.get("comparative_benchmark_digest", {})
        if isinstance(execution_artifact_summary.get("comparative_benchmark_digest"), dict)
        and _has_comparative_digest_signal(execution_artifact_summary.get("comparative_benchmark_digest", {}))
        else _comparative_benchmark_digest(comparative_benchmark)
    )
    comparative_daily_driver_readiness = (
        comparative_benchmark.get("daily_driver_readiness", {})
        if isinstance(comparative_benchmark.get("daily_driver_readiness"), dict)
        else {}
    )
    if not resume_contract:
        operator_continuity = (
            productization_surface.get("operator_continuity", {})
            if isinstance(productization_surface.get("operator_continuity"), dict)
            else {}
        )
        resume_contract = {
            "resume_kind": continuity_contract.get("resume_kind") or operator_continuity.get("resume_expectation"),
            "run_id": execution_artifact_summary.get("run_id"),
            "session_id": execution_artifact_summary.get("session_id"),
            "turn_id": execution_artifact_summary.get("turn_id"),
            "current_stage": continuity_contract.get("program_posture", {}).get("active_milestone")
            if isinstance(continuity_contract.get("program_posture"), dict)
            else None,
            "current_step_id": None,
            "approved_approval_id": None,
            "pending_approval": None,
            "resume_supported": continuity_contract.get("resume_supported"),
            "continuity_snapshot": continuity_contract.get("continuity_snapshot", {}),
            "program_posture": continuity_contract.get("program_posture", {}),
            "native_tool_usage": synthesized_native_tool_usage,
            "operator_posture_digest": productization_surface.get("operator_posture_digest", {}),
            "shared_evidence_surface": continuity_contract.get("shared_evidence_surface", []),
        }
    synthesized_session_continuity["resume_contract"] = resume_contract
    synthesized_session_continuity["daily_driver_readiness"] = (
        comparative_daily_driver_readiness
        or synthesized_session_continuity["daily_driver_readiness"]
    )
    synthesized_session_continuity["comparative_benchmark_digest"] = comparative_benchmark_digest
    synthesized_session_continuity["session_productization_surface"] = {
        **productization_surface,
        "comparative_benchmark_digest": comparative_benchmark_digest,
    }
    planner_closure_posture = derive_planner_closure_posture_summary(
        planner_decision=planner_decision
        or _derived_session_planner_decision(
            execution_artifact_summary=execution_artifact_summary,
            adapter_shared_contract=adapter_shared_contract,
        )
        or {},
        continuity=synthesized_session_continuity,
    )
    return {
        "runtime_event_count": summary.get("event_count", 0),
        "recent_execution_artifacts": recent_execution_artifacts[-10:],
        "compressed_context": compressed_context or None,
        "compacted_context_summary": _compacted_context_summary(compressed_context),
        "context_engineering_contract": context_engineering_contract or None,
        "session_continuity": synthesized_session_continuity,
        "resume_contract": resume_contract or None,
        "runtime_cost": synthesized_runtime_cost,
        "native_tool_surface": native_tool_surface or None,
        "native_tool_workflow_surface": (
            execution_artifact_summary.get("native_tool_workflow_surface", {})
            if isinstance(execution_artifact_summary.get("native_tool_workflow_surface"), dict)
            else (
                native_tool_surface.get("workflow_surface", {})
                if isinstance(native_tool_surface.get("workflow_surface"), dict)
                else {}
            )
        )
        or None,
        "native_tool_productization_surface": tool_productization_surface or None,
        "native_tool_usage": synthesized_native_tool_usage,
        "planner_decision": planner_decision
        or _derived_session_planner_decision(
            execution_artifact_summary=execution_artifact_summary,
            adapter_shared_contract=adapter_shared_contract,
        ),
        "planner_control_surface": (
            planner_decision.get("control_surface", {})
            if isinstance(planner_decision.get("control_surface"), dict)
            else (
                _derived_session_planner_decision(
                    execution_artifact_summary=execution_artifact_summary,
                    adapter_shared_contract=adapter_shared_contract,
                ).get("control_surface", {})
                if isinstance(
                    _derived_session_planner_decision(
                        execution_artifact_summary=execution_artifact_summary,
                        adapter_shared_contract=adapter_shared_contract,
                    ),
                    dict,
                )
                else {}
            )
        ) or None,
        "planner_closure_posture": planner_closure_posture or None,
        "continuity_outline": continuity_outline
        or _derived_session_continuity_outline(
            execution_artifact_summary=execution_artifact_summary,
        ),
        "native_exploration": {
            "workspace_root": repo_report.get("workspace_root"),
            "existing_path_count": len(repo_report.get("existing_paths", [])) if isinstance(repo_report.get("existing_paths"), list) else 0,
            "candidate_path_count": len(repo_report.get("candidate_paths", [])) if isinstance(repo_report.get("candidate_paths"), list) else 0,
            "file_count": repo_report.get("file_count"),
            "exploration_profile": (
                repo_report.get("artifact", {}).get("exploration_profile", {})
                if isinstance(repo_report.get("artifact"), dict) and isinstance(repo_report.get("artifact", {}).get("exploration_profile"), dict)
                else {}
            ),
            "repo_map_directory_count": (
                repo_report.get("artifact", {}).get("repo_map", {}).get("directory_count")
                if isinstance(repo_report.get("artifact"), dict) and isinstance(repo_report.get("artifact", {}).get("repo_map"), dict)
                else None
            ),
            "tool_trace_count": len(repo_report.get("artifact", {}).get("tool_surface", {}).get("tools", []))
            if isinstance(repo_report.get("artifact"), dict)
            and isinstance(repo_report.get("artifact", {}).get("tool_surface"), dict)
            and isinstance(repo_report.get("artifact", {}).get("tool_surface", {}).get("tools"), list)
            else 0,
            "exploration_evidence": (
                repo_report.get("artifact", {}).get("exploration_evidence", {})
                if isinstance(repo_report.get("artifact"), dict) and isinstance(repo_report.get("artifact", {}).get("exploration_evidence"), dict)
                else {}
            ),
        },
        "context_isolation_strategy": isolate_contract.get("strategy"),
        "context_isolation_reinjection_mode": isolate_contract.get("reinjection_mode"),
        "step_loop_context_surfaces": (
            list(step_context_refs.get("required_surfaces", []))
            if isinstance(step_context_refs.get("required_surfaces"), list)
            else []
        ),
        "native_task_proof": native_task_proof or None,
        "native_repo_task_acceptance": native_repo_task_acceptance or None,
        "native_complex_repo_task_acceptance": native_complex_repo_task_acceptance or None,
        "planner_shared_contract": planner_shared_contract or None,
        "planner_shared_contract_summary": _planner_shared_contract_summary(planner_shared_contract),
        "adapter_capability_surface": adapter_capability_surface or None,
        "adapter_capability": normalized_adapter_capability,
        "adapter_shared_contract": adapter_shared_contract or None,
        "adapter_productization_surface": adapter_productization_surface or None,
        "shared_productization_surface": shared_productization_surface,
        "comparative_benchmark": comparative_benchmark or None,
        "comparative_benchmark_digest": comparative_benchmark_digest or None,
        "route_planner_intent": (
            adapter_shared_contract.get("path_selection", {}).get("planner_intent")
            if isinstance(adapter_shared_contract.get("path_selection"), dict)
            else execution_artifact_summary.get("path_selection", {}).get("planner_intent")
            if isinstance(execution_artifact_summary.get("path_selection"), dict)
            else None
        ),
    }


def _derived_session_planner_decision(
    *,
    execution_artifact_summary: dict[str, object],
    adapter_shared_contract: dict[str, object],
) -> dict[str, object] | None:
    planner_shared_contract = (
        execution_artifact_summary.get("planner_shared_contract", {})
        if isinstance(execution_artifact_summary.get("planner_shared_contract"), dict)
        else {}
    )
    if not planner_shared_contract:
        return None
    return derive_session_planner_decision_summary(
        planner_shared={
            **planner_shared_contract,
            "operator_control": (
                {
                    "clarify_pause_state": planner_shared_contract.get("posture", {}).get("route_intent_alignment", {}).get("clarify")
                    if isinstance(planner_shared_contract.get("posture"), dict)
                    and isinstance(planner_shared_contract.get("posture", {}).get("route_intent_alignment"), dict)
                    else None,
                    "approval_pause_state": planner_shared_contract.get("posture", {}).get("route_intent_alignment", {}).get("pause")
                    if isinstance(planner_shared_contract.get("posture"), dict)
                    and isinstance(planner_shared_contract.get("posture", {}).get("route_intent_alignment"), dict)
                    else None,
                }
            ),
            "route_planner_intent": (
                execution_artifact_summary.get("path_selection", {}).get("planner_intent", {})
                if isinstance(execution_artifact_summary.get("path_selection"), dict)
                else {}
            ),
        },
        adapter_shared={
            **adapter_shared_contract,
            "path_selection": {
                "planner_intent": (
                    adapter_shared_contract.get("path_selection", {}).get("planner_intent", {})
                    if isinstance(adapter_shared_contract.get("path_selection"), dict)
                    else execution_artifact_summary.get("path_selection", {}).get("planner_intent", {})
                    if isinstance(execution_artifact_summary.get("path_selection"), dict)
                    else {}
                )
            },
        },
    )


def _derived_session_continuity_outline(
    *,
    execution_artifact_summary: dict[str, object],
) -> dict[str, object] | None:
    session_continuity = (
        execution_artifact_summary.get("session_continuity", {})
        if isinstance(execution_artifact_summary.get("session_continuity"), dict)
        else {}
    )
    program_posture = (
        session_continuity.get("program_posture", {})
        if isinstance(session_continuity.get("program_posture"), dict)
        else {}
    )
    operator_control = (
        session_continuity.get("operator_control", {})
        if isinstance(session_continuity.get("operator_control"), dict)
        else {}
    )
    session_productization_surface = (
        session_continuity.get("session_productization_surface", {})
        if isinstance(session_continuity.get("session_productization_surface"), dict)
        else {}
    )
    long_horizon_posture = (
        session_continuity.get("long_horizon_posture", {})
        if isinstance(session_continuity.get("long_horizon_posture"), dict)
        else {}
    )
    delegation_contract = (
        session_continuity.get("delegation_contract", {})
        if isinstance(session_continuity.get("delegation_contract"), dict)
        else {}
    )
    session_continuity_contract = (
        execution_artifact_summary.get("session_continuity_contract", {})
        if isinstance(execution_artifact_summary.get("session_continuity_contract"), dict)
        else {}
    )
    contract_program_posture = (
        session_continuity_contract.get("program_posture", {})
        if isinstance(session_continuity_contract.get("program_posture"), dict)
        else {}
    )
    contract_operator_control = (
        session_continuity_contract.get("operator_control", {})
        if isinstance(session_continuity_contract.get("operator_control"), dict)
        else {}
    )
    if not session_continuity and not program_posture and not operator_control:
        if not session_continuity_contract and not contract_program_posture and not contract_operator_control:
            return None
    merged_program_posture = program_posture or contract_program_posture
    merged_operator_control = operator_control or contract_operator_control
    return derive_session_continuity_outline_summary(
        continuity={
            **session_continuity,
            "resume_kind": session_continuity.get("resume_kind", session_continuity_contract.get("resume_kind")),
            "compaction_stage": session_continuity.get("compaction_stage", session_continuity_contract.get("compaction_stage")),
            "program_posture": merged_program_posture,
            "operator_control": merged_operator_control,
            "session_productization_surface": session_productization_surface,
            "long_horizon_posture": long_horizon_posture,
            "delegation_contract": (
                delegation_contract
                if isinstance(delegation_contract, dict)
                else {}
            ),
        },
        planner_family=execution_artifact_summary.get("planner_shared_contract", {}).get("planner_family")
        if isinstance(execution_artifact_summary.get("planner_shared_contract"), dict)
        else None,
    )


def _comparative_benchmark_summary(execution_artifact_summary: dict[str, object]) -> dict[str, object]:
    return build_runtime_comparative_benchmark_summary(execution_artifact_summary)


def _session_productization_surface(continuity_contract: dict[str, object]) -> dict[str, object]:
    return derive_session_productization_surface(continuity_contract)


def _native_tool_productization_surface(
    *,
    native_tool_surface: dict[str, object],
    native_tool_trace: dict[str, object],
    execution_artifact_summary: dict[str, object],
) -> dict[str, object]:
    return derive_native_tool_productization_surface(
        native_tool_surface=native_tool_surface,
        native_tool_trace=native_tool_trace,
        native_tool_productization_surface=execution_artifact_summary.get("native_tool_productization_surface", {})
        if isinstance(execution_artifact_summary.get("native_tool_productization_surface"), dict)
        else {},
    )


def _adapter_productization_surface(
    *,
    execution_artifact_summary: dict[str, object],
    adapter_shared_contract: dict[str, object],
) -> dict[str, object]:
    surface = (
        execution_artifact_summary.get("adapter_productization_surface", {})
        if isinstance(execution_artifact_summary.get("adapter_productization_surface"), dict)
        else {}
    )
    if surface:
        return surface
    return derive_adapter_productization_surface(adapter_shared_contract=adapter_shared_contract)


def _comparative_benchmark_digest(benchmark: dict[str, object]) -> dict[str, object]:
    return build_runtime_comparative_benchmark_digest(benchmark)


def _comparative_planner_closure_summary(benchmark_digest: dict[str, object]) -> dict[str, object]:
    benchmark_digest = benchmark_digest if isinstance(benchmark_digest, dict) else {}
    if not benchmark_digest.get("planner_closure_mode") and not benchmark_digest.get("planner_next_recommended_action"):
        return {}
    return {
        "format": "agent_orchestrator.comparative_planner_closure_summary.v1",
        "closure_mode": benchmark_digest.get("planner_closure_mode"),
        "next_recommended_action": benchmark_digest.get("planner_next_recommended_action"),
        "resume_posture": benchmark_digest.get("planner_resume_posture"),
        "verify_selected": benchmark_digest.get("planner_verify_selected"),
        "verification_status": benchmark_digest.get("planner_verification_status"),
        "summary": (
            f"mode={benchmark_digest.get('planner_closure_mode')} "
            f"next_action={benchmark_digest.get('planner_next_recommended_action')} "
            f"resume_posture={benchmark_digest.get('planner_resume_posture')}"
        ),
    }


def _operator_posture_digest(session_productization_surface: dict[str, object]) -> dict[str, object]:
    session_productization_surface = (
        session_productization_surface if isinstance(session_productization_surface, dict) else {}
    )
    digest = (
        session_productization_surface.get("operator_posture_digest", {})
        if isinstance(session_productization_surface.get("operator_posture_digest"), dict)
        else {}
    )
    return dict(digest) if digest else {}


def _has_comparative_digest_signal(digest: dict[str, object]) -> bool:
    if not isinstance(digest, dict) or not digest:
        return False
    for key in ("external_harness_status", "comparison_status", "comparison_grade_status"):
        if key not in digest:
            continue
        value = digest.get(key)
        if value is None:
            continue
        if isinstance(value, str) and value == "":
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        return True
    return False


def _comparative_daily_driver_benchmark_from_digest(digest: dict[str, object]) -> str | None:
    if not isinstance(digest, dict) or not digest:
        return None
    if digest.get("daily_driver_repeatability_tier") != "multi_family_broad_daily_driver_proven":
        return None
    count = digest.get("independent_daily_driver_repo_task_family_count")
    return (
        "official_catalog=docs/process/evidence-cases.json "
        f"independent_daily_driver_families={count} "
        "status=multi_family_broad_daily_driver_proven"
    )


def _planner_shared_contract_summary(planner_shared_contract: dict[str, object]) -> dict[str, object]:
    if not isinstance(planner_shared_contract, dict) or not planner_shared_contract:
        return {}
    decision_boundary = planner_shared_contract.get("decision_boundary", {})
    posture = planner_shared_contract.get("posture", {})
    autonomy_surface = planner_shared_contract.get("autonomy_surface", {})
    if not isinstance(autonomy_surface, dict) or not autonomy_surface:
        decision_evidence = planner_shared_contract.get("decision_evidence", {})
        if isinstance(decision_evidence, dict):
            autonomy_surface = decision_evidence.get("autonomy_surface", {})
            if not isinstance(autonomy_surface, dict):
                autonomy_surface = {}
    if not autonomy_surface:
        selected_actions = (
            list(planner_shared_contract.get("selected_actions", []))
            if isinstance(planner_shared_contract.get("selected_actions"), list)
            else []
        )
        action_priority = {action: index for index, action in enumerate(selected_actions)}
        route_planner_intent = (
            planner_shared_contract.get("route_planner_intent", {})
            if isinstance(planner_shared_contract.get("route_planner_intent"), dict)
            else {}
        )
        planner_family = str(planner_shared_contract.get("planner_family") or "native")
        autonomy_surface = {
            "format": "agent_orchestrator.native_planner_autonomy_surface.v1"
            if planner_family == "native"
            else "agent_orchestrator.compatibility_planner_autonomy_surface.v1",
            "decision_mode": "native_first_autonomous" if planner_family == "native" else "compatibility_guided",
            "primary_action": selected_actions[0] if selected_actions else None,
            "selected_action_count": len(selected_actions),
            "actions": {
                "explore": {"selected": "explore" in selected_actions, "priority_index": action_priority.get("explore")},
                "clarify": {"selected": "clarify" in selected_actions, "priority_index": action_priority.get("clarify")},
                "edit": {"selected": "edit" in selected_actions, "priority_index": action_priority.get("edit")},
                "verify": {"selected": "verify" in selected_actions, "priority_index": action_priority.get("verify")},
                "pause": {
                    "selected": "approval_pause" in selected_actions or bool(route_planner_intent.get("pause")),
                    "priority_index": action_priority.get("approval_pause"),
                },
                "handoff": {"selected": "handoff_external" in selected_actions, "priority_index": action_priority.get("handoff_external")},
                "fallback": {"selected": "fallback_external" in selected_actions, "priority_index": action_priority.get("fallback_external")},
            },
        }
    delegation_contract = planner_shared_contract.get("delegation_contract", {})
    operator_control = planner_shared_contract.get("operator_control", {})
    tool_workflow_plan = (
        planner_shared_contract.get("tool_workflow_plan", {})
        if isinstance(planner_shared_contract.get("tool_workflow_plan"), dict)
        else {}
    )
    autonomy_boundary = (
        planner_shared_contract.get("autonomy_boundary", {})
        if isinstance(planner_shared_contract.get("autonomy_boundary"), dict)
        else {}
    )
    planner_reasoning = (
        planner_shared_contract.get("planner_reasoning", {})
        if isinstance(planner_shared_contract.get("planner_reasoning"), dict)
        else {}
    )
    derived_primary_action = (
        autonomy_surface.get("primary_action")
        if isinstance(autonomy_surface, dict)
        else None
    )
    if not autonomy_boundary:
        autonomy_boundary = {
            "primary_action": derived_primary_action,
            "requires_clarify": bool(
                isinstance(autonomy_surface.get("actions"), dict)
                and isinstance(autonomy_surface.get("actions", {}).get("clarify"), dict)
                and autonomy_surface.get("actions", {}).get("clarify", {}).get("selected")
            )
            if isinstance(autonomy_surface, dict)
            else False,
            "requires_pause": bool(
                isinstance(autonomy_surface.get("actions"), dict)
                and isinstance(autonomy_surface.get("actions", {}).get("pause"), dict)
                and autonomy_surface.get("actions", {}).get("pause", {}).get("selected")
            )
            if isinstance(autonomy_surface, dict)
            else False,
            "requires_handoff": bool(
                isinstance(autonomy_surface.get("actions"), dict)
                and isinstance(autonomy_surface.get("actions", {}).get("handoff"), dict)
                and autonomy_surface.get("actions", {}).get("handoff", {}).get("selected")
            )
            if isinstance(autonomy_surface, dict)
            else False,
            "requires_fallback": bool(
                isinstance(autonomy_surface.get("actions"), dict)
                and isinstance(autonomy_surface.get("actions", {}).get("fallback"), dict)
                and autonomy_surface.get("actions", {}).get("fallback", {}).get("selected")
            )
            if isinstance(autonomy_surface, dict)
            else False,
            "requires_explore": bool(
                isinstance(autonomy_surface.get("actions"), dict)
                and isinstance(autonomy_surface.get("actions", {}).get("explore"), dict)
                and autonomy_surface.get("actions", {}).get("explore", {}).get("selected")
            )
            if isinstance(autonomy_surface, dict)
            else False,
            "requires_edit": bool(
                isinstance(autonomy_surface.get("actions"), dict)
                and isinstance(autonomy_surface.get("actions", {}).get("edit"), dict)
                and autonomy_surface.get("actions", {}).get("edit", {}).get("selected")
            )
            if isinstance(autonomy_surface, dict)
            else False,
            "requires_verify": bool(
                isinstance(autonomy_surface.get("actions"), dict)
                and isinstance(autonomy_surface.get("actions", {}).get("verify"), dict)
                and autonomy_surface.get("actions", {}).get("verify", {}).get("selected")
            )
            if isinstance(autonomy_surface, dict)
            else False,
            "native_first": str(planner_shared_contract.get("planner_family") or "native") == "native",
        }
    if not planner_reasoning:
        planner_reasoning = {
            "primary_action": autonomy_boundary.get("primary_action"),
            "native_first": autonomy_boundary.get("native_first"),
            "requires_clarify": autonomy_boundary.get("requires_clarify"),
            "requires_pause": autonomy_boundary.get("requires_pause"),
            "requires_handoff": autonomy_boundary.get("requires_handoff"),
            "requires_fallback": autonomy_boundary.get("requires_fallback"),
            "requires_explore": autonomy_boundary.get("requires_explore"),
            "requires_edit": autonomy_boundary.get("requires_edit"),
            "requires_verify": autonomy_boundary.get("requires_verify"),
        }
    if not tool_workflow_plan:
        selected_actions = (
            list(planner_shared_contract.get("selected_actions", []))
            if isinstance(planner_shared_contract.get("selected_actions"), list)
            else []
        )
        workflow_stages: dict[str, object] = {}
        daily_driver_tools: list[str] = []
        for stage_name, required_tools in {
            "explore": ["repo_map", "find_files", "search", "outline", "read"],
            "edit": ["patch_preview", "structured_patch", "diff_preview"],
            "verify": ["verify", "tool_trace"],
        }.items():
            selected = stage_name in selected_actions
            workflow_stages[stage_name] = {
                "selected": selected,
                "required_tools": list(required_tools),
                "projection_required": selected,
            }
            if selected:
                for tool_name in required_tools:
                    if tool_name not in daily_driver_tools:
                        daily_driver_tools.append(tool_name)
        tool_workflow_plan = {
            "format": "agent_orchestrator.native_tool_workflow_plan.v1"
            if str(planner_shared_contract.get("planner_family") or "native") == "native"
            else "agent_orchestrator.compatibility_tool_workflow_plan.v1",
            "planner_family": planner_shared_contract.get("planner_family"),
            "selected_strategy": planner_shared_contract.get("selected_strategy"),
            "workflow_stage_order": [stage for stage in ("explore", "edit", "verify") if stage in selected_actions],
            "workflow_stages": workflow_stages,
            "daily_driver_path": {
                "tools": daily_driver_tools,
                "selected_stage_count": len([item for item in workflow_stages.values() if item.get("selected") is True]),
            },
            "workflow_projection_required": True,
        }
    return {
        "format": planner_shared_contract.get("format"),
        "planner_family": planner_shared_contract.get("planner_family"),
        "selected_strategy": planner_shared_contract.get("selected_strategy"),
        "decision_candidates": list(planner_shared_contract.get("decision_candidates", []))
        if isinstance(planner_shared_contract.get("decision_candidates"), list)
        else [],
        "selected_owner": planner_shared_contract.get("selected_owner"),
        "decision_boundary": {
            "task_type": decision_boundary.get("task_type"),
            "risk_level": decision_boundary.get("risk_level"),
            "route_task_kind": decision_boundary.get("route_task_kind"),
            "requires_human_confirmation": decision_boundary.get("requires_human_confirmation"),
        },
        "route_planner_intent": planner_shared_contract.get("route_planner_intent", {})
        if isinstance(planner_shared_contract.get("route_planner_intent"), dict)
        else {},
        "route_intent_alignment": posture.get("route_intent_alignment", {})
        if isinstance(posture.get("route_intent_alignment"), dict)
        else {},
        "autonomy_boundary": autonomy_boundary,
        "planner_reasoning": planner_reasoning,
        "native_first": (
            planner_reasoning.get("native_first")
            if isinstance(planner_reasoning, dict)
            else autonomy_boundary.get("native_first")
        ),
        "autonomy_surface": {
            "format": autonomy_surface.get("format"),
            "decision_mode": autonomy_surface.get("decision_mode"),
            "primary_action": autonomy_surface.get("primary_action"),
            "selected_action_count": autonomy_surface.get("selected_action_count"),
            "actions": dict(autonomy_surface.get("actions", {}))
            if isinstance(autonomy_surface.get("actions"), dict)
            else {},
        }
        if isinstance(autonomy_surface, dict)
        else {},
        "next_recommended_action": operator_control.get("next_recommended_action"),
        "runbook_recovery_lane": operator_control.get("runbook_recovery_lane"),
        "tool_workflow_plan": tool_workflow_plan,
        "selected_executor": delegation_contract.get("selected_executor"),
        "ownership_boundary": delegation_contract.get("ownership_boundary"),
    }


def _compacted_context_summary(compressed_context: dict[str, object]) -> dict[str, object]:
    if not isinstance(compressed_context, dict) or not compressed_context:
        return {}
    summarized_history = (
        compressed_context.get("summarized_history", {})
        if isinstance(compressed_context.get("summarized_history"), dict)
        else {}
    )
    completed_steps = (
        list(summarized_history.get("completed_steps", []))
        if isinstance(summarized_history.get("completed_steps"), list)
        else []
    )
    pending_steps = (
        list(summarized_history.get("pending_steps", []))
        if isinstance(summarized_history.get("pending_steps"), list)
        else []
    )
    blocked_steps = (
        list(summarized_history.get("blocked_steps", []))
        if isinstance(summarized_history.get("blocked_steps"), list)
        else []
    )
    return {
        "objective": compressed_context.get("objective"),
        "current_status": compressed_context.get("current_status"),
        "latest_recovery_hint": compressed_context.get("latest_recovery_hint"),
        "compaction_stage": summarized_history.get("compaction_stage"),
        "masked_observation_count": summarized_history.get("masked_observation_count"),
        "summarization_triggered": summarized_history.get("summarization_triggered"),
        "observation_count": summarized_history.get("observation_count"),
        "selected_memory_count": summarized_history.get("selected_memory_count"),
        "artifact_count": summarized_history.get("artifact_count"),
        "completed_step_count": len(completed_steps),
        "pending_step_count": len(pending_steps),
        "blocked_step_count": len(blocked_steps),
    }


def _execution_fact_chain_summary(execution_artifact_summary: dict[str, object]) -> dict[str, object]:
    native_task_proof = (
        execution_artifact_summary.get("native_task_proof", {})
        if isinstance(execution_artifact_summary.get("native_task_proof"), dict)
        else {}
    )
    continuity = (
        execution_artifact_summary.get("session_continuity", {})
        if isinstance(execution_artifact_summary.get("session_continuity"), dict)
        else {}
    )
    compressed_context = (
        execution_artifact_summary.get("compressed_context", {})
        if isinstance(execution_artifact_summary.get("compressed_context"), dict)
        else {}
    )
    milestone_verification = (
        continuity.get("milestone_verification", {})
        if isinstance(continuity.get("milestone_verification"), dict)
        else {}
    )
    operator_control = (
        continuity.get("operator_control", {})
        if isinstance(continuity.get("operator_control"), dict)
        else {}
    )
    program_posture = (
        continuity.get("program_posture", {})
        if isinstance(continuity.get("program_posture"), dict)
        else {}
    )
    return {
        "format": "agent_orchestrator.execution_fact_chain.v1",
        "objective": compressed_context.get("objective"),
        "current_status": compressed_context.get("current_status"),
        "active_stage": program_posture.get("active_milestone"),
        "resume_supported": continuity.get("resume_supported"),
        "resume_kind": continuity.get("resume_kind"),
        "latest_recovery_hint": continuity.get("latest_recovery_hint"),
        "next_recommended_action": operator_control.get("next_recommended_action"),
        "recovery_lane": operator_control.get("runbook_recovery_lane"),
        "approval_pause_state": operator_control.get("approval_pause_state"),
        "clarify_pause_state": operator_control.get("clarify_pause_state"),
        "verification_status": milestone_verification.get("verification_status"),
        "checkpoint_ready": milestone_verification.get("checkpoint_ready"),
        "task_class": native_task_proof.get("task_class"),
        "native_coverage_class": compressed_context.get("session_context", {}).get("route", {}).get("native_coverage_class")
        if isinstance(compressed_context.get("session_context"), dict)
        and isinstance(compressed_context.get("session_context", {}).get("route"), dict)
        else None,
        "closure_status": native_task_proof.get("closure_status"),
        "proof_scenario": native_task_proof.get("proof_scenario"),
        "shared_surface_refs": [
            "workspace_index.execution_fact_chain",
            "ui.operator_summary.execution_fact_chain",
            "cli.workspace_state.execution_fact_chain",
        ],
    }


def _duration_seconds_from_artifacts(recent_execution_artifacts: list[dict[str, object]]) -> float | None:
    artifact_paths = [
        ref.get("ref", {}).get("path")
        for ref in recent_execution_artifacts
        if isinstance(ref, dict) and isinstance(ref.get("ref"), dict)
    ]
    timestamps: list[datetime] = []
    for raw_path in artifact_paths:
        if not isinstance(raw_path, str):
            continue
        path = Path(raw_path)
        if not path.exists():
            continue
        timestamps.append(datetime.fromtimestamp(path.stat().st_mtime))
    if len(timestamps) < 2:
        return None
    return round((max(timestamps) - min(timestamps)).total_seconds(), 6)


def workspace_recovery_dashboard(
    *,
    recovery_timeline: dict[str, object],
    runtime_events: dict[str, object],
    recovery_recommendation: dict[str, object] | None,
) -> dict[str, object]:
    timeline_summary = recovery_timeline.get("summary", {}) if isinstance(recovery_timeline.get("summary"), dict) else {}
    runtime_summary = runtime_events.get("summary", {}) if isinstance(runtime_events.get("summary"), dict) else {}
    blocking_summary = (
        timeline_summary.get("blocking_summary", {})
        if isinstance(timeline_summary.get("blocking_summary"), dict)
        else {}
    )
    return {
        "recovery_timeline": {
            "format": recovery_timeline.get("format"),
            "summary": timeline_summary,
            "read_only": True,
        },
        "runtime_events": {
            "format": runtime_events.get("format"),
            "summary": runtime_summary,
            "read_only": True,
        },
        "runtime_fidelity": {
            "provider_session_snapshot_count": len(runtime_events.get("provider_session_snapshots", []))
            if isinstance(runtime_events.get("provider_session_snapshots"), list)
            else 0,
            "operation_receipt_count": len(runtime_events.get("operation_receipts", []))
            if isinstance(runtime_events.get("operation_receipts"), list)
            else 0,
            "live_session_count": runtime_summary.get("live_session_count", 0),
            "missing_session_count": runtime_summary.get("missing_session_count", 0),
            "read_only": True,
        },
        "recovery_recommendation": recovery_recommendation,
        "blocking_summary": blocking_summary,
        "resume_hint": timeline_summary.get("resume_hint"),
        "last_checkpoint": timeline_summary.get("last_checkpoint"),
    }
