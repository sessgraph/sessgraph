# ADR-0008: Approval flow 语义

> 状态: Accepted
> 日期: 2026-06-23
> 相关任务: PR-0020 / `docs/tasks/T-0022-approval-flow-adr.md`

## 背景

ADR-0007 已决定 Safety/Auth 是 runtime-side policy boundary：model 只产出 Decision，不能通过 prompt、payload 或 Decision 自授权。PR-0019 已实现第一个 InMemory capability policy gate：`tool_call` / `submit_job` 在 action 分发前做 Session-scoped grant 检查，明确 grant 才允许，默认 deny。

下一步如果直接实现 approval flow，会触及公开 runtime 语义：ApprovalRequest 是否 durable、approval result 如何回灌 Session、审批期间是否进入 waiting、Checkpoint 记录什么、审批通过后如何继续分发原 action。按照仓库规则，公开协议和生命周期变化必须先 ADR。

## 决策

1. PR-0020 只定义 approval flow 语义，不实现 runtime 代码。
2. Approval-required 是 runtime policy outcome，不新增 Decision kind，model 不能主动要求审批来绕过授权。
3. Approval gate 发生在 Decision schema 校验之后、action 分发之前。需要审批时，runtime 必须暂停该 action，不得先执行 tool、创建 job 或触发未来 child session。
4. v0.5 首个 approval 实现范围只覆盖 `tool_call` 和 `submit_job`；timer request、external Signal admission、child session creation 后续单独 ADR 或实现切片决定。
5. Runtime 需要创建 durable `ApprovalRequest` record。最小字段为 `schema_version`、`approval_id`、`session_id`、`decision_id`、`signal_id`、`action_kind`、`resource`、`action_payload`、`requesting_actor`、`status`、`created_at`、`resolved_at`、`resolved_by`、`reason`、`data`、`idempotency_key`。
6. `status` 初始为 `pending`，可终止为 `approved`、`denied`、`expired` 或 `canceled`。终止状态不可再变更；重复 resolution 必须按 idempotency 处理。
7. `action_payload` 保存恢复和分发原 action 所需的最小 JSON-compatible payload。不得写入 provider token、secret、credential 或不可审计的宿主私有对象。
8. `approval_id` 必须确定性生成，建议基于 `session_id`、`decision_id`、`action_kind`、canonical `resource` 和 `idempotency_key`。v0.5 不使用随机数。
9. 创建 ApprovalRequest 时必须追加 `approval_requested` Event。payload 至少包含 `approval_id`、`decision_id`、`signal_id`、`action_kind`、`resource`、`requesting_actor`、`policy` 和 `reason`。
10. approval-required 时 Session 可以使用现有 `waiting` 状态，不新增 SessionStatus。Checkpoint state 必须记录 `policy_decision`、`approval_id`、`decision_id`、`action_kind`、`resource` 和 pending action metadata。
11. Approval result 通过普通 `Signal(signal_type="approval_result")` 回灌 Session，不新增 Decision kind。Signal payload 至少包含 `approval_id`、`approved`、`resolved_by`、`reason` 和 JSON object `data`。
12. Runtime 处理 `approval_result` Signal 时必须先查找 matching pending ApprovalRequest；找不到、Session 不匹配、状态已终止或 idempotency 冲突时，不得分发原 action。
13. 审批通过后，runtime 可以基于 ApprovalRequest 中的 action metadata 分发原 action，并追加 `approval_resolved` Event。payload 至少包含 `approval_id`、`decision_id`、`action_kind`、`resource`、`status`、`resolved_by` 和 `reason`。
14. 审批拒绝、过期或取消时，runtime 必须追加 `approval_resolved` Event，保存 Checkpoint，并跳过原 action。该结果是 dataized runtime outcome，不等同 runtime invariant failure。
15. approval result Signal 本身仍遵循 Signal 是唯一外部激活边界的规则；宿主传入的 AuthContext 才是 actor 身份事实，Signal payload 里的 `resolved_by` 只作为被审计数据，不能单独作为身份认证结果。
16. ApprovalRequest store 后续首个实现应为 InMemory store，覆盖 create idempotency、latest/get lookup、resolve concurrency、terminal immutability 和 deterministic ordering。
17. Activation Runner 后续实现必须覆盖 deterministic tests：approval requested、approved dispatch、denied skip、duplicate result idempotency、stale result ignored、Checkpoint round-trip、Event append-only。
18. Authorization denial 和 approval-required 保持不同 outcome：hard deny 使用现有 `authorization_denied` Event；需要审批使用 `approval_requested` / `approval_resolved` Event。
19. Production identity provider、OAuth/OIDC、IAM、policy DSL、secrets manager、network service、cloud audit export、RBAC UI、Parent/Child Session 和 capability delegation 都不属于 v0.5 approval 首个实现。

## 理由

- Approval 作为 runtime policy outcome，可以保持 “model 只产出 Decision，runtime 校验并分发 action” 的核心边界。
- ApprovalRequest durable 化后，Session 可以跨 Run、跨恢复点继续等待或处理审批结果。
- 用普通 Signal 回灌 approval result，可以复用现有 activation、Event Log 和 Checkpoint 机制。
- 把 hard deny 和 approval-required 分成不同 Event，可以让审计和后续 model context 更清楚。
- 首个实现保持 InMemory 和 deterministic tests，可以避免 Safety/Auth 过早变成业务权限平台。

## 后果

### 正面影响

- 后续可以拆一个小 PR 实现 `ApprovalRequest` / `InMemoryApprovalRequestStore`。
- Approval flow 的 waiting、resume、dispatch 和 skip 边界有稳定依据。
- Parent/Child Session 的 delegation 和 reducer 权限仍可留到更清晰的后续 ADR。

### 负面影响 / 代价

- Approval flow 会扩大公开协议面，新增 ApprovalRequest record、Event type 和 Signal payload 约束。
- Activation Runner 会多一条 pending action 恢复路径，需要更严格的幂等和并发测试。
- 首个版本只覆盖 Session-scoped、本地 InMemory 语义，不能直接代表生产 IAM 或人工审批系统。

## 备选方案

| 方案 | 为什么没有选择 |
| --- | --- |
| 新增 `DecisionKind.REQUEST_APPROVAL` | model 不能决定自己需要审批；审批必须来自 runtime policy。 |
| 把 approval result 做成专用 runtime API 而不是 Signal | 会绕过 Signal 是唯一外部激活边界的项目原则。 |
| 不保存 `action_payload`，审批通过后重新问 model | 审批对象会漂移，用户批准的 action 和最终执行的 action 可能不是同一个。 |
| 审批拒绝直接标记 Session failed | 拒绝是正常安全结果，不是 runtime invariant failure。 |
| 直接接入真实审批服务或 IAM | 违反 InMemory-first 和 provider-independent 边界，没有第一个真实调用方。 |

## 迁移说明

- 现有 `tool_call` / `submit_job` Decision payload 不变。
- 现有 PR-0019 hard deny 行为不变；后续实现只在 policy outcome 为 approval-required 时走 ApprovalRequest flow。
- 现有 Checkpoint 可以继续读取；新 Checkpoint 可额外包含 approval metadata。
- 任何实现 ApprovalRequest store、approval result Signal 或 approval Event 的 PR 必须补 deterministic tests。

## 关联

- PR: PR-0020
- Task: `docs/tasks/T-0022-approval-flow-adr.md`
- 相关 ADR: `docs/adr/0007-safety-auth-semantics.md`
