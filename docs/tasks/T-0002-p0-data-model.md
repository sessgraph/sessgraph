# T-0002: 定义 P0 核心数据结构

> 状态: 已完成
> PR: PR-0002
> 最近更新: 2026-06-12

## 目标

定义最小 P0 数据结构，让 SessGraph 成为 durable Session runtime，而不是业务应用框架。

## 范围

范围内：

- AgentDefinition。
- Session。
- Signal。
- Event。
- Decision。
- Checkpoint。
- 针对构造、校验和序列化的确定性单元测试。

范围外：

- Activation Runner 行为。
- Tool execution。
- Wait/resume。
- InMemory stores。
- Provider integrations。
- Database/web/cloud 代码。
- Parent/child Session 编排。

## 架构约束

- Session 是 durable state center。
- Signal 是唯一外部触发边界。
- Event 是 append-only fact record。
- Checkpoint 是恢复边界。
- Model output 以 Decision 对象表示。
- 数据结构必须与 provider 解耦，并且测试必须确定性。

## 实现决策

1. P0 core data structures 使用 Python 3.12 和标准库 `dataclasses`，不引入 Pydantic。
2. Event 和 Checkpoint 的初始公开序列化格式是带 `schema_version: 1` 的 JSON-compatible dict。
3. Signal 使用 `signal_id` 和可选 `idempotency_key` 支持外部重试去重；Event 使用 `event_id`、`sequence` 和可选 `source_signal_id` 支持事实唯一性、Session 内排序和因果追踪。唯一性 enforcement 留给后续 store/runtime。

上述决策记录在 `docs/adr/0001-p0-core-data-model.md`。

## 验证

- 有效和无效对象构造的单元测试。
- 如果本 PR 包含序列化，则加入序列化 round-trip 测试。
- 不使用网络、API key、数据库或真实 model 调用。

## 完成记录

- 新增 `src/sessgraph/core.py`，定义 `AgentDefinition`、`Session`、`Signal`、`Event`、`Decision`、`Checkpoint`。
- 新增 `src/sessgraph/__init__.py`，导出 P0 core data structures。
- 新增 `tests/test_core_models.py`，覆盖构造校验、序列化 round-trip、严格 JSON payload、timezone-aware datetime 和 final_answer Decision 校验。
- 新增 `Makefile` 的 `make check` 入口，默认使用 `python3.12` 和标准库 `unittest`，不新增外部依赖。
