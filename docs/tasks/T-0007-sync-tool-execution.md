# T-0007: 增加同步 tool execution flow

> 状态: 已完成
> PR: PR-0005
> 最近更新: 2026-06-14

## 目标

为 P0 runtime 增加同步 tool execution flow，让 model 可以返回 `tool_call` Decision，由 runtime 校验并调用本地注册工具，再把 tool result 作为 Signal 回灌到 Session inbox。

## 范围

范围内：

- `DecisionKind.TOOL_CALL`。
- `ToolSpec`。
- `ToolRegistry`。
- `SyncToolExecutor`。
- `ToolResult`。
- Activation Runner 对 `tool_call` 的同步分发。
- tool call / tool result Event 记录。
- tool result Signal 回灌。
- 工具成功、工具失败、未知工具和 runner 分发测试。

范围外：

- async job/timer。
- wait/resume user flow。
- tool authorization / approval。
- provider integration。
- database、queue、server 或 cloud backend。
- 多工具并行和复杂 tool schema validation。

## Runtime 语义

- Model adapter 仍然只产出 Decision。
- `tool_call` Decision payload 必须包含非空 `tool_name` 和 JSON object `arguments`。
- Runtime 通过 `SyncToolExecutor` 调用 `ToolRegistry` 中的本地工具。
- Tool 只能返回 JSON-compatible object；不能直接修改 Session、Event Log 或 Checkpoint。
- Tool 执行成功或失败都会生成 `ToolResult`。
- Runner 会记录 `tool_call_requested` 和 `tool_result_produced` Event。
- Runner 会把 `ToolResult` 转换为 `tool_result` Signal 并 enqueue 到 inbox，供后续 activation 处理。

## 验证

- ToolRegistry 注册、重复注册和未知工具测试。
- SyncToolExecutor 成功和失败测试。
- `tool_call` Decision 构造校验测试。
- ActivationRunner tool_call 分发和 tool_result Signal 回灌测试。
- 不使用网络、API key、数据库或真实 model 调用。

## 完成记录

- 新增 `src/sessgraph/tools.py`。
- 扩展 `DecisionKind.TOOL_CALL` 及 payload 校验。
- 扩展 `FakeModel` 支持 deterministic tool_call。
- 扩展 `ActivationRunner` 支持同步 tool execution。
- 新增 `tests/test_tools.py`。
