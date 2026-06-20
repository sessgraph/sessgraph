# T-0013: ADR 定义 async job/timer 语义

> 状态: 已完成
> PR: PR-0011
> 最近更新: 2026-06-20

## 目标

在实现 timer 或 async job 之前，先定义第二阶段的公开 runtime 语义，明确 Signal、Event、Decision、Checkpoint 和 store 边界。

## 范围

范围内：

- 新增 async job/timer ADR。
- 定义 timer 如何以 Signal 唤醒 Session。
- 定义 async job submitted/running/succeeded/failed 的最小状态边界。
- 定义 job result 如何以 Signal 回灌 Session。
- 定义需要新增的 Event 类型和 Checkpoint 内容边界。
- 明确 P1 仍然只使用 InMemory 和 deterministic tests。

范围外：

- 不实现 runtime 代码。
- 不新增真实 queue、database、worker、server 或 cloud。
- 不新增 provider adapter。
- 不实现 approval/auth。
- 不实现 parent/child session。

## 实现前问题

1. Timer 只由 runtime-side InMemory timer store 管理；P1 不新增 timer Decision kind。
2. Async job 需要新增 `DecisionKind.SUBMIT_JOB`，因为 model 需要表达 runtime 分发异步工作的请求。
3. Job failure 统一作为数据化 `job_result` Signal，不自动将 Session 置为 `failed`。

## 验证

- ADR review。
- 队列和后续任务范围与 ADR 保持一致。

## 完成记录

- 新增 `docs/adr/0005-async-job-timer-semantics.md`。
- 明确 timer 通过 `timer` Signal 唤醒 Session，不新增 timer Decision kind。
- 明确 async job 通过 `submit_job` Decision 创建 JobRecord，并通过 `job_result` Signal 回灌 Session。
- 明确 `job_submitted` / `job_result_enqueued` Event 边界。
- 明确 P1 仍只使用 InMemory stores、FakeModel 和 deterministic tests。
