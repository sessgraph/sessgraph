# ADR-0001: P0 核心数据模型与序列化格式

> 状态: Accepted
> 日期: 2026-06-12
> 相关任务: PR-0002 / `docs/tasks/T-0002-p0-data-model.md`

## 背景

PR-0002 需要先定义 `AgentDefinition`、`Session`、`Signal`、`Event`、`Decision`、`Checkpoint`，才能继续实现 InMemory stores、FakeModel 和 Activation Runner。这个切片必须保持 provider-independent，且不能新增数据库、Web server、真实 LLM provider 或外部依赖。

任务规格中有三个实现前开放问题：

1. P0 core data structures 使用 dataclasses 还是 Pydantic？
2. Event 和 Checkpoint 的初始公开序列化格式是什么？
3. Signal ID 和 Event ID 需要哪些字段来支持幂等性？

## 决策

1. P0 使用 Python 3.12 和标准库 `dataclasses`，不引入 Pydantic。
2. 所有 P0 核心对象公开 `to_dict()` / `from_dict()`，序列化结果是 JSON-compatible dict，并带 `schema_version: 1`。
3. 时间字段使用 timezone-aware `datetime`，序列化为 UTC ISO 8601 字符串。
4. `Signal` 包含 `signal_id` 和可选 `idempotency_key`。`signal_id` 是 runtime 事实 ID，`idempotency_key` 用于后续 store 去重外部重试。
5. `Event` 包含 `event_id`、`session_id`、`sequence` 和可选 `source_signal_id`。后续 EventStore 负责校验同一 Session 内 `sequence` 单调追加，以及 `event_id` 唯一。
6. `Checkpoint` 绑定 `session_revision` 和 `event_sequence`，表示恢复点对应的 Session 版本和 Event Log 边界。
7. `Decision` 只表示 model adapter 的输出，不直接执行工具。P0 初始支持 `noop` 和 `final_answer`。

## 理由

- Python 3.12 是当前 P0 的最低运行版本；可以使用现代类型标注和 `dataclass(slots=True)`，但仍避免外部依赖。
- `dataclasses` 足够表达 P0 数据边界，避免在 runtime core 尚未稳定前引入外部依赖和隐式校验语义。
- JSON-compatible dict 是最小可审查格式，能直接被 InMemory store、未来文件快照或数据库 adapter 使用。
- `schema_version` 让后续协议演进有显式分支，而不是依赖隐式字段探测。
- `signal_id`、`idempotency_key`、`event_id`、`sequence`、`source_signal_id` 分别覆盖外部重试、事实唯一性、Session 内排序和因果追踪；唯一性和并发 writer 规则留给 store/runtime 实现。

## 后果

- PR-0002 只提供数据结构和校验，不实现 store、runner、tool execution、wait/resume 或 provider integration。
- 后续如需改变公开字段语义、Decision kind、Event/Checkpoint 序列化格式，必须新增或更新 ADR。
- 如果未来需要更强 schema 或跨语言契约，可以在 runtime 语义稳定后再引入 Pydantic、JSON Schema 或 OpenAPI 文件。
