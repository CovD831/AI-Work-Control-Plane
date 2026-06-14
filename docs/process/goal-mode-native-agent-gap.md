# Native Coding Agent Gap Assessment

## Context

This project started as an external governance and control plane for long-running coding agents. It now also contains an emerging native coding agent path that is meant to fit the control-plane architecture while preserving hot-pluggable support for external coding agents.

The goal of this assessment is to compare the current native-agent state of this repository against the maturity of `research_repos/opencode/`, and identify the most important capability gaps.

## Bottom Line

The repository is no longer just an external governance shell. It already has a real native coding-agent runtime shape, but it is still materially behind a mature general-purpose coding agent like `opencode` in productized agent depth.

High-level judgment:

- Governance / recovery / evidence / approvals / externalized state: strong, and in some areas ahead of typical coding agents.
- Native coding-agent runtime: real and usable, but still early-to-mid maturity.
- General-purpose agent product completeness: still meaningfully behind `opencode`.

Practical estimate:

- If `opencode` is treated as a mature baseline for a general coding agent, the current native-agent layer here looks roughly like 35%-50% maturity.
- If the target is instead a governance-native coding agent tightly integrated with this control plane, the gap is smaller because this repository already has differentiated strengths that `opencode` does not prioritize.

## Evidence In This Repository

The native coding-agent path is real, not just conceptual:

- `src/agent_orchestrator/execution/coding_agent_runtime.py`
  - Contains an end-to-end runtime flow with repo exploration, context assembly, intent building, execution, verification, recovery projection, approval pauses, and resume handling.
- `src/agent_orchestrator/intake/task_router.py`
  - Provides a lightweight request classification layer that chooses task kind, clarify policy, risk, scope confidence, and execution mode.
- `src/agent_orchestrator/strategy/planner.py`
  - Adds an execution-strategy selection layer, although it still relies on a compatibility bridge to older decomposition behavior.
- `src/agent_orchestrator/execution/coding_components.py`
  - Implements bounded file mutation, command verification, repo exploration, edit intent construction, and retry/verification loops.

This means the project has already crossed the line from “governance wrapper around other agents” into “control plane with its own native execution kernel.”

## Main Gap Versus OpenCode

The largest gap is not whether a native agent exists. The gap is whether it has become a mature, general, productized coding-agent system.

### 1. Tooling Depth Gap

Current native execution is still bounded and narrow compared with mature coding agents.

Current state:

- File mutation is centered on constrained operations like append/replace.
- Verification is bounded and mostly command-based.
- Repo exploration is shallow when explicit targets are absent.

OpenCode maturity:

- Rich built-in tool registry.
- Broader edit/read/search/patch/task/skill/web capabilities.
- More flexible tool composition during multi-step work.

Interpretation:

The current native agent behaves more like a governed execution kernel than a broad, tool-rich coding copilot.

### 2. Repository Understanding Gap

Current repo understanding is still relatively lightweight.

Current state:

- If no strong target is given, candidate discovery falls back to simple file listing heuristics.
- Context assembly exists, but deep semantic repo navigation is still limited.

OpenCode maturity:

- Stronger search-oriented and task-oriented tool surface.
- Support for richer exploration patterns, including specialized tools and session-level task decomposition.

Interpretation:

Your system can operate on repository context, but it does not yet explore codebases with the breadth and fluency expected from a mature coding agent.

### 3. Planner Maturity Gap

Current strategy logic is a real step forward, but not yet a fully independent agent planner.

Current state:

- Strategy selection exists.
- However, the planner is explicitly a compatibility bridge and still leans on legacy decomposition behavior.

OpenCode maturity:

- Agent behavior is embedded in a larger agent/tool/session system.
- Multiple agent modes and permission shapes are first-class.

Interpretation:

Your planner can route and constrain execution, but it still needs to evolve into a genuinely native planner that decides when to explore, ask, edit, verify, pause, or hand off.

### 4. Session Productization Gap

Your system is strong on persistence and recovery, but not yet as mature in general interactive session productization.

Current strengths:

- Resume contracts.
- Scratchpad and memory traces.
- Externalized runtime artifacts.
- Governance and evidence surfaces.

OpenCode maturity:

- Heavier session lifecycle implementation.
- More developed token/cost/session metadata model.
- Richer message/session UX layers.
- More complete compaction, summary, revert, share, and agent/session state handling.

Interpretation:

You are ahead on control-plane accountability, but behind on broad session-product completeness.

### 5. Agent Ecosystem Gap

This is one of the biggest remaining differences.

Current state:

- Your architecture clearly wants native-agent plus external hot-pluggable-agent coexistence.
- But that coexistence has not yet fully hardened into one unified adapter ecosystem.

OpenCode maturity:

- Clear multi-agent modes.
- Tool registry and plugin loading.
- Permission model attached to agent mode.
- Subagent support.

Interpretation:

You have the right direction, but not yet the same degree of ecosystem completeness.

## Where This Project Is Already Stronger

This project has important advantages that should shape the roadmap:

- Governance is first-class, not bolted on.
- Approval, evidence, recovery, provenance, and externalized state are central design elements.
- The control plane is the product core, not an afterthought.
- Native and external coding agents can be framed as interchangeable execution kernels under one governance layer.

This is strategically important. If the goal is not to clone `opencode`, but to build the best coding agent for this control-plane architecture, then your current foundation is unusually strong.

## Practical Maturity Summary

Use this as the short judgment:

- As a governance-first agent system: already strong and differentiated.
- As a native coding-agent prototype: credible and real.
- As a mature, general coding-agent product comparable to `opencode`: still notably behind.

The current difference is best described as:

- not a 0-to-1 gap,
- but a gap between “governed native execution kernel” and “fully productized general coding-agent platform.”

## Recommended Priority Roadmap

### P0

Expand the native tool surface so the agent can work more like a real coding agent:

- stronger read/search/glob flows
- structured patching
- richer verification actions
- safer but more expressive edit operations

### P1

Replace the compatibility-heavy planner with a genuinely native planner that can decide:

- when to explore
- when to clarify
- when to edit
- when to verify
- when to pause for approval
- when to hand off to an external agent

### P2

Unify native-agent and external-agent execution behind one adapter contract:

- first-party native coding agent
- third-party coding agent adapters
- shared governance, evidence, approval, and recovery semantics

## Goal-Mode Short Form

Suggested short goal text:

Assess how far the repository has progressed from external coding-agent governance into a native coding agent, compared with `research_repos/opencode/`. Focus on capability gaps in tooling depth, repo understanding, planner maturity, session productization, and native/external-agent interoperability. Write the concise conclusion in the goal output, and use `docs/process/goal-mode-native-agent-gap.md` as the detailed reference.

## Stopping Criteria

Stop once all of the following are complete:

1. The current repository has been assessed against `research_repos/opencode/` across exactly five dimensions:
   - tooling depth
   - repository understanding
   - planner maturity
   - session productization
   - native/external-agent interoperability
2. A concise overall maturity judgment has been produced for the current repository.
3. The output clearly identifies:
   - current strengths
   - main gaps
   - the top 3 highest-leverage next steps
4. The result is written as an assessment and roadmap recommendation only.
5. No implementation work, code edits, architecture redesign, or iterative micro-optimization is attempted beyond the assessment.

If these five conditions are satisfied, the goal is complete and should stop.

## Acceptance Criteria

The goal output is acceptable only if it includes all of the following:

1. A direct comparison target:
   - `research_repos/opencode/`
2. A bounded conclusion:
   - a short maturity judgment such as early / mid / strong-in-governance but behind-in-general-agent-productization
3. A five-dimension gap summary:
   - one short finding per required dimension
4. A strengths section:
   - at least 2 concrete strengths already present in this repository
5. A gap section:
   - at least 3 concrete capability gaps
6. A prioritized next-step section:
   - exactly 3 next steps labeled `P0`, `P1`, and `P2`
7. An explicit non-goal statement:
   - this assessment does not attempt to fully match all of `opencode`, and does not continue into unlimited refinement once the bounded comparison is complete

## Anti-Optimization Guardrail

To avoid infinite local optimization, do not continue refining once:

- the five required dimensions have all been covered,
- the overall judgment is clear,
- `P0` / `P1` / `P2` have been named,
- and no new comparison dimension is being added.

Do not expand into:

- exhaustive file-by-file audits
- speculative redesign of the whole system
- implementation plans below `P0` / `P1` / `P2`
- repeated rewording of the same maturity judgment
