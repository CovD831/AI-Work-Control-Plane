"""Artifact references and JSON helpers for the control plane."""
from __future__ import annotations

# DEPS: __future__, agent_orchestrator, hashlib, json, pathlib, tempfile
# RESPONSIBILITY: Provide stable artifact IDs, references, summaries, and JSON persistence helpers.
# MODULE: decision_core
# ---

import hashlib
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from agent_orchestrator.control_plane_constants import CONTROL_PLANE_FORMATS
from agent_orchestrator.jobs import now_iso


def stable_id(prefix: str, *parts: object) -> str:
    seed = "|".join(str(part) for part in parts)
    return f"{prefix}-{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:12]}"


def atomic_write_json(path: Path, payload: dict[str, object]) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, ensure_ascii=False, indent=2)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)
    return payload


def read_json_object(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def artifact_ref(payload: dict[str, object]) -> dict[str, object]:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return {
        "format": payload.get("format"),
        "digest": hashlib.sha256(data.encode("utf-8")).hexdigest(),
        "created_at": payload.get("created_at"),
        "recorded_at": now_iso(),
        "status": payload.get("status"),
        "summary": artifact_summary(payload),
    }


def artifact_summary(payload: dict[str, object]) -> dict[str, object]:
    artifact_format = payload.get("format")
    if artifact_format == CONTROL_PLANE_FORMATS["workspace_state"]:
        return {
            "plans": len(payload.get("plans", [])) if isinstance(payload.get("plans"), list) else 0,
            "runs": len(payload.get("runs", [])) if isinstance(payload.get("runs"), list) else 0,
            "dirty": (payload.get("dirty_state") or {}).get("dirty")
            if isinstance(payload.get("dirty_state"), dict)
            else None,
        }
    if artifact_format == CONTROL_PLANE_FORMATS["context_packet"]:
        return {
            "query": payload.get("query"),
            "changed_files": len(payload.get("changed_files", [])) if isinstance(payload.get("changed_files"), list) else 0,
            "stale_warnings": len(payload.get("stale_warnings", [])) if isinstance(payload.get("stale_warnings"), list) else 0,
        }
    if artifact_format == CONTROL_PLANE_FORMATS["strategy_decision"]:
        return {
            "session_id": payload.get("session_id"),
            "current_checkpoint_objective": payload.get("current_checkpoint_objective") or payload.get("next_goal"),
            "executes": payload.get("executes"),
        }
    if artifact_format == CONTROL_PLANE_FORMATS["topology_snapshot"]:
        return {
            "session_id": payload.get("session_id"),
            "nodes": len(payload.get("nodes", [])) if isinstance(payload.get("nodes"), list) else 0,
            "read_only": payload.get("read_only"),
        }
    if artifact_format == CONTROL_PLANE_FORMATS["evidence_bundle"]:
        return {"status": payload.get("status")}
    if artifact_format == "agent_orchestrator.execution_artifact_summary.v1":
        compressed_context = payload.get("compressed_context", {})
        context_engineering_contract = payload.get("context_engineering_contract", {})
        step_loop_contract = payload.get("step_loop_contract", {})
        session_continuity_contract = payload.get("session_continuity_contract", {})
        resume_context = payload.get("resume_context", {})
        repo_report = payload.get("repo_report", {})
        adapter_contract = payload.get("adapter_contract", {})
        path_selection = payload.get("path_selection", {})
        strategy_summary = payload.get("strategy_summary", {})
        native_tool_surface = payload.get("native_tool_surface", {})
        native_tool_trace = payload.get("native_tool_trace", {})
        native_task_proof = payload.get("native_task_proof", {})
        native_repo_task_acceptance = payload.get("native_repo_task_acceptance", {})
        native_complex_repo_task_acceptance = payload.get("native_complex_repo_task_acceptance", {})
        step_context_refs = (
            step_loop_contract.get("context_engineering_refs", {})
            if isinstance(step_loop_contract, dict)
            else {}
        )
        tool_trace_entries = list(native_tool_trace.get("trace", [])) if isinstance(native_tool_trace, dict) else []
        return {
            "artifact_count": payload.get("artifact_count", 0),
            "run_id": payload.get("run_id"),
            "session_id": payload.get("session_id"),
            "turn_id": payload.get("turn_id"),
            "compressed_context": dict(compressed_context) if isinstance(compressed_context, dict) else None,
            "context_engineering_contract": dict(context_engineering_contract)
            if isinstance(context_engineering_contract, dict)
            else None,
            "step_loop_contract": dict(step_loop_contract) if isinstance(step_loop_contract, dict) else None,
            "session_continuity_contract": dict(session_continuity_contract)
            if isinstance(session_continuity_contract, dict)
            else None,
            "resume_context": dict(resume_context) if isinstance(resume_context, dict) else None,
            "repo_report": dict(repo_report) if isinstance(repo_report, dict) else None,
            "adapter_contract": dict(adapter_contract) if isinstance(adapter_contract, dict) else None,
            "path_selection": dict(path_selection) if isinstance(path_selection, dict) else None,
            "planner_shared_contract": {
                "format": strategy_summary.get("decision_evidence", {}).get("format")
                if isinstance(strategy_summary.get("decision_evidence"), dict)
                else None,
                "planner_family": strategy_summary.get("planner_family"),
                "selected_strategy": strategy_summary.get("decision_evidence", {}).get("selected_strategy")
                if isinstance(strategy_summary.get("decision_evidence"), dict)
                else strategy_summary.get("selected_execution_strategy"),
                "selected_actions": list(strategy_summary.get("decision_evidence", {}).get("selected_actions", []))
                if isinstance(strategy_summary.get("decision_evidence"), dict)
                and isinstance(strategy_summary.get("decision_evidence", {}).get("selected_actions"), list)
                else [],
                "selected_owner": strategy_summary.get("decision_evidence", {}).get("selected_owner")
                if isinstance(strategy_summary.get("decision_evidence"), dict)
                else None,
                "native_work_units": strategy_summary.get("decision_evidence", {}).get("native_work_units")
                if isinstance(strategy_summary.get("decision_evidence"), dict)
                else None,
                "decision_boundary": dict(strategy_summary.get("decision_evidence", {}).get("decision_boundary", {}))
                if isinstance(strategy_summary.get("decision_evidence"), dict)
                and isinstance(strategy_summary.get("decision_evidence", {}).get("decision_boundary"), dict)
                else {},
                "posture": dict(strategy_summary.get("decision_evidence", {}).get("posture", {}))
                if isinstance(strategy_summary.get("decision_evidence"), dict)
                and isinstance(strategy_summary.get("decision_evidence", {}).get("posture"), dict)
                else {},
            },
            "adapter_shared_contract": {
                "adapter_family": adapter_contract.get("adapter_family"),
                "agent_kind": adapter_contract.get("agent_kind"),
                "default_path": path_selection.get("default_path"),
                "operating_boundary": path_selection.get("operating_boundary"),
                "selection_reason": path_selection.get("selection_reason"),
                "handoff_reason_code": path_selection.get("handoff_reason_code"),
                "fallback_reason_code": path_selection.get("fallback_reason_code"),
                "comparison_mode": (
                    adapter_contract.get("capability_surface", {}).get("comparability", {}).get("comparison_mode")
                    if isinstance(adapter_contract.get("capability_surface"), dict)
                    and isinstance(adapter_contract.get("capability_surface", {}).get("comparability"), dict)
                    else None
                ),
                "hot_plug_supported": (
                    adapter_contract.get("capability_surface", {}).get("governance", {}).get("hot_plug_supported")
                    if isinstance(adapter_contract.get("capability_surface"), dict)
                    and isinstance(adapter_contract.get("capability_surface", {}).get("governance"), dict)
                    else None
                ),
                "fallback_governed": (
                    adapter_contract.get("capability_surface", {}).get("governance", {}).get("fallback_governed")
                    if isinstance(adapter_contract.get("capability_surface"), dict)
                    and isinstance(adapter_contract.get("capability_surface", {}).get("governance"), dict)
                    else None
                ),
                "approval_required": adapter_contract.get("approval_semantics", {}).get("approval_required")
                if isinstance(adapter_contract.get("approval_semantics"), dict)
                else None,
                "approval_pause_supported": adapter_contract.get("approval_semantics", {}).get("approval_pause_supported")
                if isinstance(adapter_contract.get("approval_semantics"), dict)
                else None,
                "evidence_outputs": list(adapter_contract.get("evidence_outputs", []))
                if isinstance(adapter_contract.get("evidence_outputs"), list)
                else [],
                "recovery_surfaces": list(adapter_contract.get("recovery_surfaces", []))
                if isinstance(adapter_contract.get("recovery_surfaces"), list)
                else [],
            },
            "step_loop_context_surfaces": list(step_context_refs.get("required_surfaces", []))
            if isinstance(step_context_refs.get("required_surfaces"), list)
            else [],
            "native_tool_surface": dict(native_tool_surface) if isinstance(native_tool_surface, dict) else None,
            "native_tool_trace": dict(native_tool_trace) if isinstance(native_tool_trace, dict) else None,
            "native_tool_usage": {
                "tool_count": len(native_tool_surface.get("tools", []))
                if isinstance(native_tool_surface, dict) and isinstance(native_tool_surface.get("tools"), list)
                else 0,
                "trace_count": len(tool_trace_entries),
                "recent_tools": [
                    item.get("tool")
                    for item in tool_trace_entries[-5:]
                    if isinstance(item, dict) and item.get("tool")
                ],
            },
            "native_task_proof": dict(native_task_proof) if isinstance(native_task_proof, dict) else None,
            "native_repo_task_acceptance": dict(native_repo_task_acceptance)
            if isinstance(native_repo_task_acceptance, dict)
            else None,
            "native_complex_repo_task_acceptance": dict(native_complex_repo_task_acceptance)
            if isinstance(native_complex_repo_task_acceptance, dict)
            else None,
        }
    return {}


def resolve_root(project_root: Path, path: Path | str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else project_root / candidate
