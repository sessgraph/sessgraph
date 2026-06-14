# ADR-0003: P0 同步 Tool Execution

> 状态: Accepted
> 日期: 2026-06-14
> 相关任务: PR-0005 / `docs/tasks/T-0007-sync-tool-execution.md`

## 背景

PR-0004 已实现最小 Activation Runner，但只支持 `final_answer` 和 `noop`。PR-0005 需要让 runtime 可以分发同步工具调用，同时保持 P0 本地、确定性、provider-independent，不引入真实网络、数据库、queue 或外部依赖。

## 决策

1. 新增 `DecisionKind.TOOL_CALL`，payload 必须包含 `tool_name` 和 JSON object `arguments`。
2. Tool 通过 `ToolSpec` 注册到 `ToolRegistry`。
3. `SyncToolExecutor` 负责调用工具 handler，并把成功或失败统一包装为 `ToolResult`。
4. Tool handler 只能接收 JSON object arguments，返回 JSON object output；不能直接修改 Session、Event Log、Checkpoint 或 inbox。
5. Activation Runner 分发 `tool_call` 时记录 `tool_call_requested` 和 `tool_result_produced` Event。
6. ToolResult 会被转换为 `tool_result` Signal 回灌到同一 Session inbox，供后续 activation 处理。
7. 同步 tool flow 不实现 approval、authorization、async job、timer、wait/resume 或 provider integration。

## 理由

- 将工具执行放在 runtime/executor 层，保持 model adapter 只产出 Decision 的边界。
- ToolResult 回灌为 Signal，复用 “Signal 是唯一外部触发入口” 的核心原则。
- 同步 executor 足够验证 P0 tool dispatch 语义；async job/timer 后续单独立项。

## 后果

- `tool_call` 扩展了公开 Decision 协议，后续修改 payload 字段必须更新 ADR 和测试。
- 当前 tool schema 只做最小 JSON object 校验；复杂 schema validation 后置。
- Tool failure 是数据化结果，不在 executor 中抛出给 runner。
