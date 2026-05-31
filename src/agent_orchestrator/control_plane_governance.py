"""Governance bundle export and inspection for the control plane."""
from __future__ import annotations

# DEPS: __future__, agent_orchestrator, json, pathlib
# RESPONSIBILITY: Export portable governance bundles and inspect their artifact completeness.
# MODULE: decision_core
# ---

import json
from pathlib import Path

from agent_orchestrator.control_plane_artifacts import artifact_ref as _artifact_ref
from agent_orchestrator.control_plane_artifacts import resolve_root as _resolve_root
from agent_orchestrator.control_plane_constants import CONTROL_PLANE_FORMATS
from agent_orchestrator.jobs import now_iso


def build_governance_bundle(
    project_root: Path | str = ".",
    *,
    query: str = "governance externalization",
    changed_files: list[str] | None = None,
    plans_root: Path | str = ".agent_orchestrator/plans",
    runs_root: Path | str = ".agent_orchestrator/runs",
    jobs_root: Path | str = ".agent_orchestrator/jobs",
    approvals_root: Path | str = ".agent_orchestrator/approvals",
    output_path: Path | str | None = None,
    compliance: dict[str, object] | None = None,
) -> dict[str, object]:
    from agent_orchestrator.control_plane import (
        build_approval_queue,
        build_context_packet,
        build_evidence_bundle,
        build_provider_evidence_summary,
        build_workspace_index,
    )

    root = Path(project_root)
    workspace_index = build_workspace_index(
        root,
        plans_root=plans_root,
        runs_root=runs_root,
        jobs_root=jobs_root,
        approvals_root=approvals_root,
    )
    context_packet = build_context_packet(
        root,
        query=query,
        changed_files=list(changed_files or []),
        jobs_root=jobs_root,
    )
    compliance_payload = compliance or {"blocking": False, "blocking_reasons": [], "warnings": []}
    evidence_bundle = build_evidence_bundle(root, compliance=compliance_payload)
    approval_queue = build_approval_queue(root, plans_root=plans_root, approvals_root=approvals_root)
    provider_evidence_summary = build_provider_evidence_summary(_resolve_root(root, jobs_root))
    artifacts = {
        "workspace_index": workspace_index,
        "context_packet": context_packet,
        "evidence_bundle": evidence_bundle,
        "approval_queue": approval_queue,
        "provider_evidence_summary": provider_evidence_summary,
    }
    payload = {
        "format": CONTROL_PLANE_FORMATS["governance_bundle"],
        "schema_version": "1.0",
        "project_root": str(root),
        "created_at": now_iso(),
        "query": query,
        "changed_files": list(changed_files or []),
        "artifacts": artifacts,
        "artifact_manifest": {
            name: _artifact_ref(artifact)
            for name, artifact in artifacts.items()
            if isinstance(artifact, dict)
        },
        "externalization": {
            "portable": True,
            "offline_inspectable": True,
            "contains_runtime_boundaries": True,
            "contains_provider_evidence_summary": True,
            "mutation_policy": "bundle export is read-only and does not resume, mutate, or own provider sessions",
        },
        "boundaries": {
            "provider_session_ownership": "provider_owned_refs_are_evidence_only",
            "token_cost_policy": "placeholder unless provider reports usage directly",
            "runtime_policy": "local command/runtime evidence, not a full provider bridge",
            "marketplace_policy": "no plugin marketplace distribution claim",
        },
    }
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def inspect_governance_bundle(path: Path | str) -> dict[str, object]:
    bundle_path = Path(path)
    try:
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "format": CONTROL_PLANE_FORMATS["governance_bundle_inspection"],
            "bundle_path": str(bundle_path),
            "complete": False,
            "auditable": False,
            "blocking": True,
            "blocking_reasons": [f"bundle unreadable: {exc}"],
            "warnings": [],
        }
    required_artifacts = [
        "workspace_index",
        "context_packet",
        "evidence_bundle",
        "approval_queue",
        "provider_evidence_summary",
    ]
    artifacts = payload.get("artifacts", {}) if isinstance(payload, dict) and isinstance(payload.get("artifacts"), dict) else {}
    missing = [name for name in required_artifacts if not isinstance(artifacts.get(name), dict)]
    boundaries = payload.get("boundaries", {}) if isinstance(payload, dict) and isinstance(payload.get("boundaries"), dict) else {}
    externalization = (
        payload.get("externalization", {})
        if isinstance(payload, dict) and isinstance(payload.get("externalization"), dict)
        else {}
    )
    evidence_bundle = artifacts.get("evidence_bundle", {}) if isinstance(artifacts.get("evidence_bundle"), dict) else {}
    compliance = evidence_bundle.get("compliance", {}) if isinstance(evidence_bundle.get("compliance"), dict) else {}
    blocking_reasons = list(compliance.get("blocking_reasons", [])) if isinstance(compliance.get("blocking_reasons"), list) else []
    blocking = bool(compliance.get("blocking", False)) or bool(missing)
    warnings: list[str] = []
    if boundaries.get("provider_session_ownership") != "provider_owned_refs_are_evidence_only":
        warnings.append("provider session ownership boundary missing or unclear")
    if externalization.get("portable") is not True or externalization.get("offline_inspectable") is not True:
        warnings.append("externalization portability flags missing or false")
    return {
        "format": CONTROL_PLANE_FORMATS["governance_bundle_inspection"],
        "bundle_path": str(bundle_path),
        "bundle_format": payload.get("format") if isinstance(payload, dict) else None,
        "complete": not missing,
        "auditable": not missing and not warnings,
        "blocking": blocking,
        "blocking_reasons": [*missing, *blocking_reasons],
        "warnings": warnings,
        "artifact_formats": {
            name: artifact.get("format")
            for name, artifact in artifacts.items()
            if isinstance(artifact, dict)
        },
        "boundary_summary": boundaries,
        "externalization": externalization,
    }
