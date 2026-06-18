"""Evidence command handlers for the Agent Orchestrator CLI."""
from __future__ import annotations

# DEPS: __future__, agent_orchestrator, argparse, pathlib
# RESPONSIBILITY: Execute evidence benchmark, capture, report, and compare CLI subcommands.
# MODULE: interface
# ---

import argparse
from pathlib import Path

from agent_orchestrator.cli_common import emit_json, json_only
from agent_orchestrator.evidence import (
    benchmark_evidence_cases,
    compare_workflow_evidence,
    capture_workflow_evidence,
    load_workflow_evidence_payload,
    load_workflow_evidence_cases,
    write_workflow_evidence_trend_markdown,
    write_workflow_evidence_markdown,
)
from agent_orchestrator.opencode_harness import (
    build_authoritative_comparative_report,
    build_comparative_evidence_report,
    build_native_run_records,
    build_opencode_run_records,
    build_same_contract_case_pack,
    normalize_run_records,
    load_case_pack,
    write_case_pack,
)


def run_evidence_command(args: argparse.Namespace) -> None:

    if args.evidence_command == "case-pack":
        case_pack = build_same_contract_case_pack()
        path = write_case_pack(args.output, case_pack)
        if json_only(args):
            emit_json({"output": str(path), "case_pack": case_pack}, args)
        else:
            print(f"Wrote same-contract case pack: {path}")
        return


    if args.evidence_command == "native-run":
        case_pack = load_case_pack(args.case_pack)
        payload = build_native_run_records(case_pack)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(__import__("json").dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if json_only(args):
            emit_json({"output": str(output), "summary": {"runner": payload.get("runner"), "record_count": len(payload.get("records", []))}}, args)
        else:
            print(f"Wrote native run records: {output}")
        return

    if args.evidence_command == "opencode-run":
        case_pack = load_case_pack(args.case_pack)
        payload = build_opencode_run_records(
            case_pack,
            command_template=getattr(args, "command_template", None),
            authoritative_runner=getattr(args, "authoritative_runner", False),
            workspace_dir=getattr(args, "workspace_dir", None),
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(__import__("json").dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if json_only(args):
            emit_json({"output": str(output), "summary": {"runner": payload.get("runner"), "record_count": len(payload.get("records", []))}}, args)
        else:
            print(f"Wrote OpenCode run records: {output}")
        return


    if args.evidence_command == "normalize-records":
        case_pack = load_case_pack(args.case_pack)
        record_set = load_workflow_evidence_payload(args.records)
        payload = normalize_run_records(record_set, case_pack)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(__import__("json").dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if json_only(args):
            emit_json({"output": str(output), "summary": {"runner": payload.get("runner"), "record_count": len(payload.get("records", []))}}, args)
        else:
            print(f"Wrote normalized records: {output}")
        return

    if args.evidence_command == "authoritative-report":
        case_pack = load_case_pack(args.case_pack)
        native_records = load_workflow_evidence_payload(args.native_records)
        opencode_records = load_workflow_evidence_payload(args.opencode_records)
        payload = build_authoritative_comparative_report(case_pack, native_records, opencode_records)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(__import__("json").dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if json_only(args):
            emit_json({"output": str(output), "operator_decision": payload.get("operator_decision", {}), "instrumentation_closure": payload.get("instrumentation_closure", {})}, args)
        else:
            print(f"Wrote authoritative native vs OpenCode comparative report: {output}")
        return

    if args.evidence_command == "external-report":
        case_pack = load_case_pack(args.case_pack)
        native_records = load_workflow_evidence_payload(args.native_records)
        opencode_records = load_workflow_evidence_payload(args.opencode_records)
        payload = build_comparative_evidence_report(case_pack, native_records, opencode_records)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(__import__("json").dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if json_only(args):
            emit_json({"output": str(output), "operator_decision": payload.get("operator_decision", {})}, args)
        else:
            print(f"Wrote native vs OpenCode comparative report: {output}")
        return

    if args.evidence_command == "benchmark":
        payload = capture_workflow_evidence(
            benchmark_evidence_cases(),
            project_root=Path.cwd(),
            output_path=Path(args.output) if args.output else None,
        )
        emit_json(payload, args)
        return

    if args.evidence_command == "capture":
        cases = load_workflow_evidence_cases(args.case_file)
        payload = capture_workflow_evidence(cases, project_root=Path.cwd(), output_path=Path(args.output))
        emit_json(payload, args)
        return

    if args.evidence_command == "report":
        cases = load_workflow_evidence_cases(args.case_file) if args.case_file else benchmark_evidence_cases()
        payload = capture_workflow_evidence(
            cases,
            project_root=Path.cwd(),
            output_path=Path(args.json_output) if args.json_output else None,
        )
        path = write_workflow_evidence_markdown(payload, Path(args.output))
        if json_only(args):
            emit_json({"output": str(path), "summary": payload.get("summary", {})}, args)
        else:
            print(f"Wrote evidence report: {path}")
        return

    if args.evidence_command == "compare":
        payload = compare_workflow_evidence(
            load_workflow_evidence_payload(args.baseline),
            load_workflow_evidence_payload(args.current),
        )
        path = write_workflow_evidence_trend_markdown(payload, Path(args.output))
        if json_only(args):
            baseline = payload.get("baseline", {}) if isinstance(payload.get("baseline"), dict) else {}
            current = payload.get("current", {}) if isinstance(payload.get("current"), dict) else {}
            emit_json(
                {
                    "output": str(path),
                    "deltas": payload.get("deltas", {}),
                    "baseline": {
                        "case_count": baseline.get("case_count", 0),
                        "comparative_benchmark": baseline.get("comparative_benchmark", {}),
                    },
                    "current": {
                        "case_count": current.get("case_count", 0),
                        "comparative_benchmark": current.get("comparative_benchmark", {}),
                    },
                },
                args,
            )
        else:
            print(f"Wrote evidence trend report: {path}")
        return

    raise SystemExit("an evidence subcommand is required")
