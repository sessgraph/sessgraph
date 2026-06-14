# 产品 PR 队列

> 状态: 当前
> 最近更新: 2026-06-14

本文件是可独立 review 的产品工作的权威队列。每个 PR 都应足够小，可以作为一个连贯变更被 review 和测试。

## 队列

| ID | 状态 | 标题 | 任务规格 | 范围 | 验证方式 |
| --- | --- | --- | --- | --- | --- |
| PR-0001 | 已完成 | 建立规划与 AI 治理文件 | `docs/tasks/T-0001-bootstrap-governance.md` | 仅 docs/state；不实现 runtime | Markdown/文件一致性检查；git diff review |
| PR-0001F | 已完成 | 处理规划 review 意见并新增中文统一流程 | `docs/tasks/T-0003-review-planning-files.md` | 仅 docs/process/index/ADR/OpenAPI 占位；不实现 runtime | Markdown/文件一致性检查；git diff review |
| PR-0001G | 已完成 | 将 agent 指令和规划文档统一为中文 | `docs/tasks/T-0004-localize-agent-docs.md` | root agent 指令、README、docs/state、docs/tasks 的中文化；不实现 runtime | Markdown/文件一致性检查；git diff review |
| PR-0002 | 已完成 | 定义 P0 核心数据结构 | `docs/tasks/T-0002-p0-data-model.md` | AgentDefinition、Session、Signal、Event、Decision、Checkpoint 数据类型和测试 | 构造、校验、序列化单元测试 |
| PR-0003 | 已完成 | 实现 InMemory stores | `docs/tasks/T-0005-p0-inmemory-stores.md` | SessionStore、InboxStore、EventStore、CheckpointStore | 包含幂等性的确定性 store 测试 |
| PR-0004 | 已完成 | 构建最小 Activation Runner 循环 | `docs/tasks/T-0006-p0-activation-runner.md` | FakeModel + final_answer Decision + basic example | 单元测试和 example smoke test |
| PR-0005 | 已完成 | 增加同步 tool execution flow | `docs/tasks/T-0007-sync-tool-execution.md` | ToolSpec、ToolRegistry、SyncToolExecutor | Tool 成功/失败测试 |
| PR-0006 | 已完成 | 增加 wait/resume user flow | `docs/tasks/T-0008-wait-resume-user-flow.md` | ask_user Decision 和 user_message Signal resume | waiting/resume 测试 |

## PR-0001 / PR-0001F / PR-0001G 完成记录

- `docs/state/` 包含当前项目状态、项目边界、队列、行动项、风险、inbox 和维护指南。
- 初始任务规格已覆盖治理 bootstrap、第一个 P0 data-model 工作、中文统一流程补齐和中文文档本地化修正。
- README 指向状态文件和开发流程。
- 根目录 `AGENTS.md` 和 `CLAUDE.md` 记录 AI 协作约束，并已改为中文。
- `docs/DEVELOPMENT_PROCESS.md` 记录中文统一开发流程。
- `docs/README.md` 索引文档表面。
- `docs/adr/0000-template.md` 和 `docs/openapi/README.md` 保留架构决策与契约事实源位置。
- 规划/bootstrap 变更均以文档提交完成。

## PR-0002 完成记录

- 新增 P0 core data structures：`AgentDefinition`、`Session`、`Signal`、`Event`、`Decision`、`Checkpoint`。
- 新增 ADR-0001，记录 Python 3.12、dataclasses、JSON-compatible `schema_version: 1`、Signal/Event 幂等字段和 Checkpoint 恢复边界。
- 新增标准库 `unittest` 覆盖构造校验、序列化 round-trip 和严格 JSON payload。
- 未实现 Activation Runner、InMemory stores、tool execution、wait/resume、provider integration、database 或 server mode。

## PR-0003 完成记录

- 新增 `InMemorySessionStore`、`InMemoryInboxStore`、`InMemoryEventStore`、`InMemoryCheckpointStore`。
- Store 层覆盖 Session revision 乐观并发、Signal idempotency、Event append-only sequence 和 Checkpoint latest lookup。
- 新增标准库 `unittest` 覆盖 store 行为和边界条件。
- 未实现 Activation Runner、FakeModel、tool execution、wait/resume、provider integration、database 或 server mode。

## PR-0004 完成记录

- 新增 `ActivationRunner`、`ActivationContext`、`ActivationResult` 和 `FakeModel`。
- Runner 支持一个 pending Signal 激活一次 Session，分发 `final_answer` / `noop` Decision，记录 `signal_received` / `decision_produced` Event，并保存 Checkpoint。
- 新增 ADR-0002，记录 P0 Activation Runner 最小循环语义。
- 新增 `examples/basic_session.py` 和 example smoke test。
- 未实现 tool execution、wait/resume、async job/timer、provider integration、database 或 server mode。

## PR-0005 完成记录

- 新增 `DecisionKind.TOOL_CALL`、`ToolSpec`、`ToolRegistry`、`SyncToolExecutor` 和 `ToolResult`。
- Runner 支持同步分发 `tool_call` Decision，记录 `tool_call_requested` / `tool_result_produced` Event，并将 ToolResult 回灌为 `tool_result` Signal。
- 新增 ADR-0003，记录同步 tool execution 语义。
- 新增标准库 `unittest` 覆盖工具注册、成功执行、失败结果、未知工具和 runner tool flow。
- 未实现 wait/resume、async job/timer、approval/authorization、provider integration、database 或 server mode。

## PR-0006 完成记录

- 新增 `DecisionKind.ASK_USER` 和 ask_user payload 校验。
- Runner 支持 `ask_user` Decision，将 Session 置为 `waiting` 并保存 Checkpoint。
- `user_message` Signal 可恢复 waiting Session 并继续 activation。
- 新增 ADR-0004，记录 P0 wait/resume user flow 语义。
- 新增标准库 `unittest` 覆盖 ask_user、waiting inactive 和 user_message resume。
- 未实现 UI、timeout/timer、approval/authorization、provider integration、database 或 server mode。

## 队列纪律

- 一个 PR 只实现一个切片。
- 如果切片触及公开协议语义，先新增或更新 ADR。
- 如果 PR 预计超过约 800 行变更，先拆分再实现。
