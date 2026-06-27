# T-0029: Child result Signal flow

> 状态: 待开始
> PR: PR-0027
> 最近更新: 2026-06-27

## 目标

基于 ADR-0009 和 PR-0026，实现 Child Session terminal result 通过普通 `child_result` Signal 回灌 Parent 的最小 InMemory flow。该任务只覆盖 child result delivery，不实现独立 reducer DSL、shared memory 或 capability delegation。

## 范围

范围内：

- 扩展 `ChildSessionRecord` lifecycle，支持 `completed` / `failed` terminal 状态、result payload、deterministic terminal transition 和待回灌查询。
- 新增 runtime-side dispatcher，将 terminal Child relationship 转换为普通 `Signal(signal_type="child_result")` enqueue 到 Parent inbox，并追加 `child_result_enqueued` Event。
- Parent 被 `child_result` Signal 唤醒后复用现有 Activation Runner、Context、Event 和 Checkpoint 语义。
- 覆盖 deterministic tests：completed/failed result 回灌、duplicate enqueue idempotency、Event append-only、Parent activation 处理 `child_result`。

范围外：

- 不实现独立 reducer DSL 或 reducer-specific Decision kind。
- 不自动把 Child output 合并进 Parent business state。
- 不实现 shared memory、cross-session context、capability delegation 或 approval delegation。
- 不实现 Child cancellation、timeout、fan-out/fan-in helper API。
- 不引入真实 worker、queue、database、server、provider、GUI 或 cloud。

## 依赖

- PR-0025 / ADR-0009 已完成并 accepted。
- PR-0026 / T-0028 InMemory child session creation flow 已完成。

## 验证

- `make check`。
- 新增 child result dispatcher 单元测试和 Parent activation 集成测试。
- 不发起真实网络调用或真实 LLM 调用。
