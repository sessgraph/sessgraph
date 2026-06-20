# ADR-0005: P1 Async Job / Timer 语义

> 状态: Accepted
> 日期: 2026-06-20
> 相关任务: PR-0011 / `docs/tasks/T-0013-async-job-timer-adr.md`

## 背景

P0 已证明本地 durable Session runtime 的核心闭环。第二阶段 / P1 需要让 Session 能被 timer 或 async job result 再次唤醒，但仍必须保持本地、确定性、provider-independent，不引入真实 queue、database、worker、server 或 cloud。

本 ADR 先定义公开 runtime 语义，后续 PR-0012 / PR-0013 再分别实现 InMemory timer flow 和 InMemory async job flow。

任务规格中有三个实现前开放问题：

1. Timer 是否只由 runtime 内部 store 管理，还是也需要 Decision kind 表达 model 请求 timer？
2. Async job 是否需要新增 Decision kind，还是先通过 tool result / external Signal 语义表达？
3. Job failure 是否统一作为数据化 `job_result` Signal，还是要新增 failed Session 状态转移？

## 决策

1. P1 timer 由 runtime-side InMemory timer store 管理，不新增 timer Decision kind。
2. Timer 到期时由 deterministic dispatcher 将 TimerRecord 转换为普通 `Signal(signal_type="timer")` 并 enqueue 到 Session inbox。
3. Timer Signal payload 至少包含 `timer_id`、`reason` 和 JSON object `data`；Signal 使用确定性 `signal_id` 和 `idempotency_key` 支持重复 due scan 去重。
4. Timer 激活复用现有 Activation Runner 语义：Runner 处理 `timer` Signal 时记录现有 `signal_received` / `decision_produced` Event，并保存 Checkpoint；P1 不新增 timer 专用 Event 作为必需字段。
5. Async job 需要新增 `DecisionKind.SUBMIT_JOB`，payload 至少包含非空 `job_type` 和 JSON object `arguments`，可选 `idempotency_key`。
6. Runtime 接受 `submit_job` Decision 后只创建 JobRecord，不同步执行 job；Session 回到 `idle`，等待后续 `job_result` Signal。
7. InMemory job store 表达最小状态：`submitted`、`running`、`succeeded`、`failed`。状态只能按已定义顺序前进，不能直接修改 Session。
8. Runtime 记录 `job_submitted` Event；job 完成并回灌 Signal 时记录 `job_result_enqueued` Event；后续 activation 仍会记录现有 `signal_received` / `decision_produced` Event。
9. Job completion 统一转换为普通 `Signal(signal_type="job_result")`。payload 至少包含 `job_id`、`ok`、`output` 和 `error`；`ok=false` 表示 job failure。
10. Job failure 是数据化结果，不自动将 Session 置为 `failed`。只有 runtime 无法维持自身不变量时才使用 Session `failed` 状态；业务或 job 失败由 model 在下一次 activation 中决定如何处理。
11. Job id、job result signal id、timer signal id 和新增 event id 均必须可确定，P1 不使用随机数。
12. P1 仍只实现 InMemory stores、FakeModel 和 deterministic tests；真实 worker、queue、database、retry policy、timeout policy、provider adapter 和 server integration 后续单独立项。

## 理由

- Timer 可以先作为外部/宿主 runtime 调度机制，不需要立刻扩展 model Decision 协议；这样 PR-0012 可以聚焦 “due timer -> Signal -> Session activation”。
- Async job 与同步 tool 不同：job 会跨 activation 完成，因此需要 `submit_job` Decision 明确表达 model 请求 runtime 分发异步工作。
- `job_result` 和 `timer` 都建模为 Signal，保持 “Signal 是唯一外部激活边界”。
- Job failure 数据化可以避免 tool/job 失败直接污染 Session lifecycle；model 可以基于 `job_result` 决定重试、询问用户或 final_answer。
- P1 不引入真实队列和 worker，避免 runtime core 在语义未稳定前耦合生产基础设施。

## 后果

- PR-0012 可以不修改 DecisionKind，只实现 TimerRecord、InMemory timer store、due scan 和 timer Signal enqueue。
- PR-0013 需要扩展公开 Decision 协议，增加 `DecisionKind.SUBMIT_JOB` 及 payload 校验。
- `job_submitted` 和 `job_result_enqueued` 会成为新的 Event type；后续变更必须更新 ADR 和测试。
- P1 仍不能声称具备生产调度能力；它只证明本地调度语义和恢复边界。
- 如果未来需要 model 主动设置 timer，需要新增单独 ADR 扩展 timer Decision 或通用 scheduling Decision。

## 备选方案

| 方案 | 为什么没有选择 |
| --- | --- |
| Timer 也新增 Decision kind | 当前没有第一个真实调用方要求 model 主动 sleep/schedule；会扩大 PR-0012 协议面。 |
| Async job 只通过 external Signal 表达 | 无法表达 model 请求 runtime 分发异步工作的边界，会弱化 Decision 协议。 |
| Job failure 直接置 Session `failed` | job 失败通常是业务数据或可恢复结果，不应等同 runtime 不变量失败。 |
| 在 P1 引入真实 queue/worker | 违反第二阶段本地确定性边界，且会把 core 过早耦合到基础设施。 |

## 迁移说明

- P0 现有对象和测试不需要迁移。
- PR-0013 增加 `submit_job` Decision kind 时，必须补充 core model、FakeModel、Activation Runner 和 job store 的确定性测试。
- 现有 `tool_call` 语义保持同步执行，不被 async job 取代。

## 关联

- PR: PR-0011
- Task: `docs/tasks/T-0013-async-job-timer-adr.md`
- 后续任务: `docs/tasks/T-0014-inmemory-timer-flow.md`、`docs/tasks/T-0015-inmemory-async-job-flow.md`
