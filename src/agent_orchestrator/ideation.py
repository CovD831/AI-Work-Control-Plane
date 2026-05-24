"""Idea discussion and lightweight debate helpers."""
from __future__ import annotations

# DEPS: __future__, agent_orchestrator, dataclasses
# RESPONSIBILITY: Produce structured early-stage debate messages before formal planning.
# MODULE: decision_core
# ---

from dataclasses import dataclass

from agent_orchestrator.messages import MessageRouter, MessageStore


@dataclass(frozen=True, slots=True)
class IdeationRound:
    session_id: str
    requirement: str
    proponent_summary: str
    skeptic_summary: str
    lead_synthesis: str
    message_ids: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "requirement": self.requirement,
            "proponent_summary": self.proponent_summary,
            "skeptic_summary": self.skeptic_summary,
            "lead_synthesis": self.lead_synthesis,
            "message_ids": list(self.message_ids),
        }


def run_ideation(*, requirement: str, session_id: str, message_store: MessageStore) -> IdeationRound:
    router = MessageRouter(message_store)
    proponent_summary = f"Proponent: pursue the idea by turning it into a scoped plan for {requirement}."
    skeptic_summary = f"Skeptic: challenge assumptions, unclear constraints, and execution risk for {requirement}."
    lead_synthesis = (
        "Lead synthesis: keep the idea moving, preserve open questions, and only proceed to execution "
        "after reviewable acceptance criteria exist."
    )
    proponent = router.build_handoff(
        session_id=session_id,
        from_role="lead",
        to_role="proponent",
        content=f"Develop the strongest version of this idea: {requirement}",
        work_unit_id=session_id,
        payload={"phase": "ideation", "position": "proponent"},
        requires_response=True,
    )
    proponent_reply = router.build_handoff(
        session_id=session_id,
        from_role="proponent",
        to_role="lead",
        content=proponent_summary,
        work_unit_id=session_id,
        payload={"phase": "ideation", "reply_to_message_id": proponent.id},
    )
    skeptic = router.build_handoff(
        session_id=session_id,
        from_role="lead",
        to_role="skeptic",
        content=f"Challenge this idea before formal planning: {requirement}",
        work_unit_id=session_id,
        payload={"phase": "ideation", "position": "skeptic"},
        requires_response=True,
    )
    skeptic_reply = router.build_handoff(
        session_id=session_id,
        from_role="skeptic",
        to_role="lead",
        content=skeptic_summary,
        work_unit_id=session_id,
        payload={"phase": "ideation", "reply_to_message_id": skeptic.id},
    )
    synthesis = router.build_handoff(
        session_id=session_id,
        from_role="lead",
        to_role="planner",
        content=lead_synthesis,
        work_unit_id=session_id,
        payload={"phase": "ideation", "inputs": [proponent_reply.id, skeptic_reply.id]},
    )
    return IdeationRound(
        session_id=session_id,
        requirement=requirement,
        proponent_summary=proponent_summary,
        skeptic_summary=skeptic_summary,
        lead_synthesis=lead_synthesis,
        message_ids=[proponent.id, proponent_reply.id, skeptic.id, skeptic_reply.id, synthesis.id],
    )
