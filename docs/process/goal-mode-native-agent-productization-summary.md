# Native Agent Productization Goal Summary

## One-Paragraph Goal

下一阶段 goal 的核心，不再是继续证明 native path 在更多 bounded task 上可用，而是把当前已经具备默认执行能力的 native coding agent，继续推进成更接近 `research_repos/opencode/` 水平的“可日常使用”的 general coding agent product。目标是围绕 tool surface、native planner、session productization 与 native/external unified adapter ecosystem 四个面，缩小当前项目在产品厚度、工具深度与长期任务完成能力上的差距，同时保留现有 governance、approval、evidence、recovery 与 hot-pluggable external fallback/handoff 优势。

This summary now tracks `native_tool_workflow_surface`, `native_tool_productization_surface`, `operator_tool_digest`, `session_productization_surface`, `workflow_continuity`, `planner_closure_posture`, `adapter_productization_surface`, `comparative_adapter_summary`, `comparative_session_posture_summary`, `comparative_session_continuity_summary`, `comparative_daily_driver_summary`, `comparative_completion_summary`, and `shared_productization_contract_ready` as the shared evidence surface.

## Four Required Parts

1. `P0 Tool Surface`
   扩 native agent 的读/搜/补丁/验证工具面，使其更像真实 coding copilot，而不只是 bounded execution kernel。
2. `P1 Native Planner`
   把当前 planner 从 compatibility-heavy 路径继续推进成原生 planner，能更独立地决定 explore / clarify / edit / verify / pause / handoff。
3. `P2 Session Productization`
   强化长任务 session 的 compaction、resume、cost/runtime metadata、operator-visible continuity，使 native path 更接近日常主执行器。
4. `P3 Unified Adapter Ecosystem`
   把 native/external 执行统一到更完整的 adapter contract / capability surface 下，保留 governed fallback/handoff，但减少体系割裂。

## Completion Standard

只有当以下条件同时成立，这个 goal 才算完成：

- native path 的工具深度、planner 自主性、session continuity、adapter 一致性都出现真实提升；
- 至少一类比当前更长、更复杂的真实仓库任务能主要依赖 native path 闭环，而不只是 bounded happy-path；
- 与 `opencode` 的差距被明确收敛到“平台广度仍落后，但 daily-driver 主路径已更接近同代际”；
- comparative benchmark、workspace index、runtime/session、UI/CLI summary 与文档能共享同一类 productization 证据；
- external agent 仍可热插拔接入，且 fallback / handoff 继续受治理。

## Shared Evidence Note

完成判定还要求 `session_continuity`、`runtime_cost`、`native_tool_usage`、`planner decision evidence`、`adapter capability surface` 和 `comparative benchmark shared_evidence_surface` 能在 runtime payload / workspace index / UI summary / CLI summary / 文档之间互相对应，而不是只在单点可见。

当前共享证据面的具体例子已经包括：`native_tool_workflow_surface` 与 `native_tool_productization_surface` 作为 operator-facing tool productization aggregate contract，`operator_tool_digest` 作为 operator-facing tool posture digest，`operator_planner_digest` 作为 operator-facing planner posture digest，`session_continuity.session_productization_surface` 作为 operator-facing session productization aggregate contract，`planner_closure_posture` 作为 operator-facing planner closure posture contract，`adapter_productization_surface` 与 `comparative_adapter_summary` 作为 operator-facing adapter productization aggregate contract 及 comparative digest，`comparative_daily_driver_summary` 作为 operator-facing daily-driver proof digest，`comparative_completion_summary` 作为 operator-facing closure-readiness digest，`session_continuity.continuity_snapshot` 作为 artifact-backed continuity digest，`adapter_shared_contract.recovery_contract` 作为 native/external 共享恢复语义契约，以及 comparative benchmark 内的 `shared_contract_alignment` / `shared_productization_contract_ready`。现在 session snapshot 还会把 `session_continuity.comparative_benchmark` 与 `session_continuity.comparative_benchmark_digest` 一起带出来，让 `comparison_posture`、`comparison_posture_basis`、`comparison_proof_strength` 与 `external_comparison_harness_surface` 这层 full benchmark surface 也进入 session continuity / resume contract，而不只是等 workspace、UI 或 CLI 再次反推。其余方面，`native_tool_workflow_surface` 应显式聚合 `explore`、`edit`、`verify` 与 `daily_driver_path`，让 repo-scale exploration 不再只被隐式折叠进 read/search，而是把 bounded glob / candidate fan-out readiness 也作为 daily-driver tool surface 的独立信号投影出来；`native_tool_productization_surface` 则应显式聚合 `repo_exploration_ready`、`bounded_read_search_ready`、`glob_ready`、`structured_patch_ready`、`patch_preview_ready`、`diff_preview_ready`、`verification_ready`、`operator_visibility_ready` 与 `usage_visibility_ready`，而 `operator_tool_digest` 还应显式聚合 `tooling_posture`、`recent_tools`、`explore_tools`、`edit_tools`、`verify_tools` 与 `daily_driver_tools`，`operator_planner_digest` 还应显式聚合 `primary_action`、`selected_executor`、`closure_mode`、`next_recommended_action`、`resume_expectation`、`resume_posture`、`pause_expected`、`handoff_expected`、`fallback_expected` 与 `requires_human_confirmation`，让 workspace index / UI summary / CLI summary / evidence report 不只看得到“工具面 readiness 布尔值”，也看得到主路径上当前最值得操作者理解的工具姿态与 planner 姿态；`session_productization_surface` 应显式聚合 `resume_supported`、`resume_kind`、`compaction_stage`、`runtime_duration_seconds`、`usage_cost_measurement_status`、`operator_continuity` 与 `continuity_readiness`，`planner_closure_posture` 应显式聚合 `closure_mode`、`resume_posture`、`pause_expected`、`handoff_expected`、`fallback_expected`、`clarify_expected` 与 `complete_ready`，而 `adapter_productization_surface` 应显式聚合 `comparison_mode`、`hot_plug_supported`、`fallback_governed`、`resume_contract_supported`、`governed_recovery_ready` 与 `shared_contract_format`；进一步地，`comparative_adapter_summary` 还应显式聚合 `surface_status`、`comparison_mode`、`hot_plug_supported`、`fallback_governed`、`resume_contract_supported`、`governed_recovery_ready`、`default_path` 与 `ownership_boundary`，`comparative_daily_driver_summary` 还应显式聚合 `comparison_status`、`daily_driver_repeatability_tier`、`independent_daily_driver_repo_task_family_count`、`independent_daily_driver_repo_task_families_proven`、`direct_proof_status` 与 `repeatability_status`，而 `comparative_completion_summary` 还应显式聚合 `completion_ready`、`human_audit_required`、`comparison_status`、`comparison_grade_status`、`blocking_gap` 与 `operator_action`，让 runtime payload / workspace index / UI summary / CLI summary / docs 不只共享原始 benchmark 字段，还共享“当前为什么已经更接近日常主路径、证据强到什么层级、为什么还不能宣布 goal 完成、下一步还需要什么判断或外部 harness”这一层 operator-readable judgment。对于 mixed benchmark suites，comparative benchmark 现在还应显式区分总 `case_count` 与 `productization_case_count`，这样 `shared_productization_contract_ready` 的分母才是 native-runtime productization cases，而不是把 standard / followup / UI-only evidence 一起混进 shared productization 对齐要求里。对于更强的长链 native-first 仓库任务，还应进一步看到 `daily_driver_main_path_ready` 这一类 direct proof，用来表达“shared productization 已 ready，且至少一类更长链真实任务已开始接近日常主路径”；同时也应看到 `comparison_posture`、`comparison_posture_basis`、`comparison_proof_strength`、`comparative_native_tool_summary`、`comparative_adapter_summary`、`comparative_daily_driver_summary`、`comparative_completion_summary` 与 `external_comparison_harness_surface` 这类结构化剩余差距说明、成因说明、证明强度说明、tool/adapter comparative digest、daily-driver proof digest、completion-readiness digest 与 external-comparison runway 说明，避免“更接近日常主路径”或“尚未完成”只停留在审计 prose。为了把“还缺哪些 repeatability 证明”也 productize 成共享 contract，`comparison_proof_strength` 现在还应投影 `stronger_task_families`、`repo_task_acceptance_families_proven`、`daily_driver_repo_task_families_proven`、`independent_daily_driver_repo_task_families_proven` 与 `broader_repeatability_gap_families`，让 stronger family 已证成什么、哪些 family 共享了 daily-driver main path signal、哪些 family 已经能算更独立的 daily-driver repeatability anchor、broader daily-driver family 还缺什么，不再只靠人工解释；`external_comparison_harness_surface` 则应把 authoritative harness 仍缺哪些 artifacts、为什么当前仍需 human audit、下一条 evidence milestone 是什么，也作为同一 shared evidence contract 的一部分投影出来。当前 benchmark 也已经能把 governed internal repo-task slice 上的更宽 repeatability 单独投影为 `repeatability_status=broadly_proven_on_internal_repo_task_slice` 与 `daily_driver_repeatability_tier=multi_family_broad_daily_driver_proven`，这样“内部多 family 已较强可复现”和“外部对比级结论仍偏弱”就不会再混成一个模糊判断。

在 session continuity 这条链上，shared evidence contract 现在还应把 `workflow_continuity` 当成与 `continuity_snapshot`、`runtime_cost`、`native_tool_usage` 同级的主字段：`session_productization_surface` 不只要表达“可恢复”，还要表达当前 `explore/edit/verify` workflow 的 active stage、selected stages、projection readiness、resume alignment 与 recovery alignment；`comparative_session_posture_summary` 与 `comparative_session_continuity_summary` 也应把 `workflow_active_stage`、`selected_workflow_stages`、`workflow_projection_ready`、`workflow_resume_ready`、`workflow_projection_visible` 与 `workflow_recovery_aligned` 明确投影到 workspace index / UI summary / CLI summary / docs，让操作者能直接看到 planner-owned workflow contract 是否贯通，而不是只能从底层 planner trace 或 runtime payload 反推。

更进一步，`docs/process/evidence-cases.json` 这套官方 benchmark case catalog 已经不只是“可加载的一组案例清单”，而是能直接聚合出六类 `repo_task_acceptance` / `independent_daily_driver_repo_task_families_proven` 的 comparative benchmark bundle：`multi_file_operator_surface_repo_task`、`compliance_process_repo_task`、`helper_implementation_repo_task`、`long_chain_native_first_repo_task`、`workspace_index_alignment_repo_task` 与 `evidence_contract_alignment_repo_task`。这意味着当前仓库已能把“单个长链 native-first 样例存在”提升成“官方 case catalog 可以稳定重放出 multi-family daily-driver internal proof slice”，从而把 stronger direct proof 从单点样例推进到 benchmark-bundle 级别；同时也更清楚地把 remaining gap 收敛为 external harness、platform breadth 与更广泛 general-task coverage，而不是继续停留在“是否已有 daily-driver 主路径证据”这个更基础的问题。

在这组 shared contract 里，planner / session 的 operator-visible posture 也需要同样产品化，而不是只在 runtime payload 里局部可见：`session_planner_decision` 现在应显式投影 `decision_boundary`、`autonomy_posture` 与 `delegation_contract`，让 `pause_expected`、`handoff_expected`、`fallback_expected`、`clarify_pause_state`、`approval_pause_state`、`requires_human_confirmation` 与 `resume_expectation` 能在 runtime payload / workspace index / UI summary / CLI summary / docs 中保持同义；`session_continuity_outline` 也应显式投影 `resume_expectation` 与 `autonomy_posture.resume_posture`，让“当前为什么停、预计如何续、是否仍处在 governed handoff/fallback/pause posture”成为 daily-driver 主路径的一部分，而不是依赖操作者重读完整 continuity contract 或 planner internals 才能判断；进一步地，`comparative_session_posture_summary` 还应把 `primary_action`、`pause_expected`、`handoff_expected`、`fallback_expected`、`clarify_pause_state`、`approval_pause_state`、`resume_expectation`、`resume_posture` 与 `next_recommended_action` 收口成一条 operator-readable digest，让 comparative benchmark 不只知道这些字段“存在”，还知道这些字段在主路径上当前表达出的暂停/接续/移交姿态是什么。为了让 comparative benchmark 真正审计这条 shared posture contract，而不是只说 planner evidence 已存在，shared-contract 对齐统计现在也应显式看到 `session_posture_cases`，用来表达这些 pause/handoff/fallback/resume posture 字段已经在 runtime/workspace/UI/CLI/evidence surfaces 之间保持对应。
在原生 planner 侧，`approval_boundary` 这类真正需要 human confirmation 的未知边界现在也应直接触发 `NEED_HUMAN_CONFIRMATION` / `approval_pause`，而不是被折叠进一般性的 `clarify_then_edit`，这样 `pause_expected`、`approval_pause_state` 与 `resume_expectation=approval_pause` 才能在 planner decision、session continuity 和 comparative digest 上保持同一语义。

## Recommended Execution Order

为了避免再次回到“多加几个 bounded coverage case”的局部最优，建议本 goal 内部按以下顺序推进：

1. `P1 Native Planner`
   先提高 planner 的 native-first 独立性，让后续 tool surface、session continuity 和 adapter contract 都有更稳定的主决策面。
2. `P2 Session Productization`
   再补长任务 session 的 continuity、compaction、resume posture 和 runtime/cost metadata，把 native path 推向更可日常使用的主执行器。
3. `P0 Tool Surface`
   在 planner 和 session 主链路更稳定之后，再扩读/搜/补丁/验证/探索工具面，避免工具只停留在 helper 层。
4. `P3 Unified Adapter Ecosystem`
   最后统一 native/external contract、benchmark 和 recovery semantics，收口成更一致的 executor ecosystem。

## Detail File

完整 goal 细节、阶段验收、文件级验收与停止条件见：

[goal-mode-native-agent-productization.md](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/goal-mode-native-agent-productization.md)
