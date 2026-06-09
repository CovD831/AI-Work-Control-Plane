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
    return {}


def resolve_root(project_root: Path, path: Path | str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else project_root / candidate
