# ADR-0009: Parent/Child Session 语义

> 状态: Accepted
> 日期: 2026-06-27
> 相关任务: PR-0025 / `docs/tasks/T-0027-parent-child-session-adr.md`

## 背景

SessGraph 已完成本地 durable Session runtime core、async job/timer、Memory + Context，以及 Safety/Auth v0.5 本地确定性闭环。下一块核心编排能力是 Parent/Child Session：一个 Session 可以请求 runtime 创建另一个 Session，并在 Child 完成后通过 durable 边界把结果回灌 Parent。

Parent/Child Session 会触及公开 runtime 语义：Parent 如何请求创建 Child、Child 是否能修改 Parent、Child result 如何回灌、reducer merge 是否需要独立协议、Checkpoint 如何恢复，以及 capability / approval 是否能委派。按照仓库规则，这些生命周期和协议变化必须先 ADR，再实现。

## 决策

1. PR-0025 只定义 Parent/Child Session 语义，不实现 runtime 代码。
2. Parent 通过新的 `DecisionKind.START_CHILD_SESSION` 请求 runtime 创建 Child Session。Model 只能提出请求；创建、校验、授权和记录都由 runtime 执行。
3. `start_child_session` payload 至少包含 `child_agent_id` 和 JSON object `input`，可选 `idempotency_key`、`context_policy` 和 JSON object `metadata`。
4. Runtime 接受该 Decision 后必须创建 durable `ChildSessionRecord`，表达 parent-child relationship。最小字段为 `schema_version`、`child_session_id`、`parent_session_id`、`parent_decision_id`、`parent_signal_id`、`child_agent_id`、`status`、`input`、`metadata`、`idempotency_key`、`created_at`、`completed_at`、`result_signal_id`。`status` 的最小生命周期为 `started` -> `completed` / `failed`；创建 Child Session 并 enqueue `child_start` Signal 后即为 `started`。
5. `child_session_id` 必须确定性生成，建议基于 `parent_session_id`、`parent_decision_id`、`child_agent_id` 和 `idempotency_key`。重复 `start_child_session` 必须按 idempotency 返回同一个 child relationship，不创建重复 Child。
6. 创建 Child 时，runtime 必须为 Child 创建普通 `Session`，并向 Child inbox enqueue 初始 `Signal(signal_type="child_start")`。Signal payload 至少包含 `parent_session_id`、`parent_decision_id`、`input` 和 `metadata`。
7. Parent Event Log 必须追加 `child_session_started` Event。payload 至少包含 `child_session_id`、`parent_decision_id`、`parent_signal_id`、`child_agent_id` 和 `idempotency_key`。
8. Child Session 拥有独立 Event Log、Checkpoint、inbox 和 lifecycle。Child 永远不能直接修改 Parent Session、Parent Event Log、Parent Checkpoint 或 Parent memory。
9. Parent 接受 `start_child_session` 后返回 `idle`，等待未来 `child_result` Signal。Parent 不因 Child pending 自动进入 `waiting`；同一 Parent 可同时存在多个 pending Child。
10. 同一个 Parent 的多个 child result 通过 Parent inbox 串行处理，仍遵守同一 Session 同一时间只有一个 writer 的规则。ordering 以 inbox enqueue 顺序和 Event sequence 为准。
11. Child 完成后，由 runtime-side dispatcher 将 terminal Child relationship 转换为普通 `Signal(signal_type="child_result")` enqueue 到 Parent inbox。Child 不能直接调用 Parent reducer 或写 Parent state。
12. `child_result` Signal payload 至少包含 `child_session_id`、`parent_decision_id`、`status`、JSON object `result`、`completed_at` 和可选 `error`。`result` 是 Child terminal output 的数据化表示；业务失败或子任务失败应作为数据进入 payload，不自动使 Parent failed。
13. child result enqueue 时，runtime 必须追加 `child_result_enqueued` Event。后续 Parent activation 处理 `child_result` 时继续复用现有 `signal_received` / `decision_produced` Event 和 Checkpoint 语义。
14. Parent reducer merge 在第一版中不新增独立 reducer DSL 或 reducer Decision kind。`child_result` 是普通 Signal；Parent model 在下一次 activation 中读取 context 并产出普通 Decision，runtime 按现有规则校验和分发。
15. Runtime 只负责 durable delivery、idempotency、authorization gate、Event 和 Checkpoint，不自动把 Child output 合并进 Parent business state。
16. Parent 和 Child 默认不共享 context、memory、capability grant 或 approval request。Child 初始 context 只来自 `start_child_session` payload 中显式传入的 `input` / `metadata`。
17. 如果未来需要共享 memory、cross-session context、capability delegation 或 approval delegation，必须单独 ADR。首个 Parent/Child 实现不得隐式继承 Parent grant 或 pending approval。
18. `start_child_session` 是需要 Safety/Auth gate 的 action kind。后续实现必须在 Decision schema 校验之后、创建 Child 之前调用 policy gate；hard deny 或 approval-required 行为复用 ADR-0007 / ADR-0008 的 runtime-side boundary。
19. Child 自己发起的 tool/job/child-session 等 action 必须使用 Child Session 的 authorization context 和 grants。Parent grant 不会自动扩大到 Child。
20. Checkpoint state 在 Parent 创建 Child 后必须记录 child relationship metadata，包括 `child_session_id`、`parent_decision_id`、`status`、`idempotency_key` 和 `event_id`。Child 的 Checkpoint 仍只记录 Child 自身恢复状态。
21. child result delivery 必须可恢复：dispatcher 重跑时不能重复 enqueue 相同 `child_result` Signal；已 enqueue 的 `result_signal_id` 必须写回 `ChildSessionRecord` 或可由确定性 id 重建。
22. Child terminal 状态至少包含 `completed` 和 `failed`；`failed` 表示 Child runtime 无法维持自身不变量或 Child action 出现不可恢复 runtime failure。普通业务失败应进入 `result` / `error` payload，而不是直接污染 Parent lifecycle。
23. 首个实现必须保持 InMemory-first、FakeModel 和 deterministic tests；不得引入真实 worker、queue、database、server、provider、GUI、cloud 或复杂 multi-agent graph framework。
24. 后续实现应拆分为小 PR：先实现 InMemory child session creation，再实现 child result Signal 回灌，最后补 checkpoint recovery example/test 或更复杂 fan-out 行为。

## 理由

- 用新的 `START_CHILD_SESSION` Decision 可以清楚表达 model 请求 runtime 创建子任务，同时保持 “model 只产出 Decision，runtime 校验并分发 action”。
- 把 child completion 建模为普通 `child_result` Signal，可以复用现有 durable activation、Event Log、Checkpoint 和 idempotent inbox 机制。
- 不在第一版引入 reducer DSL，可以避免 Parent/Child Session 一次性膨胀成复杂多 Agent 编排框架。
- Parent / Child 默认隔离 context、memory 和 grant，可以守住 Safety/Auth 边界，避免隐式 capability delegation。
- Parent 保持 `idle` 能支持多个 Child 并行完成；真正的串行安全仍由 Parent inbox 和 one-writer invariant 保证。

## 后果

### 正面影响

- 后续可以拆一个小 PR 只实现 InMemory child session creation，不必同时处理 result merge。
- Child result、job result、timer 都统一通过 Signal 唤醒 Session，runtime 概念更一致。
- capability delegation、shared memory 和 reducer framework 保留为明确的后续 ADR，不会混入第一版实现。

### 负面影响 / 代价

- Decision 协议会新增 `START_CHILD_SESSION`，需要更新 payload 校验、FakeModel 和 runner tests。
- Runtime 需要新增 child relationship store 和 dispatcher idempotency 规则。
- Parent reducer merge 依赖下一次 model activation，不提供自动 deterministic state merge；需要调用方显式处理 Child result。

## 备选方案

| 方案 | 为什么没有选择 |
| --- | --- |
| 通过外部 Signal 直接创建 Child | 无法表达 Parent model 请求 runtime 分发子任务的边界，也不利于审计 parent decision。 |
| Child 直接写 Parent state 或 Parent Event Log | 违反 “Child Session 永远不能直接修改 Parent Session” 和 one-writer invariant。 |
| 新增 reducer-specific Event / Decision DSL | 第一版没有足够调用方证明需要独立 reducer 框架，会扩大协议面和测试矩阵。 |
| Parent 创建 Child 后进入 `waiting` | 会限制多个 Child 并行和 Parent 接收其他 Signal；pending relationship 已能表达等待中的子任务。 |
| 默认继承 Parent capability grant | 隐式 delegation 风险过高，必须等 Parent/Child 语义稳定后单独 ADR。 |
| 直接接入真实 worker、queue 或 database | 违反 InMemory-first、FakeModel 和 provider-independent 主线。 |

## 迁移说明

- 现有 Session、Signal、Event、Checkpoint 可以继续读取；后续实现会新增 Decision kind、Event type、Signal type 和 ChildSessionRecord。
- 现有 `tool_call`、`submit_job`、`approval_result`、`job_result`、`timer` 语义不变。
- 任何实现 Parent/Child Session 的 PR 必须补 deterministic tests，覆盖 child creation、idempotency、authorization gate、Event append-only 和 Checkpoint round-trip。

## 关联

- PR: PR-0025
- Task: `docs/tasks/T-0027-parent-child-session-adr.md`
- 相关 ADR: `docs/adr/0005-async-job-timer-semantics.md`、`docs/adr/0006-memory-context-semantics.md`、`docs/adr/0007-safety-auth-semantics.md`、`docs/adr/0008-approval-flow-semantics.md`
- 后续任务: `docs/tasks/T-0028-inmemory-child-session-creation.md`
