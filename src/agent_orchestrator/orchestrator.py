"""End-to-end adaptive orchestration pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import threading
import time
from pathlib import Path
from uuid import uuid4

from agent_orchestrator.adapters import (
    MockClaudeDecomposer,
    MockClaudePlanner,
    MockClaudeReviewRescue,
    MockCodexWorker,
    PlannerAdapter,
    DecomposerAdapter,
    ReviewRescueAdapter,
    WorkerAdapter,
)
from agent_orchestrator.observability import EventLog
from agent_orchestrator.policies import OrchestrationMode, get_policy
from agent_orchestrator.routing import PolicyRouter, RoutingDecision
from agent_orchestrator.state_machine import StateMachine
from agent_orchestrator.failure import FailureRouter
from agent_orchestrator.run_store import RunStore
from agent_orchestrator.topology import build_execution_topology
from agent_orchestrator.tasks import (
    DecisionArtifact,
    DecisionSignals,
    ExecutionContract,
    OrchestrationAttempt,
    OrchestrationAttemptHandle,
    OrchestrationRun,
    OrchestrationRunHandle,
    WorkUnit,
    WorkUnitResult,
)
from agent_orchestrator.jobs import AgentJob


@dataclass(slots=True)
class Orchestrator:
    """Coordinates Claude-style planning, Codex-style execution, and review/rescue."""

    planner: PlannerAdapter = field(default_factory=MockClaudePlanner)
    decomposer: DecomposerAdapter = field(default_factory=MockClaudeDecomposer)
    worker: WorkerAdapter = field(default_factory=MockCodexWorker)
    reviewer: ReviewRescueAdapter = field(default_factory=MockClaudeReviewRescue)
    router: PolicyRouter = field(default_factory=PolicyRouter)
    failure_router: FailureRouter = field(default_factory=FailureRouter)
    run_store: RunStore = field(default_factory=RunStore)
    _run_threads: dict[str, threading.Thread] = field(default_factory=dict, init=False, repr=False)
    _run_locks: dict[str, threading.Lock] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self.restore_pending_runs()

    def start_run(
        self,
        requirement: str,
        mode: OrchestrationMode | None = OrchestrationMode.SUCCESS_FIRST,
        reroute: bool = True,
        parent_run_id: str | None = None,
        agent_enabled: bool | None = None,
        depth: int | None = None,
    ) -> OrchestrationRunHandle:
        routing_decision: RoutingDecision | None = None
        if mode is None:
            routing_decision = self.router.route(requirement)
            policy = get_policy(routing_decision.mode, agent_enabled=agent_enabled, depth=depth)
            initial_mode = routing_decision.mode
        else:
            policy = get_policy(mode, agent_enabled=agent_enabled, depth=depth)
            initial_mode = mode

        run_id = f"run-{uuid4().hex[:8]}"
        run = OrchestrationRun(
            run_id=run_id,
            parent_run_id=parent_run_id,
            requirement=requirement,
            initial_mode=initial_mode,
            final_mode=policy.mode,
            attempts=[],
            reroute_history=[],
            accepted=False,
            final_state=None,
            status="queued",
            reroute_enabled=reroute,
            events=[{"event": "run_queued", "run_id": run_id}],
            jobs=[],
            routing_decision=routing_decision,
            policy=policy,
            contract=None,
            work_units=[],
            results=[],
            job_ids=[],
            job_status_summary={},
            active_attempt_id=None,
            lineage=[],
            metadata={},
        )
        self._store_run(run)

        if not self.run_store.acquire_run_lock(run_id, owner="orchestrator", reason="start_run"):
            return OrchestrationRunHandle(
                run_id=run_id,
                status=run.status,
                active_attempt_id=None,
                job_ids=[],
                final_mode=run.final_mode,
                parent_run_id=parent_run_id,
            )

        thread = threading.Thread(
            target=self._background_run,
            kwargs={
                "run_id": run_id,
                "requirement": requirement,
                "mode": mode,
                "reroute": reroute,
                "parent_run_id": parent_run_id,
                "agent_enabled": agent_enabled,
                "depth": depth,
            },
            daemon=True,
            name=f"orchestrator-run-{run_id}",
        )
        self._run_threads[run_id] = thread
        thread.start()
        return OrchestrationRunHandle(
            run_id=run_id,
            status=run.status,
            active_attempt_id=None,
            job_ids=[],
            final_mode=run.final_mode,
            parent_run_id=parent_run_id,
        )

    def poll_run(self, run_id: str) -> OrchestrationRun:
        return self._load_run(run_id)

    def poll_attempt(self, run_id: str, attempt_id: str) -> OrchestrationAttempt:
        run = self._load_run(run_id)
        for attempt in run.attempts:
            if attempt.attempt_id == attempt_id:
                return attempt
        raise KeyError(f"Unknown attempt id: {attempt_id}")

    def resume_run(self, run_id: str) -> OrchestrationRun:
        run = self._load_run(run_id)
        if run.status in {"completed", "failed", "blocked", "cancelled"}:
            return run
        if not self.run_store.acquire_run_lock(run_id, owner="orchestrator", reason="resume_run"):
            return self._load_run(run_id)
        if run_id not in self._run_threads or not self._run_threads[run_id].is_alive():
            thread = threading.Thread(
                target=self._background_run,
                kwargs={
                    "run_id": run_id,
                    "requirement": run.requirement,
                    "mode": run.initial_mode,
                    "reroute": run.reroute_enabled,
                    "parent_run_id": run.parent_run_id,
                    "agent_enabled": run.policy.agent_enabled if run.policy else None,
                    "depth": run.policy.topology_depth if run.policy else None,
                },
                daemon=True,
                name=f"orchestrator-resume-{run_id}",
            )
            self._run_threads[run_id] = thread
            thread.start()
        return self._load_run(run_id)

    def reroute_run(self, run_id: str, target_mode: OrchestrationMode | None = None) -> OrchestrationRunHandle:
        run = self._load_run(run_id)
        next_mode = target_mode or self._next_mode(run.final_mode)
        if next_mode is None:
            return OrchestrationRunHandle(
                run_id=run.run_id,
                status=run.status,
                active_attempt_id=run.active_attempt_id,
                job_ids=run.job_ids,
                final_mode=run.final_mode,
                parent_run_id=run.parent_run_id,
            )
        return self.start_run(
            run.contract.goal if run.contract else "",
            next_mode,
            reroute=True,
            parent_run_id=run.run_id,
            agent_enabled=run.policy.agent_enabled if run.policy else None,
            depth=run.policy.topology_depth if run.policy else None,
        )

    def run(
        self,
        requirement: str,
        mode: OrchestrationMode | None = OrchestrationMode.SUCCESS_FIRST,
        reroute: bool = True,
        agent_enabled: bool | None = None,
        depth: int | None = None,
    ) -> OrchestrationRun:
        handle = self.start_run(requirement, mode, reroute=reroute, agent_enabled=agent_enabled, depth=depth)
        return self._wait_for_run(handle.run_id)

    def _background_run(
        self,
        *,
        run_id: str,
        requirement: str,
        mode: OrchestrationMode | None,
        reroute: bool,
        parent_run_id: str | None,
        agent_enabled: bool | None,
        depth: int | None,
    ) -> None:
        heartbeat_stop = threading.Event()
        heartbeat_thread = threading.Thread(
            target=self._run_lock_heartbeat,
            kwargs={"run_id": run_id, "stop_event": heartbeat_stop, "reason": "running"},
            daemon=True,
            name=f"orchestrator-heartbeat-{run_id}",
        )
        heartbeat_thread.start()
        try:
            self._set_run_status(run_id, "running")
            run = self._execute_run(
                requirement,
                mode,
                reroute=reroute,
                parent_run_id=parent_run_id,
                run_id=run_id,
                agent_enabled=agent_enabled,
                depth=depth,
            )
            self._store_run(run)
        except Exception as exc:  # pragma: no cover - background safety net
            try:
                run = self._load_run(run_id)
            except Exception:
                return
            self._store_run(
                OrchestrationRun(
                    run_id=run.run_id,
                    parent_run_id=run.parent_run_id,
                    requirement=run.requirement,
                    initial_mode=run.initial_mode,
                    final_mode=run.final_mode,
                    attempts=run.attempts,
                    reroute_history=run.reroute_history,
                    accepted=run.accepted,
                    final_state=run.final_state,
                    status="failed",
                    reroute_enabled=run.reroute_enabled,
                    events=[*run.events, {"event": "run_failed", "error": str(exc)}],
                    jobs=run.jobs,
                    routing_decision=run.routing_decision,
                    policy=run.policy,
                    contract=run.contract,
                    work_units=run.work_units,
                    results=run.results,
                    job_ids=run.job_ids,
                    job_status_summary=run.job_status_summary,
                    active_attempt_id=run.active_attempt_id,
                    lineage=run.lineage,
                    metadata=run.metadata,
                )
            )
        finally:
            heartbeat_stop.set()
            heartbeat_thread.join(timeout=0.5)
            self.run_store.release_run_lock(run_id)

    def _execute_run(
        self,
        requirement: str,
        mode: OrchestrationMode | None = OrchestrationMode.SUCCESS_FIRST,
        reroute: bool = True,
        parent_run_id: str | None = None,
        run_id: str | None = None,
        agent_enabled: bool | None = None,
        depth: int | None = None,
    ) -> OrchestrationRun:
        routing_decision: RoutingDecision | None = None
        if mode is None:
            routing_decision = self.router.route(requirement)
            policy = get_policy(routing_decision.mode, agent_enabled=agent_enabled, depth=depth)
            initial_mode = routing_decision.mode
        else:
            policy = get_policy(mode, agent_enabled=agent_enabled, depth=depth)
            initial_mode = mode

        attempts: list[OrchestrationAttempt] = []
        reroute_history: list[dict[str, object]] = []
        run_events = EventLog()
        current_mode = policy.mode
        final_attempt: OrchestrationAttempt | None = None
        upgrades_used = 0
        run_id = run_id or f"run-{uuid4().hex[:8]}"
        active_attempt_id: str | None = None
        lineage: list[dict[str, object]] = []

        for attempt_index in range(self.failure_router.max_auto_upgrades + 1):
            attempt_events = EventLog()
            state = StateMachine(attempt_events)
            attempt_id = f"attempt-{uuid4().hex[:8]}"
            active_attempt_id = attempt_id
            attempt_lineage = [*lineage, {"run_id": run_id, "attempt_id": attempt_id, "mode": current_mode.value}]

            state.transition("draft")
            contract = self.planner.clarify(requirement, policy)
            attempt_events.record("contract_created", task_id=contract.id, risk=contract.risk_level)
            state.transition("clarified")

            work_units = self.decomposer.decompose(contract, policy)
            attempt_events.record("work_units_created", count=len(work_units), parallelism=policy.parallelism)
            state.transition("decomposed")

            state.transition("dispatched")
            state.transition("running")

            results = [self._execute_work_unit(work_unit, policy, state, attempt_events) for work_unit in work_units]

            attempt = OrchestrationAttempt(
                attempt_id=attempt_id,
                run_id=run_id,
                parent_run_id=parent_run_id,
                parent_attempt_id=attempts[-1].attempt_id if attempts else None,
                policy=policy,
                contract=contract,
                work_units=work_units,
                results=results,
                accepted=_results_accepted(results),
                final_state="review",
                status="running",
                events=attempt_events.to_list(),
                jobs=[*_runtime_jobs(self.worker), *_runtime_jobs(self.reviewer)],
                routing_decision=routing_decision,
                attempt_index=attempt_index,
                job_ids=_job_ids([*_runtime_jobs(self.worker), *_runtime_jobs(self.reviewer)]),
                job_status_summary=_job_status_summary([*_runtime_jobs(self.worker), *_runtime_jobs(self.reviewer)]),
                current_mode=current_mode,
                lineage=attempt_lineage,
            )
            attempts.append(attempt)
            final_attempt = attempt

            decision = self.failure_router.inspect(attempt)
            attempt.failure_decision = decision
            attempt.failure_signal = (
                self.failure_router._signal(attempt, decision.reasons, any("high-risk" in reason for reason in decision.reasons))
                if decision.next_mode or decision.work_unit_ids
                else None
            )
            attempt.signals = _build_decision_signals(
                contract=contract,
                work_units=work_units,
                results=results,
                reroute_enabled=reroute,
                routing_decision=routing_decision,
            )
            attempt.decision_artifact = _build_decision_artifact(
                policy=policy,
                results=results,
                decision=decision,
                reroute_enabled=reroute,
                accepted=attempt.accepted,
                routing_decision=routing_decision,
            )

            if reroute and decision.action == "partial_rescue" and decision.work_unit_ids:
                replay_results = self._dependency_rescue(
                    work_units=work_units,
                    results=results,
                    policy=policy,
                    events=attempt_events,
                    root_cause_work_unit_ids=decision.root_cause_work_unit_ids,
                    affected_work_unit_ids=decision.affected_work_unit_ids,
                )
                attempt.dependency_rescue_results = replay_results
                attempt.partial_rescue_results = replay_results
                attempt.replayed_work_unit_ids = [result.work_unit_id for result in replay_results]
                attempt.recovered_work_unit_ids = decision.work_unit_ids
                results = _merge_results(results, replay_results)
                attempt.results = results
                attempt.accepted = _results_accepted(results)
                attempt.final_state = "review"
                attempt.status = "rerouting"
                attempt_events.record(
                    "dependency_rescue_finished",
                    replayed_work_unit_ids=attempt.replayed_work_unit_ids,
                    accepted=attempt.accepted,
                )

                decision = self._upgrade_after_dependency_rescue(current_mode, attempt, work_units)
                attempt.failure_decision = decision
                attempt.failure_signal = (
                    self.failure_router._signal(attempt, decision.reasons, any("high-risk" in reason for reason in decision.reasons))
                    if decision.next_mode
                    else attempt.failure_signal
                )

                if attempt.accepted and decision.next_mode is None:
                    state.transition("review")
                    state.transition("accepted")
                    attempt.final_state = state.current
                    attempt.status = "completed"
                    attempt_events.record("run_finished", accepted=True)
                    attempt.decision_artifact = _build_decision_artifact(
                        policy=policy,
                        results=attempt.results,
                        decision=decision,
                        reroute_enabled=reroute,
                        accepted=attempt.accepted,
                        routing_decision=routing_decision,
                    )
                    break

            if attempt.accepted and attempt.final_state == "review" and decision.next_mode is None:
                state.transition("review")
                state.transition("accepted")
                attempt.final_state = state.current
                attempt.status = "completed"
                attempt_events.record("run_finished", accepted=True)
            elif not attempt.accepted:
                state.transition("review")
                attempt.accepted = _results_accepted(attempt.results)
                state.transition("accepted" if attempt.accepted else "blocked")
                attempt.final_state = state.current
                attempt.status = "completed" if attempt.accepted else "blocked"
                attempt_events.record("run_finished", accepted=attempt.accepted)

            attempt.decision_artifact = _build_decision_artifact(
                policy=policy,
                results=attempt.results,
                decision=decision,
                reroute_enabled=reroute,
                accepted=attempt.accepted,
                routing_decision=routing_decision,
            )

            if not reroute or decision.next_mode is None or upgrades_used >= self.failure_router.max_auto_upgrades:
                break

            reroute_history.append(
                {
                    "from_mode": current_mode.value,
                    "to_mode": decision.next_mode.value,
                    "from_agent_enabled": policy.agent_enabled,
                    "to_agent_enabled": decision.next_agent_enabled,
                    "from_depth": policy.topology_depth,
                    "to_depth": decision.next_depth,
                    "upgrade_kind": decision.upgrade_kind,
                    "reasons": decision.reasons,
                    "confidence": decision.confidence,
                }
            )
            run_events.record("reroute", from_mode=current_mode.value, to_mode=decision.next_mode.value)
            upgrades_used += 1
            current_mode = decision.next_mode
            agent_enabled = decision.next_agent_enabled
            depth = decision.next_depth
            policy = get_policy(current_mode, agent_enabled=agent_enabled, depth=depth)
            lineage = [
                *lineage,
                {
                    "from_mode": reroute_history[-1]["from_mode"],
                    "to_mode": reroute_history[-1]["to_mode"],
                    "from_agent_enabled": reroute_history[-1]["from_agent_enabled"],
                    "to_agent_enabled": reroute_history[-1]["to_agent_enabled"],
                    "from_depth": reroute_history[-1]["from_depth"],
                    "to_depth": reroute_history[-1]["to_depth"],
                    "upgrade_kind": reroute_history[-1]["upgrade_kind"],
                },
            ]

        if final_attempt is None:
            raise RuntimeError("No orchestration attempts were executed.")

        return OrchestrationRun(
            run_id=run_id,
            parent_run_id=parent_run_id,
            requirement=requirement,
            initial_mode=initial_mode,
            final_mode=final_attempt.policy.mode,
            attempts=attempts,
            reroute_history=reroute_history,
            accepted=final_attempt.accepted,
            final_state=final_attempt.final_state,
            status="completed" if final_attempt.accepted else "blocked",
            reroute_enabled=reroute,
            events=[*run_events.to_list(), *final_attempt.events],
            jobs=[*_runtime_jobs(self.worker), *_runtime_jobs(self.reviewer)],
            job_ids=_job_ids([*_runtime_jobs(self.worker), *_runtime_jobs(self.reviewer)]),
            job_status_summary=_job_status_summary([*_runtime_jobs(self.worker), *_runtime_jobs(self.reviewer)]),
            routing_decision=routing_decision,
            policy=final_attempt.policy,
            contract=final_attempt.contract,
            work_units=final_attempt.work_units,
            results=final_attempt.results,
            active_attempt_id=active_attempt_id,
            lineage=lineage,
            signals=final_attempt.signals,
            decision_artifact=final_attempt.decision_artifact,
            metadata=_build_run_metadata(
                requirement=requirement,
                mode=final_attempt.policy.mode.value,
                contract=final_attempt.contract,
                work_units=final_attempt.work_units,
                routing_decision=routing_decision,
            ),
        )

    def _load_run(self, run_id: str) -> OrchestrationRun:
        payload = self.run_store.read(run_id)
        if not payload:
            raise KeyError(f"Unknown run id: {run_id}")
        run = OrchestrationRun.from_dict(payload)
        run.lock_status = self.run_store.read_run_lock(run_id)
        return run

    def _store_run(self, run: OrchestrationRun) -> None:
        payload = run.to_dict()
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        metadata.setdefault("entrypoint", "direct_run")
        metadata.setdefault(
            "provenance",
            {
                "source_requirement": run.requirement,
                "selected_mode": run.final_mode.value,
            },
        )
        metadata.setdefault(
            "execution_contract",
            _build_execution_contract_payload(
                requirement=run.requirement,
                policy_mode=run.final_mode.value,
                contract=run.contract,
                work_units=run.work_units,
            ),
        )
        payload["metadata"] = metadata
        self.run_store.write(run.run_id, payload)

    def _set_run_status(self, run_id: str, status: str) -> None:
        run = self._load_run(run_id)
        self._store_run(
            OrchestrationRun(
                run_id=run.run_id,
                parent_run_id=run.parent_run_id,
                requirement=run.requirement,
                initial_mode=run.initial_mode,
                final_mode=run.final_mode,
                attempts=run.attempts,
                reroute_history=run.reroute_history,
                accepted=run.accepted,
                final_state=run.final_state,
                status=status,
                reroute_enabled=run.reroute_enabled,
                events=[*run.events, {"event": "run_status_changed", "status": status}],
                jobs=run.jobs,
                routing_decision=run.routing_decision,
                policy=run.policy,
                contract=run.contract,
                work_units=run.work_units,
                results=run.results,
                job_ids=run.job_ids,
                job_status_summary=run.job_status_summary,
                active_attempt_id=run.active_attempt_id,
                lineage=run.lineage,
                metadata=run.metadata,
            )
        )

    def _wait_for_run(self, run_id: str) -> OrchestrationRun:
        while True:
            try:
                run = self._load_run(run_id)
            except Exception:
                time.sleep(0.01)
                continue
            if not run:
                time.sleep(0.01)
                continue
            if run.status in {"completed", "failed", "blocked", "cancelled"}:
                return run
            time.sleep(0.01)

    def restore_pending_runs(self) -> None:
        root = Path(self.run_store.root)
        for path in sorted(root.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                run = OrchestrationRun.from_dict(payload)
            except Exception:
                continue
            if run.status in {"completed", "failed", "blocked", "cancelled"}:
                continue
            if run.run_id in self._run_threads and self._run_threads[run.run_id].is_alive():
                continue
            if not self.run_store.acquire_run_lock(run.run_id, owner="orchestrator", reason="restore_pending_runs"):
                continue
            thread = threading.Thread(
                target=self._background_run,
                kwargs={
                    "run_id": run.run_id,
                    "requirement": run.requirement,
                    "mode": run.initial_mode,
                    "reroute": run.reroute_enabled,
                    "parent_run_id": run.parent_run_id,
                    "agent_enabled": run.policy.agent_enabled if run.policy else None,
                    "depth": run.policy.topology_depth if run.policy else None,
                },
                daemon=True,
                name=f"orchestrator-restore-{run.run_id}",
            )
            self._run_threads[run.run_id] = thread
            thread.start()

    def _run_lock_heartbeat(self, *, run_id: str, stop_event: threading.Event, reason: str) -> None:
        while not stop_event.wait(0.5):
            if not self.run_store.refresh_run_lock(run_id, owner="orchestrator", reason=reason):
                return

    def _next_mode(self, current_mode: OrchestrationMode) -> OrchestrationMode | None:
        return self.failure_router.choose_next_mode(current_mode, self.failure_router._signal(_policy_run(get_policy(current_mode)), [], False))

    def _execute_work_unit(
        self,
        work_unit: WorkUnit,
        policy: object,
        state: StateMachine,
        events: EventLog,
    ) -> WorkUnitResult:
        events.record("worker_started", work_unit_id=work_unit.id, owner=work_unit.owner_type)
        result = self.worker.execute(work_unit, policy)
        events.record("worker_finished", work_unit_id=work_unit.id, status=result.status)

        if result.needs_rescue or _review_required(work_unit.risk_level, policy.review_required):
            state.transition("rescue" if result.needs_rescue else "review")
            result = self.reviewer.review_or_rescue(work_unit, result, policy)
            events.record("review_rescue_finished", work_unit_id=work_unit.id, status=result.status)
            state.transition("running")

        return result

    def _dependency_rescue(
        self,
        *,
        work_units: list[WorkUnit],
        results: list[WorkUnitResult],
        policy: object,
        events: EventLog,
        root_cause_work_unit_ids: list[str],
        affected_work_unit_ids: list[str],
    ) -> list[WorkUnitResult]:
        units_by_id = {unit.id: unit for unit in work_units}
        replay_ids = [*root_cause_work_unit_ids, *[unit_id for unit_id in affected_work_unit_ids if unit_id not in root_cause_work_unit_ids]]
        replayed_results: list[WorkUnitResult] = []

        for work_unit_id in replay_ids:
            work_unit = units_by_id[work_unit_id]
            events.record("dependency_rescue_started", work_unit_id=work_unit_id)
            rerun = self.worker.execute(work_unit, policy)
            rerun = self.reviewer.review_or_rescue(work_unit, rerun, policy)
            events.record("dependency_rescue_work_unit_finished", work_unit_id=work_unit_id, status=rerun.status)
            replayed_results.append(rerun)

        return replayed_results

    def _upgrade_after_dependency_rescue(
        self,
        current_mode: OrchestrationMode,
        attempt: OrchestrationAttempt,
        work_units: list[WorkUnit],
    ) -> object:
        units_by_id = {unit.id: unit for unit in work_units}
        reasons: list[str] = []
        if any(result.status == "failed" for result in attempt.results):
            reasons.append("dependency rescue left failed work units")
        if any(
            result.review_result and result.review_result.verdict == "needs_attention"
            for result in attempt.results
        ):
            reasons.append("dependency rescue left high-risk review findings")
        if current_mode != OrchestrationMode.SUCCESS_FIRST and any(
            result.recovery_origin_status == "failed" for result in attempt.dependency_rescue_results
        ):
            reasons.append("dependency rescue followed an original failed work unit")
        if current_mode != OrchestrationMode.SUCCESS_FIRST and any(
            _is_high_risk_work_unit(units_by_id[result.work_unit_id])
            for result in attempt.dependency_rescue_results
        ):
            reasons.append("dependency rescue still involves high-risk work units")

        signal = self.failure_router._signal(attempt, reasons, any("high-risk" in reason for reason in reasons))
        return type(attempt.failure_decision)(
            action="upgrade_mode" if signal.next_mode else "abort",
            next_mode=signal.next_mode,
            next_agent_enabled=signal.next_agent_enabled,
            next_depth=signal.next_depth,
            upgrade_kind=signal.upgrade_kind,
            work_unit_ids=[],
            reasons=reasons or ["dependency rescue did not require escalation"],
            confidence=0.8 if reasons else 0.5,
        )


def _review_required(risk_level: str, review_required: bool | str) -> bool:
    if review_required is True:
        return True
    if review_required == "risk_based":
        return risk_level in {"medium", "high"}
    return False


def _results_accepted(results: list[WorkUnitResult]) -> bool:
    return all(
        result.status in {"succeeded", "rescued"}
        and not (result.review_result and result.review_result.verdict == "needs_attention")
        for result in results
    )


def _policy_run(policy: object) -> object:
    return type("PolicyRun", (), {"policy": policy})()


def _merge_results(
    results: list[WorkUnitResult],
    replacements: list[WorkUnitResult],
) -> list[WorkUnitResult]:
    replacements_by_id = {result.work_unit_id: result for result in replacements}
    return [replacements_by_id.get(result.work_unit_id, result) for result in results]


def _is_high_risk_work_unit(work_unit: WorkUnit) -> bool:
    lowered = f"{work_unit.goal} {work_unit.context} {' '.join(work_unit.inputs)}".lower()
    return any(token in lowered for token in ["auth", "payment", "security", "migration"])


def _runtime_jobs(adapter: object) -> list[AgentJob]:
    runtime = getattr(adapter, "runtime", None)
    jobs = getattr(runtime, "jobs", None)
    if isinstance(jobs, dict):
        return list(jobs.values())
    list_recent = getattr(runtime, "list_recent", None)
    if callable(list_recent):
        try:
            return list(list_recent())
        except Exception:
            return []
    return []


def _job_ids(jobs: list[AgentJob]) -> list[str]:
    return [job.id for job in jobs]


def _job_status_summary(jobs: list[AgentJob]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for job in jobs:
        summary[job.status] = summary.get(job.status, 0) + 1
    return summary


def _build_decision_signals(
    *,
    contract: object,
    work_units: list[WorkUnit],
    results: list[WorkUnitResult],
    reroute_enabled: bool,
    routing_decision: RoutingDecision | None,
) -> DecisionSignals:
    has_failures = any(
        result.status == "failed" or result.recovery_origin_status == "failed"
        for result in results
    )
    has_rescues = any(result.status == "rescued" for result in results)
    needs_review_attention = any(
        result.review_result and result.review_result.verdict == "needs_attention"
        for result in results
    )
    return DecisionSignals(
        task={
            "owner_type": contract.owner_type,
            "parallelism": "high" if contract.parallelizable else "low",
            "goal": contract.goal,
            "route_source": "router" if routing_decision else "explicit_mode",
        },
        risk={
            "contract_risk": contract.risk_level,
            "review_attention": needs_review_attention,
            "routing_risk": routing_decision.profile.risk if routing_decision else contract.risk_level,
        },
        dependency={
            "work_unit_count": len(work_units),
            "has_dependencies": any(unit.depends_on for unit in work_units),
        },
        failure={
            "has_failures": has_failures,
            "has_rescues": has_rescues,
            "failed_work_unit_count": sum(
                1
                for result in results
                if result.status == "failed" or result.recovery_origin_status == "failed"
            ),
        },
        budget={
            "reroute_enabled": reroute_enabled,
            "max_depth": contract.max_depth,
        },
    )


def _build_decision_artifact(
    *,
    policy: object,
    results: list[WorkUnitResult],
    decision: object,
    reroute_enabled: bool,
    accepted: bool,
    routing_decision: RoutingDecision | None,
) -> DecisionArtifact:
    replay_policy = "none"
    if any(result.recovery_origin_status == "failed" for result in results):
        replay_policy = "dependency_affected"
    elif any(result.status == "failed" for result in results):
        replay_policy = "failed_only"

    stop_reason = "accepted" if accepted else "blocked"
    if getattr(decision, "next_mode", None) is not None and reroute_enabled:
        stop_reason = "rerouted"

    return DecisionArtifact(
        route={
            "selected_mode": policy.mode.value,
            "agent_enabled": policy.agent_enabled,
            "topology_depth": policy.topology_depth,
            "source": "router" if routing_decision else "explicit_mode",
        },
        review_level={
            "policy": "required" if policy.review_required is True else str(policy.review_required),
        },
        rescue_mode={
            "policy": policy.rescue_policy,
            "enabled": policy.rescue_enabled,
        },
        replay_scope={
            "policy": replay_policy,
        },
        reroute_policy={
            "enabled": reroute_enabled,
            "next_mode": getattr(getattr(decision, "next_mode", None), "value", None),
            "upgrade_kind": getattr(decision, "upgrade_kind", "abort"),
        },
        stop_reason=stop_reason,
    )


def _build_execution_contract_payload(
    *,
    requirement: str,
    policy_mode: str,
    contract: TaskContract | None,
    work_units: list[WorkUnit],
) -> dict[str, object]:
    goal = contract.goal if contract else requirement
    acceptance_criteria = list(contract.acceptance_criteria) if contract else []
    single_worker_only = len(work_units) == 1 and work_units[0].owner_type == "single_worker"
    topology = build_execution_topology(
        policy_mode,
        agent_enabled=False if single_worker_only else None,
        depth=len([unit for unit in work_units if unit.provider_hint]),
    )
    return ExecutionContract(
        source="approved_plan_style_direct_run",
        goal=goal,
        acceptance_criteria=acceptance_criteria,
        topology={
            "selected_mode": policy_mode,
            "selected_topology": topology.topology_name,
            "provider_flow": [unit.provider_hint for unit in work_units if unit.provider_hint],
            "work_unit_count": len(work_units),
        },
        provider_recommendation={
            "author": "codex",
            "reviewer": "claude",
        },
        gating={
            "contract_source": "direct_requirement_with_planning_contract",
            "review_required": bool(contract and "review summary" in contract.outputs),
        },
    ).to_dict()


def _build_run_metadata(
    *,
    requirement: str,
    mode: str,
    contract: TaskContract,
    work_units: list[WorkUnit],
    routing_decision: RoutingDecision | None,
) -> dict[str, object]:
    execution_contract = _build_execution_contract_payload(
        requirement=requirement,
        policy_mode=mode,
        contract=contract,
        work_units=work_units,
    )
    topology = execution_contract.get("topology", {}) if isinstance(execution_contract, dict) else {}
    provider_recommendation = (
        execution_contract.get("provider_recommendation", {}) if isinstance(execution_contract, dict) else {}
    )
    metadata = {
        "entrypoint": "direct_run",
        "provenance": {
            "source_requirement": requirement,
            "selected_mode": mode,
            "route_source": "router" if routing_decision else "explicit_mode",
            "selected_topology": topology.get("selected_topology"),
            "selected_provider_runtime": provider_recommendation,
        },
        "approved_plan_summary": {
            "session_id": None,
            "goal": contract.goal,
            "selected_topology": topology.get("selected_topology"),
            "selected_provider_runtime": provider_recommendation,
        },
        "execution_contract": execution_contract,
    }
    return metadata
