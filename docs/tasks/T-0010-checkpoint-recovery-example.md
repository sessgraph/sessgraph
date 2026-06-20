# T-0010: 增加 checkpoint recovery example/test

> 状态: 已完成
> PR: PR-0008
> 最近更新: 2026-06-20

## 目标

补齐 P0 “Checkpoint save/load” 的显式恢复验证：在 runner 保存 Checkpoint 后，从 CheckpointStore 读取最新 Checkpoint，并证明其中的 session snapshot 可以恢复为可用的 `Session` 边界。

## 范围

范围内：

- 增加 checkpoint recovery 的确定性测试。
- 如有必要，增加一个很小的 helper 或 example，用于从 `Checkpoint.state["session"]` 恢复 `Session`。
- 验证恢复出的 Session 与 Checkpoint 的 `session_revision`、`event_sequence` 和已记录 Event 边界一致。
- 保持所有数据为 JSON-compatible dict，不改变现有 Checkpoint 公开字段。

范围外：

- 不实现 file persistence、database、queue 或 crash recovery framework。
- 不新增事务系统。
- 不改变 `Checkpoint` 序列化格式。
- 不实现 provider、server、GUI 或 cloud 代码。
- 不实现 async job/timer。

## 验证

- 新增 deterministic unit test 覆盖 latest checkpoint load 和 session recovery。
- `make check` 通过。

## 实现决策

1. 不新增 public helper；P0 直接使用 `Session.from_dict(checkpoint.state["session"])` 验证恢复边界。
2. 新增独立 `examples/checkpoint_recovery.py`，避免扩大 `examples/basic_session.py` 的职责。
3. Checkpoint 公开序列化格式不变，恢复验证只依赖已有 `schema_version: 1` JSON-compatible dict。

## 完成记录

- 新增 `examples/checkpoint_recovery.py`，演示从 latest Checkpoint 恢复 Session snapshot。
- 新增 `tests/test_checkpoint_recovery.py`，覆盖 latest checkpoint load、Session recovery、event boundary 和 Checkpoint round-trip recovery。
- 未新增外部依赖，未实现 file persistence、database、queue、crash recovery framework、provider、server、GUI 或 async job/timer。
