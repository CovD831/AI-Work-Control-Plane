"""Team command dispatch for the CLI."""
from __future__ import annotations

# DEPS: __future__, agent_orchestrator, argparse, collections, dataclasses, json, pathlib
# RESPONSIBILITY: Dispatch planning-governance team subcommands away from the main CLI parser.
# MODULE: interface
# ---

import argparse
from collections.abc import Callable
from dataclasses import dataclass
import json
import os
from pathlib import Path

from agent_orchestrator.agent_config import AgentConfigStore
from agent_orchestrator.cli_common import emit_json as _emit_json, json_only as _json_only
from agent_orchestrator.cli_presenters import (
    pick_primary_action as _pick_primary_action,
    print_approval_queue_summary as _print_approval_queue_summary_presenter,
    print_approval_resolution_summary as _print_approval_resolution_summary_presenter,
    print_blocker_session_summary as _print_blocker_session_summary_presenter,
    print_context_packet_summary as _print_context_packet_summary_presenter,
    print_docs_context_summary as _print_docs_context_summary_presenter,
    print_docs_index_summary as _print_docs_index_summary_presenter,
    print_evidence_bundle_summary as _print_evidence_bundle_summary_presenter,
    print_execution_session_summary as _print_execution_session_summary_presenter,
    print_handoff_summary as _print_handoff_summary_presenter,
    print_provider_session_snapshot_summary as _print_provider_session_snapshot_summary_presenter,
    print_team_next as _print_team_next_presenter,
    print_team_runbook as _print_team_runbook_presenter,
    print_team_summary as _print_team_summary_presenter,
    print_topology_snapshot_summary as _print_topology_snapshot_summary_presenter,
    print_workspace_state_summary as _print_workspace_state_summary_presenter,
    status_summary as _status_summary,
    summary_bool as _summary_bool,
    team_next_alternatives as _team_next_alternatives,
)
from agent_orchestrator.control_plane import (
    build_approval_queue,
    build_context_packet,
    build_evidence_bundle,
    build_execution_topology_snapshot,
    build_governance_bundle,
    build_provider_evidence_summary,
    build_provider_session_snapshot,
    build_recovery_recommendation,
    build_workspace_index,
    inspect_governance_bundle,
    resolve_approval_item,
)
from agent_orchestrator.policies import OrchestrationMode
from agent_orchestrator.planning import build_operator_runbook
from agent_orchestrator.planning_support import repair_missing_source_headers
from agent_orchestrator.roles import role_contracts


@dataclass(frozen=True, slots=True)
class TeamCommandHandlers:
    build_team_orchestrator: Callable[[str, str | None, str, str], object]
    provider_health_snapshot: Callable[..., dict[str, object]]
    runtime_mode_contract: Callable[[], list[dict[str, object]]]


def run_team_command(args: argparse.Namespace, parser: argparse.ArgumentParser, handlers: TeamCommandHandlers) -> None:
    team = handlers.build_team_orchestrator(args.runtime, getattr(args, "provider", None), args.plans_root, args.runs_root)
    health_snapshot = handlers.provider_health_snapshot() if args.runtime == "command" else None
    if args.team_command == "start":
        _emit_json(
            team.start(
                args.requirement,
                review_policy_override=getattr(args, "review_policy", "auto"),
                provider_health_snapshot=health_snapshot,
            ).to_dict(),
            args,
        )
        return
    if args.team_command == "status":
        _emit_json(team.status(args.session_id).to_dict(), args)
        return
    if args.team_command == "summary":
        session = team.status(args.session_id)
        if _json_only(args):
            _emit_json(session.to_dict(), args)
        else:
            _print_team_summary(session)
        return
    if args.team_command == "roles":
        payload = _team_role_contract_payload()
        if not _json_only(args):
            _print_team_role_contracts(payload)
        _emit_json(payload, args)
        return
    if args.team_command == "next":
        session = team.status(args.session_id)
        if _json_only(args):
            payload = session.to_dict()
            payload["recovery_recommendation"] = build_recovery_recommendation(session)
            _emit_json(payload, args)
        else:
            _print_team_next(session, args)
        return
    if args.team_command == "task":
        if args.task_command == "list":
            payload = team.task_list(args.session_id)
        elif args.task_command == "next":
            payload = team.task_next(args.session_id)
        elif args.task_command == "done":
            payload = team.task_done(args.session_id, args.task_id)
        else:
            parser.error("a team task subcommand is required")
        if not _json_only(args):
            _print_team_task_payload(payload)
        _emit_json(payload, args)
        return
    if args.team_command == "runbook":
        _print_team_runbook(team.status(args.session_id))
        return
    if args.team_command == "check-compliance":
        changed_files = list(getattr(args, "changed_file", []) or [])
        payload = (
            team.check_session_compliance(args.session_id, changed_files=changed_files)
            if args.session_id
            else team.check_compliance(changed_files=changed_files)
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        if payload.get("blocking"):
            raise SystemExit(1)
        return
    if args.team_command == "refresh-docs":
        print(json.dumps(team.refresh_documentation_sync(), ensure_ascii=False, indent=2))
        return
    if args.team_command == "repair-compliance":
        changed_files = list(getattr(args, "changed_file", []) or [])
        refresh_payload = team.refresh_documentation_sync()
        header_repair = (
            repair_missing_source_headers(Path.cwd(), changed_files=changed_files)
            if getattr(args, "fix_headers", False)
            else {"changed_files": [], "required_actions": [], "remaining_warnings": []}
        )
        compliance = (
            team.check_session_compliance(args.session_id, changed_files=changed_files)
            if args.session_id
            else team.check_compliance(changed_files=changed_files)
        )
        payload = {
            "refresh_results": refresh_payload.get("refresh_results", []),
            "header_repair": header_repair,
            "doc_sync": refresh_payload,
            "compliance": compliance,
            "required_actions": compliance.get("required_actions", []),
            "remaining_warnings": compliance.get("warnings", []),
            "recommended_commands": compliance.get("recommended_commands", []),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        if compliance.get("blocking"):
            raise SystemExit(1)
        return
    if args.team_command == "retry-review":
        print(json.dumps(team.retry_review(args.session_id).to_dict(), ensure_ascii=False, indent=2))
        return
    if args.team_command == "retry-adversarial-review":
        print(json.dumps(team.retry_adversarial_review(args.session_id).to_dict(), ensure_ascii=False, indent=2))
        return
    if args.team_command == "chat":
        print(json.dumps(team.chat_with_lead(args.session_id, message=args.message).to_dict(), ensure_ascii=False, indent=2))
        return
    if args.team_command == "draft-ready":
        print(json.dumps(team.mark_draft_ready(args.session_id).to_dict(), ensure_ascii=False, indent=2))
        return
    if args.team_command == "submit-review":
        print(json.dumps(team.submit_draft_for_review(args.session_id).to_dict(), ensure_ascii=False, indent=2))
        return
    if args.team_command == "resume":
        print(json.dumps(team.resume(args.session_id, apply=getattr(args, "apply", False)).to_dict(), ensure_ascii=False, indent=2))
        return
    if args.team_command == "approve":
        print(json.dumps(team.approve(args.session_id).to_dict(), ensure_ascii=False, indent=2))
        return
    if args.team_command == "revise":
        print(
            json.dumps(
                team.revise(args.session_id, summary=args.summary, closed_gap_ids=list(args.close_gap)).to_dict(),
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    if args.team_command == "execute":
        mode = None if args.mode == "auto" else OrchestrationMode(args.mode)
        print(
            json.dumps(
                team.execute(
                    args.session_id,
                    mode,
                    review_policy_override=getattr(args, "review_policy", "auto"),
                    provider_health_snapshot=health_snapshot,
                    context_policy=getattr(args, "context_policy", "resume_if_same_task"),
                ).to_dict(),
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    if args.team_command == "setup":
        payload = _team_setup_snapshot(team, args, handlers)
        if not _json_only(args):
            _print_team_setup_summary(payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if args.team_command == "inspect-execution":
        payload = team.inspect_execution(args.session_id)
        if not _json_only(args):
            _print_execution_session_summary(payload)
        _emit_json(payload, args)
        return
    if args.team_command == "inspect-blockers":
        payload = team.inspect_blockers(args.session_id)
        if not _json_only(args):
            _print_blocker_session_summary(payload)
        _emit_json(payload, args)
        return
    if args.team_command == "inspect-knowledge":
        payload = team.inspect_knowledge(args.session_id)
        if not _json_only(args):
            _print_knowledge_summary(payload)
        _emit_json(payload, args)
        return
    if args.team_command == "inspect-handoff":
        payload = team.inspect_handoff(args.session_id, limit=getattr(args, "limit", 10))
        if not _json_only(args):
            _print_handoff_summary(payload)
        _emit_json(payload, args)
        return
    if args.team_command == "inspect-docs":
        payload = team.inspect_docs(
            query=getattr(args, "query", ""),
            changed_files=list(getattr(args, "changed_file", []) or []),
            include_all=bool(getattr(args, "all", False)),
        )
        if not _json_only(args):
            _print_docs_context_summary(payload)
        _emit_json(payload, args)
        return
    if args.team_command == "docs-index":
        payload = team.docs_index(
            query=getattr(args, "query", ""),
            changed_files=list(getattr(args, "changed_file", []) or []),
        )
        if not _json_only(args):
            _print_docs_index_summary(payload)
        _emit_json(payload, args)
        return
    if args.team_command == "workspace-status":
        payload = build_workspace_index(
            Path.cwd(),
            plans_root=getattr(args, "plans_root", ".agent_orchestrator/plans"),
            runs_root=getattr(args, "runs_root", ".agent_orchestrator/runs"),
            jobs_root=getattr(args, "jobs_root", ".agent_orchestrator/jobs"),
            approvals_root=getattr(args, "approvals_root", ".agent_orchestrator/approvals"),
            provider_health=health_snapshot,
        )
        if not _json_only(args):
            _print_workspace_state_summary(payload)
        _emit_json(payload, args)
        return
    if args.team_command == "runtime":
        if args.runtime_command != "inspect":
            parser.error("a team runtime subcommand is required")
        payload = build_provider_session_snapshot(
            args.job_id,
            Path.cwd(),
            jobs_root=getattr(args, "jobs_root", ".agent_orchestrator/jobs"),
        )
        if not _json_only(args):
            _print_provider_session_snapshot_summary(payload)
        _emit_json(payload, args)
        return
    if args.team_command == "context-packet":
        payload = build_context_packet(
            Path.cwd(),
            query=getattr(args, "query", ""),
            changed_files=list(getattr(args, "changed_file", []) or []),
            jobs_root=getattr(args, "jobs_root", ".agent_orchestrator/jobs"),
        )
        if not _json_only(args):
            _print_context_packet_summary(payload)
        _emit_json(payload, args)
        return
    if args.team_command == "topology":
        if args.topology_command != "inspect":
            parser.error("a team topology subcommand is required")
        session = team.status(args.session_id)
        payload = build_execution_topology_snapshot(
            session,
            plans_root=getattr(args, "plans_root", ".agent_orchestrator/plans"),
            approvals_root=getattr(args, "approvals_root", ".agent_orchestrator/approvals"),
            project_root=Path.cwd(),
        )
        if not _json_only(args):
            _print_topology_snapshot_summary(payload)
        _emit_json(payload, args)
        return
    if args.team_command == "approvals":
        if args.approvals_command == "list":
            payload = build_approval_queue(
                Path.cwd(),
                plans_root=getattr(args, "plans_root", ".agent_orchestrator/plans"),
                approvals_root=getattr(args, "approvals_root", ".agent_orchestrator/approvals"),
            )
            if not _json_only(args):
                _print_approval_queue_summary(payload)
            _emit_json(payload, args)
            return
        if args.approvals_command == "resolve":
            payload = resolve_approval_item(
                args.approval_id,
                status=args.status,
                reason=args.reason,
                actor=getattr(args, "actor", "human"),
                project_root=Path.cwd(),
                plans_root=getattr(args, "plans_root", ".agent_orchestrator/plans"),
                approvals_root=getattr(args, "approvals_root", ".agent_orchestrator/approvals"),
            )
            if not _json_only(args):
                _print_approval_resolution_summary(payload)
            _emit_json(payload, args)
            return
        parser.error("a team approvals subcommand is required")
    if args.team_command == "evidence-gates":
        compliance = team.check_compliance()
        payload = build_evidence_bundle(Path.cwd(), compliance=compliance)
        if not _json_only(args):
            _print_evidence_bundle_summary(payload)
        _emit_json(payload, args)
        return
    if args.team_command == "governance-bundle":
        if args.governance_bundle_command == "export":
            compliance = team.check_compliance()
            payload = build_governance_bundle(
                Path.cwd(),
                query=getattr(args, "query", "governance externalization"),
                changed_files=list(getattr(args, "changed_file", []) or []),
                plans_root=getattr(args, "plans_root", ".agent_orchestrator/plans"),
                runs_root=getattr(args, "runs_root", ".agent_orchestrator/runs"),
                jobs_root=getattr(args, "jobs_root", ".agent_orchestrator/jobs"),
                approvals_root=getattr(args, "approvals_root", ".agent_orchestrator/approvals"),
                output_path=args.output,
                compliance=compliance,
            )
            if not _json_only(args):
                print(f"governance_bundle: wrote {args.output}")
            _emit_json(payload, args)
            return
        if args.governance_bundle_command == "inspect":
            payload = inspect_governance_bundle(args.bundle_path)
            if not _json_only(args):
                print(
                    "governance_bundle: "
                    f"complete={'yes' if payload.get('complete') else 'no'} "
                    f"auditable={'yes' if payload.get('auditable') else 'no'} "
                    f"blocking={'yes' if payload.get('blocking') else 'no'}"
                )
            _emit_json(payload, args)
            return
        parser.error("a team governance-bundle subcommand is required")
    parser.error("a team subcommand is required")


def _print_team_summary(session: object) -> None:
    _print_team_summary_presenter(session, pick_primary_action=_pick_primary_action)


def _print_team_next(session: object, args: argparse.Namespace) -> None:
    _print_team_next_presenter(
        session,
        pick_primary_action=_pick_primary_action,
        build_team_next_command=_build_team_next_command,
        team_next_alternatives=_team_next_alternatives,
        args=args,
    )


def _print_team_runbook(session: object) -> None:
    _print_team_runbook_presenter(
        session,
        pick_primary_action=_pick_primary_action,
        build_operator_runbook=build_operator_runbook,
    )


def _print_execution_session_summary(payload: dict[str, object]) -> None:
    _print_execution_session_summary_presenter(payload)


def _print_blocker_session_summary(payload: dict[str, object]) -> None:
    _print_blocker_session_summary_presenter(payload)


def _print_docs_context_summary(payload: dict[str, object]) -> None:
    _print_docs_context_summary_presenter(payload)


def _print_handoff_summary(payload: dict[str, object]) -> None:
    _print_handoff_summary_presenter(payload)


def _print_provider_session_snapshot_summary(payload: dict[str, object]) -> None:
    _print_provider_session_snapshot_summary_presenter(payload)


def _print_docs_index_summary(payload: dict[str, object]) -> None:
    _print_docs_index_summary_presenter(payload)


def _print_workspace_state_summary(payload: dict[str, object]) -> None:
    _print_workspace_state_summary_presenter(payload)


def _print_context_packet_summary(payload: dict[str, object]) -> None:
    _print_context_packet_summary_presenter(payload)


def _print_topology_snapshot_summary(payload: dict[str, object]) -> None:
    _print_topology_snapshot_summary_presenter(payload)


def _print_approval_queue_summary(payload: dict[str, object]) -> None:
    _print_approval_queue_summary_presenter(payload)


def _print_approval_resolution_summary(payload: dict[str, object]) -> None:
    _print_approval_resolution_summary_presenter(payload)


def _print_evidence_bundle_summary(payload: dict[str, object]) -> None:
    _print_evidence_bundle_summary_presenter(payload)


def _print_team_task_payload(payload: dict[str, object]) -> None:
    print(f"session: {payload.get('session_id')}")
    tasks = payload.get("tasks")
    if isinstance(tasks, list):
        for task in tasks:
            if not isinstance(task, dict):
                continue
            blocked_by = task.get("blocked_by", [])
            blocked_text = f" blocked_by={','.join(str(item) for item in blocked_by)}" if blocked_by else ""
            print(
                "task: "
                f"{task.get('id')} status={task.get('status')} owner={task.get('owner')} "
                f"next_action={task.get('next_action')} title={task.get('title')}{blocked_text}"
            )
    next_task = payload.get("next_executable_task")
    if isinstance(next_task, dict):
        print(
            "next_task: "
            f"{next_task.get('id')} action={next_task.get('next_action')} title={next_task.get('title')}"
        )
    elif payload.get("blocked"):
        blocked_by = payload.get("blocked_by", [])
        print(f"blocked_by: {', '.join(str(item) for item in blocked_by) if blocked_by else 'none'}")


def _team_role_contract_payload() -> dict[str, object]:
    contracts = [contract.to_dict() for contract in role_contracts()]
    return {
        "roles": contracts,
        "contract_count": len(contracts),
        "skill_discipline": "职责约束定义了允许动作、禁止动作、结构化输入输出、半自治协作能力以及对应命令入口",
    }


def _print_team_role_contracts(payload: dict[str, object]) -> None:
    print(f"role_contracts: {payload.get('contract_count', 0)}")
    for contract in payload.get("roles", []):
        if not isinstance(contract, dict):
            continue
        print(
            "role: "
            f"{contract.get('role')} runtime_mode={contract.get('runtime_mode')} "
            f"allowed={','.join(str(item) for item in contract.get('allowed_actions', []))} "
            f"required_outputs={','.join(str(item) for item in contract.get('required_outputs', []))} "
            f"inputs={','.join(str(item) for item in contract.get('structured_inputs', []))} "
            f"blocker={contract.get('can_raise_blocker')} "
            f"alternative={contract.get('can_propose_alternative')} "
            f"rfi={contract.get('can_request_information')} "
            f"reflection={contract.get('can_publish_reflection')}"
        )


def _print_knowledge_summary(payload: dict[str, object]) -> None:
    print(f"session: {payload.get('session_id')}")
    counts = payload.get("counts", {}) if isinstance(payload.get("counts"), dict) else {}
    print(
        "knowledge: "
        f"decisions={counts.get('decisions', 0)} lessons={counts.get('lessons', 0)} "
        f"workflow_notes={counts.get('workflow_notes', 0)}"
    )
    for record in payload.get("knowledge", [])[:5]:
        if isinstance(record, dict):
            print(f"- {record.get('artifact_type')}: {record.get('summary')}")


def _build_team_next_command(
    payload: dict[str, object],
    primary_action: str,
    failed_jobs: list[dict[str, object]],
    args: argparse.Namespace,
) -> str:
    session_id = str(payload.get("id"))
    plans_root = str(args.plans_root)
    runs_root = str(args.runs_root)
    status_summary = _status_summary(payload)

    if primary_action == "inspect_delegated_job" and failed_jobs:
        failed_job = failed_jobs[0]
        if str(failed_job.get("provider")) == "claude":
            if str(failed_job.get("round_type")) in {"adversarial_review", "adversarial_review_retry"}:
                return (
                    "python -m agent_orchestrator.cli team retry-adversarial-review "
                    f"{session_id} --plans-root {plans_root} --runs-root {runs_root}"
                )
            return (
                "python -m agent_orchestrator.cli team retry-review "
                f"{session_id} --plans-root {plans_root} --runs-root {runs_root}"
            )
        job_id = str(failed_job.get("job_id"))
        jobs_root = (
            payload.get("doc_sync", {}).get("jobs_root")
            if isinstance(payload.get("doc_sync"), dict)
            else ".agent_orchestrator/jobs"
        )
        return f"python -m agent_orchestrator.cli status {job_id} --root {jobs_root}"
    if primary_action == "revise":
        return (
            "python -m agent_orchestrator.cli team revise "
            f"{session_id} --summary \"close required gaps\" --plans-root {plans_root} --runs-root {runs_root}"
        )
    if primary_action == "mark_draft_ready":
        return (
            "python -m agent_orchestrator.cli team draft-ready "
            f"{session_id} --plans-root {plans_root} --runs-root {runs_root}"
        )
    if primary_action == "submit_review":
        return (
            "python -m agent_orchestrator.cli team submit-review "
            f"{session_id} --plans-root {plans_root} --runs-root {runs_root}"
        )
    if primary_action == "lead_chat":
        return (
            "python -m agent_orchestrator.cli team chat "
            f"{session_id} --message \"clarify the plan\" --plans-root {plans_root} --runs-root {runs_root}"
        )
    if primary_action == "approve":
        return (
            "python -m agent_orchestrator.cli team approve "
            f"{session_id} --plans-root {plans_root} --runs-root {runs_root}"
        )
    if primary_action == "execute":
        if not _summary_bool(status_summary, "approved_plan_ready"):
            return (
                "python -m agent_orchestrator.cli team status "
                f"{session_id} --plans-root {plans_root} --runs-root {runs_root}"
            )
        return (
            "python -m agent_orchestrator.cli team execute "
            f"{session_id} --mode success_first --plans-root {plans_root} --runs-root {runs_root}"
        )
    if primary_action == "human_decision":
        return (
            "python -m agent_orchestrator.cli team summary "
            f"{session_id} --plans-root {plans_root} --runs-root {runs_root}"
        )
    if primary_action == "inspect_compliance":
        return (
            "python -m agent_orchestrator.cli team check-compliance "
            f"{session_id} --plans-root {plans_root} --runs-root {runs_root}"
        )
    if primary_action == "inspect_execution":
        return (
            "python -m agent_orchestrator.cli team inspect-execution "
            f"{session_id} --plans-root {plans_root} --runs-root {runs_root}"
        )
    return (
        "python -m agent_orchestrator.cli team status "
        f"{session_id} --plans-root {plans_root} --runs-root {runs_root}"
    )


def _team_setup_snapshot(team: object, args: argparse.Namespace, handlers: TeamCommandHandlers) -> dict[str, object]:
    project_root = Path.cwd()
    health_snapshot = handlers.provider_health_snapshot(refresh=args.runtime == "command")
    doc_sync = team.refresh_documentation_sync()
    compliance = team.check_compliance()
    agent_config = AgentConfigStore().read()
    role_profiles = _role_profile_snapshot(agent_config)
    readiness = _build_setup_readiness(
        project_root,
        health_snapshot,
        doc_sync,
        compliance,
        runtime_mode_contract=handlers.runtime_mode_contract,
        role_profiles=role_profiles,
    )
    runtime_measurement = _runtime_measurement_readiness(project_root)
    return {
        "contract": {
            "format": "agent_orchestrator.setup_doctor.v1",
            "json_pure": True,
            "pretty_output": "human-readable summary; automation should consume --format json",
        },
        "provider_health": health_snapshot,
        "runtime_modes": handlers.runtime_mode_contract(),
        "role_profiles": role_profiles,
        "doc_sync": doc_sync,
        "compliance": compliance,
        "readiness": readiness,
        "runtime_measurement": runtime_measurement,
        "release_readiness": _build_release_readiness(project_root, compliance, readiness, runtime_measurement),
        "stable_fields": [
            "contract",
            "provider_health",
            "runtime_modes",
            "role_profiles",
            "doc_sync",
            "compliance",
            "readiness",
            "runtime_measurement",
            "release_readiness",
            "recommended_commands",
        ],
        "recommended_commands": [
            "python -m agent_orchestrator.cli team check-compliance",
            "python -m agent_orchestrator.cli team refresh-docs",
            "python -m agent_orchestrator.cli health --format json",
        ],
    }


def _print_team_setup_summary(payload: dict[str, object]) -> None:
    readiness = payload.get("readiness", {}) if isinstance(payload.get("readiness"), dict) else {}
    release = payload.get("release_readiness", {}) if isinstance(payload.get("release_readiness"), dict) else {}
    compliance = readiness.get("compliance_status", {}) if isinstance(readiness.get("compliance_status"), dict) else {}
    provider_states = readiness.get("provider_states", []) if isinstance(readiness.get("provider_states"), list) else []
    role_profiles = payload.get("role_profiles", []) if isinstance(payload.get("role_profiles"), list) else []
    checklist = release.get("checklist", {}) if isinstance(release.get("checklist"), dict) else {}
    available = [str(item.get("provider")) for item in provider_states if isinstance(item, dict) and item.get("available")]
    unavailable = [
        str(item.get("provider"))
        for item in provider_states
        if isinstance(item, dict) and not item.get("available")
    ]
    print(
        "setup: "
        f"ready={'yes' if readiness.get('ready') else 'no'} "
        f"release_ready={'yes' if release.get('ready') else 'no'} "
        f"compliance={'blocked' if compliance.get('blocking') else 'ok'}"
    )
    print(f"providers: available={','.join(available) if available else 'none'} unavailable={','.join(unavailable) if unavailable else 'none'}")
    if role_profiles:
        modes = sorted({str(item.get("runtime_mode")) for item in role_profiles if isinstance(item, dict)})
        print(f"runtime_modes: {','.join(modes)}")
    if checklist:
        checklist_text = ", ".join(
            f"{key}={'ok' if value else 'missing'}"
            for key, value in checklist.items()
        )
        print(f"release_checklist: {checklist_text}")
    commands = payload.get("recommended_commands", []) if isinstance(payload.get("recommended_commands"), list) else []
    if commands:
        print(f"next_command: {commands[0]}")


def _build_release_readiness(
    project_root: Path,
    compliance: dict[str, object],
    readiness: dict[str, object],
    runtime_measurement: dict[str, object] | None = None,
) -> dict[str, object]:
    warnings = list(readiness.get("compliance_status", {}).get("warnings", [])) if isinstance(readiness.get("compliance_status"), dict) else []
    blocking_reasons = list(readiness.get("compliance_status", {}).get("blocking_reasons", [])) if isinstance(readiness.get("compliance_status"), dict) else []
    provider_states = list(readiness.get("provider_states", [])) if isinstance(readiness.get("provider_states"), list) else []
    version_sync = {
        "package_version": _project_version(),
        "version_file_present": (project_root / "pyproject.toml").exists(),
        "version_note": "project metadata is declared in pyproject.toml; no plugin-style distribution is implied",
    }
    evidence_state = {
        "benchmark_report_present": (project_root / "docs" / "process" / "v1x-evidence-report.md").exists(),
        "trend_report_present": (project_root / "docs" / "process" / "v1x-evidence-trend.md").exists(),
        "evidence_cases_present": (project_root / "docs" / "process" / "evidence-cases.json").exists(),
    }
    gate_evidence = _build_gate_evidence_summary(project_root, compliance, evidence_state)
    runtime_measurement = runtime_measurement or _runtime_measurement_readiness(project_root)
    checklist = {
        "version_sync": bool(version_sync["version_file_present"]),
        "tests": "pytest" in " ".join(_release_readiness_commands()),
        "evidence": all(evidence_state.values()),
        "compliance": not blocking_reasons,
        "gate_evidence": bool(gate_evidence.get("available", False)),
        "runtime_measurement": bool(runtime_measurement.get("measurement_surface_available", False)),
    }
    return {
        "project_root": str(project_root),
        "ready": bool(readiness.get("ready", False)) and not blocking_reasons,
        "version_sync": version_sync,
        "provider_states": provider_states,
        "evidence_state": evidence_state,
        "gate_evidence": gate_evidence,
        "runtime_measurement": runtime_measurement,
        "checklist": checklist,
        "warnings": warnings,
        "blocking_reasons": blocking_reasons,
        "recommended_commands": _release_readiness_commands(),
    }


def _build_gate_evidence_summary(
    project_root: Path,
    compliance: dict[str, object],
    evidence_state: dict[str, object],
) -> dict[str, object]:
    gates = [
        {
            "name": "targeted_tests",
            "command": "phase-specific pytest slice",
            "cwd": str(project_root),
            "exit_code": None,
            "duration_seconds": None,
            "summary": "recorded per implementation phase; run only the phase targeted test before final convergence",
            "artifact_path": None,
            "status": "planned",
        },
        {
            "name": "full_tests",
            "command": "pytest",
            "cwd": str(project_root),
            "exit_code": None,
            "duration_seconds": None,
            "summary": "reserved for final convergence",
            "artifact_path": None,
            "status": "planned",
        },
        {
            "name": "compliance",
            "command": "env PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance",
            "cwd": str(project_root),
            "exit_code": 1 if bool(compliance.get("blocking", False)) else 0,
            "duration_seconds": None,
            "summary": "blocked" if bool(compliance.get("blocking", False)) else "passed or warning-only",
            "artifact_path": None,
            "status": "failed" if bool(compliance.get("blocking", False)) else "passed",
        },
        {
            "name": "evidence_report",
            "command": "python -m agent_orchestrator.cli evidence report --output docs/process/v1x-evidence-report.md",
            "cwd": str(project_root),
            "exit_code": 0 if bool(evidence_state.get("benchmark_report_present", False)) else None,
            "duration_seconds": None,
            "summary": "local markdown evidence report present" if bool(evidence_state.get("benchmark_report_present", False)) else "local markdown evidence report missing",
            "artifact_path": "docs/process/v1x-evidence-report.md",
            "status": "passed" if bool(evidence_state.get("benchmark_report_present", False)) else "missing",
        },
    ]
    return {
        "available": True,
        "format": "agent_orchestrator.gate_evidence.v1",
        "log_policy": "large logs stay in artifact_path; setup and release readiness show summaries only",
        "gates": gates,
        "latest": gates[-1],
    }


def _release_readiness_commands() -> list[str]:
    return [
        "python -m agent_orchestrator.cli team check-compliance",
        "python -m agent_orchestrator.cli team refresh-docs",
        "python -m agent_orchestrator.cli evidence report --output docs/process/v1x-evidence-report.md",
        "pytest",
    ]


def _project_version() -> str:
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        return "unknown"
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    return "unknown"


def _build_setup_readiness(
    project_root: Path,
    health_snapshot: dict[str, object],
    doc_sync: dict[str, object],
    compliance: dict[str, object],
    *,
    runtime_mode_contract: Callable[[], list[dict[str, object]]],
    role_profiles: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    providers = health_snapshot.get("providers", []) if isinstance(health_snapshot.get("providers"), list) else []
    provider_states = []
    for item in providers:
        if not isinstance(item, dict):
            continue
        provider_states.append(
            {
                "provider": item.get("provider"),
                "available": bool(item.get("available", False)),
                "binary": item.get("binary"),
                "recommended_fallback": item.get("recommended_fallback"),
                "detail": item.get("detail"),
            }
        )
    warnings = [str(item) for item in compliance.get("warnings", [])] if isinstance(compliance.get("warnings"), list) else []
    blocking_reasons = [str(item) for item in compliance.get("blocking_reasons", [])] if isinstance(compliance.get("blocking_reasons"), list) else []
    ready = not blocking_reasons and not warnings
    return {
        "project_root": str(project_root),
        "ready": ready,
        "provider_states": provider_states,
        "runtime_mode_states": runtime_mode_contract(),
        "role_profiles": role_profiles or [],
        "masked_key_readiness": _masked_key_readiness(),
        "doc_sync_status": {
            "missing_docs": list(doc_sync.get("missing_docs", [])) if isinstance(doc_sync.get("missing_docs"), list) else [],
            "stale_docs": list(doc_sync.get("stale_docs", [])) if isinstance(doc_sync.get("stale_docs"), list) else [],
            "header_contract_violations": list(doc_sync.get("header_contract_violations", [])) if isinstance(doc_sync.get("header_contract_violations"), list) else [],
        },
        "compliance_status": {
            "blocking": bool(compliance.get("blocking", False)),
            "warnings": warnings,
            "blocking_reasons": blocking_reasons,
            "required_actions": list(compliance.get("required_actions", [])) if isinstance(compliance.get("required_actions"), list) else [],
            "recommended_commands": list(compliance.get("recommended_commands", [])) if isinstance(compliance.get("recommended_commands"), list) else [],
        },
    }


def _runtime_measurement_readiness(project_root: Path) -> dict[str, object]:
    jobs_root = project_root / ".agent_orchestrator" / "jobs"
    jobs = []
    if jobs_root.exists():
        for path in sorted(jobs_root.glob("job-*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(payload, dict):
                jobs.append(payload)
    measurements = [
        job.get("runtime_measurement", {})
        for job in jobs
        if isinstance(job.get("runtime_measurement", {}), dict)
    ]
    measured = [item for item in measurements if item.get("measurement_status") == "measured"]
    placeholder = [item for item in measurements if item.get("measurement_status") == "placeholder"]
    unavailable = [item for item in measurements if item.get("measurement_status") == "unavailable"]
    command_duration = [item for item in measurements if item.get("duration_seconds") is not None]
    degraded = [item for item in measurements if item.get("degraded_reason")]
    return {
        "format": "agent_orchestrator.runtime_measurement_readiness.v1",
        "measurement_surface_available": True,
        "job_count": len(jobs),
        "measurement_count": len(measurements),
        "measured_count": len(measured),
        "placeholder_count": len(placeholder),
        "unavailable_count": len(unavailable),
        "command_duration_available_count": len(command_duration),
        "degraded_runtime_count": len(degraded),
        "measurement_status": "measured" if measured else "placeholder" if placeholder or jobs else "unavailable",
        "provider_evidence_summary": build_provider_evidence_summary(jobs_root),
        "rc_blocking": False,
        "rc_blockers": [],
        "policy": "runtime measurement is required as a surface; provider token/cost remains placeholder unless reported by runtime",
    }


def _masked_key_readiness() -> dict[str, object]:
    keys = {
        "openai": os.environ.get("OPENAI_API_KEY"),
        "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
    }
    return {
        provider: {
            "present": bool(value),
            "masked": _mask_secret(value) if value else None,
            "source": "env" if value else "missing",
        }
        for provider, value in keys.items()
    }


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "****"
    return f"{value[:3]}…{value[-4:]}"


def _role_profile_snapshot(agent_config: object) -> list[dict[str, object]]:
    profiles = getattr(agent_config, "profiles", {})
    if not isinstance(profiles, dict):
        return []
    return [
        {
            "role": role,
            "provider": profile.provider,
            "model": profile.model,
            "runtime_mode": profile.runtime_mode,
            "sandbox": profile.sandbox,
            "enabled": profile.enabled,
        }
        for role, profile in sorted(profiles.items())
    ]
