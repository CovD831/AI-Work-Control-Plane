from __future__ import annotations

from agent_orchestrator.execution.models import (
    derive_adapter_capability_summary,
    derive_adapter_productization_surface,
)


def test_derive_adapter_productization_surface_from_native_adapter_contract() -> None:
    surface = derive_adapter_productization_surface(
        adapter_contract={
            "adapter_family": "native_first_party",
            "agent_kind": "coding_agent",
            "approval_semantics": {
                "approval_required": True,
                "approval_pause_supported": True,
            },
            "evidence_outputs": ["execution_result", "runtime_event_stream"],
            "recovery_surfaces": ["state_store", "resume_contract"],
            "capability_surface": {
                "governance": {
                    "hot_plug_supported": True,
                    "fallback_governed": True,
                },
                "comparability": {
                    "comparison_mode": "same_contract_two_executors",
                },
                "shared_contract": {
                    "format": "agent_orchestrator.adapter_shared_contract.v1",
                    "comparison_mode": "same_contract_two_executors",
                    "path_selection": {
                        "default_path": "native",
                        "operating_boundary": "native_preferred",
                    },
                    "continuity_support": {
                        "resume_contract": True,
                    },
                    "recovery_contract": {
                        "continue_allowed": True,
                        "scope_realign_required": False,
                        "fallback_allowed": True,
                        "handoff_allowed": True,
                        "remaining_budget_preserved": True,
                        "resume_continuity_required": True,
                    },
                },
            },
        }
    )

    assert surface["format"] == "agent_orchestrator.adapter_productization_surface.v1"
    assert surface["surface_status"] == "same_contract_two_executors_governed"
    assert surface["shared_contract_format"] == "agent_orchestrator.adapter_shared_contract.v1"
    assert surface["resume_contract_supported"] is True
    assert surface["operator_recovery_surface"]["format"] == "agent_orchestrator.adapter_operator_recovery_surface.v1"
    assert surface["operator_recovery_surface"]["default_recovery_lane"] == "approval_pause"
    assert surface["evidence_output_count"] == 2
    assert surface["recovery_surface_count"] == 2


def test_derive_adapter_productization_surface_from_shared_contract_shape() -> None:
    surface = derive_adapter_productization_surface(
        adapter_shared_contract={
            "adapter_family": "native_first_party",
            "agent_kind": "coding_agent",
            "comparison_mode": "same_contract_two_executors",
            "default_path": "native",
            "operating_boundary": "native_preferred",
            "approval_required": True,
            "approval_pause_supported": True,
            "hot_plug_supported": True,
            "fallback_governed": True,
            "shared_contract_resume_supported": True,
            "shared_contract_format": "agent_orchestrator.adapter_shared_contract.v1",
            "evidence_outputs": ["execution_result", "runtime_event_stream"],
            "recovery_surfaces": ["state_store", "resume_contract"],
            "recovery_contract": {
                "continue_allowed": True,
                "scope_realign_required": False,
                "fallback_allowed": True,
                "handoff_allowed": True,
                "remaining_budget_preserved": True,
                "resume_continuity_required": True,
            },
            "operator_recovery_surface": {
                "format": "agent_orchestrator.adapter_operator_recovery_surface.v1",
                "default_recovery_lane": "approval_pause",
            },
        }
    )

    assert surface["format"] == "agent_orchestrator.adapter_productization_surface.compat.v1"
    assert surface["surface_status"] == "same_contract_two_executors_governed"
    assert surface["governed_recovery_ready"] is True
    assert surface["shared_contract_format"] == "agent_orchestrator.adapter_shared_contract.v1"
    assert surface["operator_recovery_surface"]["default_recovery_lane"] == "approval_pause"
    assert "workspace_index" in surface["shared_evidence_surface"]


def test_derive_adapter_capability_summary_from_capability_surface() -> None:
    summary = derive_adapter_capability_summary(
        adapter_capability_surface={
            "format": "agent_orchestrator.adapter_capability_surface.v1",
            "adapter_family": "native_first_party",
            "agent_kind": "coding_agent",
            "governance": {
                "approval_required": True,
                "approval_pause_supported": True,
                "hot_plug_supported": True,
                "fallback_governed": True,
            },
            "evidence_outputs": ["execution_result", "runtime_event_stream"],
            "recovery_surfaces": ["state_store", "resume_contract"],
            "comparability": {
                "comparison_mode": "same_contract_two_executors",
            },
            "shared_contract": {
                "format": "agent_orchestrator.adapter_shared_contract.v1",
                "path_selection": {
                    "default_path": "native",
                },
                "continuity_support": {
                    "resume_contract": True,
                },
                "recovery_contract": {
                    "continue_allowed": True,
                    "scope_realign_required": False,
                    "fallback_allowed": True,
                    "handoff_allowed": True,
                    "remaining_budget_preserved": True,
                    "resume_continuity_required": True,
                },
                "operator_recovery_surface": {
                    "format": "agent_orchestrator.adapter_operator_recovery_surface.v1",
                    "default_recovery_lane": "approval_pause",
                },
            },
        }
    )

    assert summary["format"] == "agent_orchestrator.adapter_capability_surface.v1"
    assert summary["comparison_mode"] == "same_contract_two_executors"
    assert summary["hot_plug_supported"] is True
    assert summary["approval_required"] is True
    assert summary["shared_contract_format"] == "agent_orchestrator.adapter_shared_contract.v1"
    assert summary["shared_contract_path_default"] == "native"
    assert summary["shared_contract_resume_supported"] is True
    assert summary["shared_contract_recovery_contract"]["fallback_allowed"] is True
    assert summary["shared_contract_operator_recovery_surface"]["default_recovery_lane"] == "approval_pause"
    assert summary["shared_evidence_surface"] == [
        "runtime_payload",
        "workspace_index",
        "ui_execution_summary",
        "cli_execution_summary",
        "evidence_report",
    ]
