# ADR-0007: Safety/Auth 语义

> 状态: Accepted
> 日期: 2026-06-23
> 相关任务: PR-0018 / `docs/tasks/T-0020-safety-auth-adr.md`

## 背景

P0 durable Session runtime core、P1 async job/timer 和 Memory + Context 本地确定性闭环已经完成。下一阶段 v0.5 需要定义 Safety/Auth 语义，让 runtime 在分发 tool、job、timer、未来 child session 等动作前能做授权和审批判断，同时继续保持 provider-independent、deterministic tests 和 InMemory-first。

现有架构已经有几个硬边界：

1. Model adapter 只产出 Decision，不直接执行工具或修改 Session。
2. Runtime 校验 Decision，并分发 action。
3. Tool、job 和 child session 不能直接修改 parent Session state。
4. Signal 是唯一外部激活边界。
5. Event Log 只能追加，Checkpoint 是恢复边界。

Safety/Auth 必须接在这些边界上，而不是引入独立的业务应用权限系统。

P1 后续方向重评估中留下四个前置问题：

1. Capability grant 是绑定 AgentDefinition、Session、ToolSpec、JobType 还是 Signal 来源？
2. Approval 是新的 Decision kind、Signal type，还是 runtime-side policy gate？
3. 失败策略是拒绝 Decision、进入 waiting，还是生成 dataized result Signal？
4. 用户身份和 actor 信息放在 Signal payload、metadata，还是单独 AuthContext？

## 决策

1. PR-0018 只定义 Safety/Auth 语义，不实现 runtime 代码。
2. Safety/Auth 是 runtime-side policy boundary。Model 不能通过 Decision、prompt 或 payload 自授权。
3. Authorization gate 发生在 Decision schema 校验之后、action 分发之前；适用于 `tool_call`、`submit_job`，以及后续 timer request、child session creation、external Signal admission 等敏感边界。
4. CapabilityGrant 后续实现先支持 Session-scoped grants。grant 至少应表达 `grant_id`、`session_id`、可选 `agent_id`、`subject`、`action_kind`、`resource`、`constraints`、`created_at`、`expires_at`、`revoked_at` 和 `idempotency_key`。
5. `subject` 表示被授权主体，可以是 actor、agent 或宿主系统身份；P1/P2 不先做全局用户目录。
6. `resource` 是 JSON object，用于约束 action 目标，例如 `tool_name`、`job_type`、`signal_type` 或未来 `child_agent_id`。没有明确 grant 时默认 deny。
7. Agent-scoped、global、cross-session grants 后续单独 ADR；v0.5 首个实现不要默认共享 capability。
8. Actor/AuthContext 由宿主 runtime 在 Signal 进入边界时提供，不信任 model payload 自报身份。最小 AuthContext 应包含 `actor_id`、`actor_type`、`authenticated`、`scopes` 和 provider-independent `claims` JSON object。
9. AuthContext 是 activation-time 输入，不是 Session 业务状态。需要审计时，Event payload 和 Checkpoint state 只记录必要 actor / policy metadata，不把 secrets 或 provider tokens 写入 Event Log。
10. Approval 不新增 Decision kind。Approval 是 runtime-side policy gate 的结果：当 action 需要人工或外部系统审批时，runtime 生成 ApprovalRequest，暂停该 action。
11. ApprovalRequest 后续实现应是 durable record，至少包含 `approval_id`、`session_id`、`decision_id`、`action_kind`、`resource`、`requesting_actor`、`status`、`created_at`、`resolved_at` 和 `idempotency_key`。
12. Approval result 通过普通 `Signal(signal_type="approval_result")` 回灌 Session。Signal payload 至少包含 `approval_id`、`approved`、`resolved_by`、`reason` 和 JSON object `data`。
13. Approval-required 时，Session 可以进入 `waiting`，并保存 Checkpoint；恢复时仍从 Event Log、ApprovalRequest 和 approval result Signal 推导后续动作。
14. Authorization denial 和 approval-required 是数据化 runtime outcome，不等同 runtime invariant failure。只有 Decision 结构非法、Session 不变量破坏或 store 并发失败才使用异常 / failed runtime 路径。
15. Denial 必须追加 Event。Event payload 至少包含 `decision_id`、`action_kind`、`resource`、`actor`、`policy` 和 `reason`，并保存 Checkpoint 作为恢复边界。
16. Approval request / approval resolved 也必须追加 Event。Event payload 至少引用 `approval_id`、`decision_id`、`action_kind`、`resource`、`status` 和 actor metadata。
17. Policy outcome 需要确定性 id。grant id、approval id、policy event id 和 approval result signal id 都必须支持 idempotency；v0.5 不使用随机数。
18. Tool handler、job worker 和未来 child session 仍不能直接修改 parent Session；Safety/Auth 只决定 runtime 是否分发 action，不把业务 mutation 权限交给下游执行体。
19. v0.5 首个实现仍只允许 InMemory stores、FakeModel 和 deterministic tests；不接入真实 identity provider、OAuth/OIDC、IAM、secrets manager、network service、production policy DSL 或 cloud audit export。
20. Parent/Child Session 的权限继承、grant delegation 和 child result reducer 权限后续单独 ADR，不夹带进 Safety/Auth 首个实现。

## 理由

- 把 Safety/Auth 放在 runtime-side gate，可以保持 “model 只产出 Decision，runtime 校验并分发 action” 的核心边界。
- Session-scoped grants 与当前 durable Session 中心一致，能避免过早引入 cross-session 权限污染。
- AuthContext 由宿主提供，而不是信任 Signal payload 或 model payload，可以避免把不可信输入误当身份事实。
- Approval 作为 policy outcome 而不是 Decision kind，可以防止 model 自己请求审批来绕过授权。
- Denial / approval-required 数据化后，model 可以在后续 activation 中恢复、解释、请求用户输入或选择替代动作；不把业务权限拒绝误报成 runtime failure。
- Event + Checkpoint 分别承担审计和恢复职责，和现有 tool/job/timer/memory 边界保持一致。

## 后果

### 正面影响

- 后续可以分小 PR 实现 InMemory capability policy gate、ApprovalRequest store 和 approval result flow。
- Tool/job 的授权边界变清晰，真实 provider 或生产 IAM 不会提前进入 core。
- Parent/Child Session 可以等 capability delegation 语义清楚后再设计。

### 负面影响 / 代价

- v0.5 需要新增 AuthContext、CapabilityGrant、ApprovalRequest 等概念，公开协议面会扩大。
- Approval flow 会让 Activation Runner 的状态转移更复杂，需要严格测试 waiting、resume、denial 和 idempotency。
- 仅做 Session-scoped grants 会推迟 agent/global 共享权限能力。

## 备选方案

| 方案 | 为什么没有选择 |
| --- | --- |
| 让 model 产出 approval Decision | model 不能自授权，也不能决定自己是否需要审批；approval 必须是 runtime policy outcome。 |
| 把 actor 写进 Signal payload 并直接信任 | Signal payload 是外部输入，不能作为身份事实；宿主必须构造 AuthContext。 |
| 授权失败直接抛 DecisionRejectedError | 权限拒绝是正常业务/安全结果，不是 Decision schema 错误；需要 dataized outcome 供 Session 恢复。 |
| 先做全局 RBAC / policy DSL | 没有第一个真实调用方，且会把 core 过早变成业务权限平台。 |
| 直接接 OAuth/OIDC 或云 IAM | 违反 provider-independent 和 InMemory-first 边界，真实 identity provider 应留到 integration 层。 |

## 迁移说明

- 现有 P0/P1/Memory + Context 对象和测试不需要迁移。
- 现有 `tool_call` 和 `submit_job` Decision 结构暂不改变；后续实现 Safety/Auth gate 时应在 Decision 校验后、action 分发前插入 policy check。
- 现有 Checkpoint state 可以继续读取；新 Checkpoint 可额外包含 policy outcome metadata。
- 任何新增 AuthContext、CapabilityGrant、ApprovalRequest、approval result Signal 或 policy Event type 的实现 PR 必须补 deterministic tests。

## 关联

- PR: PR-0018
- Task: `docs/tasks/T-0020-safety-auth-adr.md`
- 相关 ADR: `docs/adr/0003-sync-tool-execution.md`、`docs/adr/0005-async-job-timer-semantics.md`、`docs/adr/0006-memory-context-semantics.md`
