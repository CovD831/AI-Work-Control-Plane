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


def run_evidence_command(args: argparse.Namespace) -> None:
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
