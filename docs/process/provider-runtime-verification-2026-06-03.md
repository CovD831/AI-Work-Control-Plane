# Provider / Runtime 真实验证记录（2026-06-03）

## 目的

验证当前仓库的 provider/runtime 层是否已经具备以下能力：

1. 识别本机 `codex` / `claude` CLI binary
2. 通过仓库的 provider health 机制报告本地可用性
3. 通过底层 `CommandJobRuntime` 真实启动本地 provider 命令
4. 记录真实执行结果、失败原因和 runtime measurement

本次验证重点是**真实本机 CLI 路径**，不是 fake runner 或 mock session 测试。

## 验证环境

- 日期：2026-06-03
- 仓库根目录：`/Users/abab/Desktop/AI-Work-Control-Plane`
- `codex` binary：`/Users/abab/.nvm/versions/node/v24.14.0/bin/codex`
- `claude` binary：`/opt/homebrew/bin/claude`

## 已验证结论

### 1. provider health 已真实可用

运行：

```bash
PYTHONPATH=src python -m agent_orchestrator.cli health --refresh --format json
```

结果：

- `codex` 被识别为可用，版本 `codex-cli 0.134.0`
- `claude` 被识别为可用，版本 `2.1.63 (Claude Code)`
- `direct_api` 鉴权未配置，`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` 均为 `auth_required`

结论：

- provider health 不是纯 mock，已经能真实检查本机 binary 和版本信息

### 2. `CommandJobRuntime` 已能真实启动本地 provider 命令

本次没有只停留在 `health`，而是直接调用底层 `CommandJobRuntime` 启动 job。

#### Codex CLI

真实构造出的命令形态：

```text
codex exec --model gpt-5.4 --sandbox workspace-write <rendered prompt>
```

结果：

- job 成功启动
- 记录了 `session_id`、`thread_id`、`pid`
- 记录了 `runtime_measurement`
- 最终失败

失败原因：

- `~/.codex/state_5.sqlite` 写入失败：`attempt to write a readonly database`
- 当前目录不是 trusted directory，且未指定 `--skip-git-repo-check`

结论：

- `codex` provider 层**已经真实接上**
- 当前不是“没有调用到 codex CLI”，而是“调用到了，但执行被本地环境/权限边界拦住了”

#### Claude Code CLI

真实构造出的命令形态：

```text
claude -p --output-format json --model sonnet <rendered prompt>
```

结果：

- job 成功启动
- 记录了 `session_id`、`thread_id`、`pid`
- 记录了 `runtime_measurement`
- 进程退出码为 `0`
- job 被当前适配器判定为 `completed`

但 stdout 中的 JSON envelope 带有 `subtype: "error_during_execution"`，并包含多条错误：

- 无法在 `~/.claude/plugins/...` 下创建 marketplace 目录
- 无法写入 `~/.claude/debug/...`

结论：

- `claude` provider 层**已经真实接上**
- 但当前解析逻辑主要依赖 `exit_code` 和 `is_error`，没有把 `subtype=error_during_execution` 视为失败
- 因此当前存在一个真实边界：**Claude Code 发生执行期错误时，仓库可能把它误记为 completed**

## 额外发现

### 1. 上层 `cli run --runtime command --provider ...` 路径没有按预期落到 command runtime

本次验证中，运行：

```bash
PYTHONPATH=/Users/abab/Desktop/AI-Work-Control-Plane/src python -m agent_orchestrator.cli run "Reply with exactly: provider verification ok" --runtime command --provider codex --mode success_first
```

返回结果里的 `execution_contract.provider_recommendation.runtime` 仍然是 `mock`，且 run 很快失败在：

```text
Rescue jobs require a failure_reason.
```

结论：

- 上层 `run` 路径当前不能作为 provider/runtime 已打通的证据
- provider 层验证应优先看底层 `CommandJobRuntime`
- 需要后续单独排查 orchestration 层是否正确传递了 `--runtime command`

### 2. 当前真实问题更多是“环境边界”和“错误语义判定”，而不是“provider 层不存在”

本次验证后，更准确的说法应该是：

> provider/runtime 层已经具备真实 CLI 接入能力，但在真实执行中仍存在环境权限边界，以及 Claude 结果判定语义不够严格的问题。

## 当前最准确的项目表述

不建议再说：

> provider 层已经完整跑通

建议改成：

> provider/runtime 层已经完成真实 CLI 接入与基础验证，`codex` / `claude` 均可被本地 runtime 启动并记录测量数据；但真实执行仍暴露出环境权限边界，以及部分 provider 结果语义尚未完全收紧。

## 后续建议

1. 为 `codex` 增加 trusted directory / state path 相关处理策略
2. 为 `cli_isolated` 模式补一轮真实 provider 验证
3. 收紧 `ClaudeCodeAdapter.parse_result`，把 `error_during_execution` 识别为失败
4. 排查 `cli run --runtime command` 为什么没有真正落到 command runtime
