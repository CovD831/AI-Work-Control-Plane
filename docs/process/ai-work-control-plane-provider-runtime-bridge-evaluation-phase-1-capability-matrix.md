# AI Work Control Plane Provider Runtime Bridge Evaluation Phase 1: Capability Matrix

## Goal

Record the currently observed provider/runtime capabilities so a later adapter contract can be drafted from evidence rather than aspiration.

## Capability Legend

- `supported`: implemented locally or exposed by current CLI help.
- `observed`: visible as local metadata or command behavior, but not a durable provider contract.
- `records_only`: AI-Work-Control-Plane can record the fact, but does not control provider behavior.
- `placeholder`: field exists but no trustworthy provider value is available.
- `unavailable`: not exposed by the current runtime path.
- `unknown`: not evaluated yet.

## Runtime Matrix

| Runtime | Start | Resume | Send | Cancel | Status | Logs | Artifact | Session Ref | CWD / Workspace | Exit Code | Usage / Cost | Permission Model | Structured Output |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `FileJobRuntime` / mock | supported | unavailable | supported records_only | supported records_only | supported | supported local log | records_only job JSON/log | generated local ref | supported from request | placeholder unless completed manually | placeholder | request sandbox only | job JSON |
| `CommandJobRuntime` | supported | unavailable | observed if live session, otherwise fallback/file behavior | observed if live session, otherwise fallback/file behavior | supported | supported stdout/stderr/log | records_only job JSON/log | observed local session ref | supported from request | supported when command exits | placeholder unless parsed payload reports usage | request sandbox plus provider CLI behavior | adapter parsed payload |
| `CodexCliAdapter` | supported via `codex exec` | CLI exposes `resume`; adapter does not own it | adapter delegates only to live process session | adapter delegates only to live process session | records_only through command runtime | stdout/stderr capture | stdout/stderr payload | local process session ref, not provider-owned | CLI supports `--cd`; adapter currently uses process cwd/request cwd | supported when process exits | placeholder | CLI sandbox options observed | stdout/stderr payload; `codex exec --json` exists but adapter does not consume it yet |
| `ClaudeCodeAdapter` | supported via `claude -p --output-format json` | CLI exposes `--resume`, `--continue`, `--session-id`; adapter does not own them | adapter delegates only to live process session | adapter delegates only to live process session | records_only through command runtime | stdout/stderr capture | JSON envelope payload | local process session ref, not provider-owned | CLI supports cwd/worktree/add-dir options; adapter currently uses process cwd/request cwd | supported when process exits | placeholder unless JSON envelope exposes usage in the future | CLI permission/tool options observed | JSON envelope |
| `DirectApiJobRuntime` | supported single-turn fakeable client | unavailable | unsupported | unsupported | supported job record | supported job payload | parsed payload | generated local ref | request cwd only | placeholder | placeholder unless API client reports usage | env-key readiness only | direct API payload |
| `TmuxJobRuntime` | supported local tmux wrapper | observed through tmux session naming | supported local tmux send | supported local tmux cancel | supported local tmux/status wrapper | tmux/log behavior | records_only | tmux session ref | local cwd/session | placeholder/observed by wrapper | placeholder | tmux/local shell policy | job JSON/log |
| Codex CLI local capability | supported: `codex exec` | supported by CLI: `codex resume`, `codex exec resume` | unknown for non-interactive bridge | unknown for non-interactive bridge | observed through process result; remote-control/app-server exists but not evaluated | stdout/json events with `codex exec --json` | last-message output via `-o`; apply/review commands exist | CLI session ids are provider-owned | `-C/--cd`, `--add-dir`, sandbox flags | process exit code | unknown | sandbox and approval flags observed | `codex exec --json`, output schema |
| Claude Code local capability | supported: `claude -p` | supported by CLI: `--resume`, `--continue`, `--session-id`, `--fork-session` | observed possibilities: stream-json input and background agents; not adapter-owned | unknown for non-interactive bridge; agents command is inspectable | `claude agents --json` exposes live sessions; not yet integrated | debug files, stream-json, stdout/stderr | JSON/stream-json output, debug logs | provider-owned session id options | `--add-dir`, `--worktree`, settings, permission mode | process exit code | budget flag observed, actual usage not evaluated | permission mode, tools, allowed/disallowed tools | `--output-format json` and `stream-json` |

## Observed CLI Evidence

Codex CLI:

- Version: `codex-cli 0.133.0-alpha.1`.
- Top-level commands include `exec`, `review`, `resume`, `fork`, `mcp`, `plugin`, `doctor`, `remote-control`, `app-server`, `exec-server`, and `apply`.
- `codex exec` supports non-interactive runs, `--json`, `--output-schema`, `--output-last-message`, `--cd`, `--add-dir`, sandbox flags, approval flags, `--ephemeral`, `--ignore-user-config`, and `--ignore-rules`.
- `codex resume` supports session id or `--last`, with `--include-non-interactive`.

Claude Code:

- Version: `2.1.152 (Claude Code)`.
- Top-level options include `--print`, `--output-format json|stream-json`, `--input-format stream-json`, `--resume`, `--continue`, `--session-id`, `--fork-session`, `--permission-mode`, `--allowedTools`, `--disallowedTools`, `--add-dir`, `--worktree`, `--max-budget-usd`, and `--no-session-persistence`.
- `claude agents --json` can print live background sessions for scripting.

## Risks And Gaps

- Existing `CommandJobRuntime` uses local process sessions, not provider-native session ownership.
- Codex and Claude both expose resume/session concepts, but the current adapters do not persist or drive provider-native continuation semantics.
- Send/cancel currently mean local process/session operation receipts unless a future adapter proves provider-native support.
- Usage/cost must remain placeholder until a runtime reports trustworthy values.
- Live provider calls are too environment-dependent to be mandatory test gates.

## Phase 1 Result

This matrix is the evidence base for Phase 2 ownership boundaries and Phase 3 adapter contract drafting.

