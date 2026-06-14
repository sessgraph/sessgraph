# T-0005: 实现 P0 InMemory stores

> 状态: 已完成
> PR: PR-0003
> 最近更新: 2026-06-14

## 目标

实现 P0 所需的本地、确定性 InMemory stores，为后续 Activation Runner 提供 durable Session runtime 的最小存储边界。

## 范围

范围内：

- `InMemorySessionStore`。
- `InMemoryInboxStore`。
- `InMemoryEventStore`。
- `InMemoryCheckpointStore`。
- store 层错误类型。
- 针对幂等、append-only、乐观并发和快照隔离的确定性单元测试。

范围外：

- Activation Runner 行为。
- FakeModel adapter。
- Tool execution。
- Wait/resume。
- Provider integrations。
- Database、queue、file persistence 或 cloud backend。
- Parent/child Session 编排。

## 存储语义

- `SessionStore` 负责按 `session_id` 保存 Session，并用 `expected_revision` 做乐观并发校验。
- `InboxStore` 负责按 Session 保存 pending Signal，并通过 `signal_id` 和可选 `idempotency_key` 处理外部重试。
- `EventStore` 负责 append-only Event Log，校验同一 Session 内 `sequence` 必须从 0 开始连续递增。
- `CheckpointStore` 负责按 `checkpoint_id` 保存 Checkpoint，并可读取同一 Session 的最新 Checkpoint。
- 所有 store 返回对象快照，不暴露内部存储引用。

## 验证

- Session create/update/get/list 测试。
- Inbox enqueue/list/pop 和幂等冲突测试。
- Event append-only、sequence gap、重复 append 测试。
- Checkpoint save/get/latest 测试。
- 不使用网络、API key、数据库或真实 model 调用。

## 完成记录

- 新增 `src/sessgraph/stores.py`，实现四个 InMemory stores 和 store 错误类型。
- 新增 `tests/test_inmemory_stores.py`，覆盖 store 行为和边界条件。
- 更新 public exports，暴露 P0 InMemory stores。
