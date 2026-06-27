# Safety/Auth 收尾审查与下一阶段重评估

> 状态: 当前
> 最近更新: 2026-06-27

## 背景

P0 durable Session runtime core、P1 async job/timer、本地 Memory + Context，以及 Safety/Auth 本地确定性实现已经连续完成。当前需要决定下一阶段进入哪条主线，同时避免把真实 identity provider、production policy 或业务 RBAC 提前混入 core。

本次重评估对照：

- ADR-0007：Safety/Auth 语义。
- ADR-0008：Approval flow 语义。
- PR-0019 到 PR-0023 的完成记录和测试覆盖。

## 结论

下一阶段优先进入 **Parent/Child Session**，先做 ADR，再做 InMemory 本地确定性实现。

推荐顺序：

1. PR-0025：ADR 定义 Parent/Child Session 语义。
2. 后续再拆 InMemory child session creation、child result Signal / reducer flow、Checkpoint recovery example/test。
3. capability delegation 等 Parent/Child Session 边界清楚后再单独 ADR。
4. 真实 identity provider、production policy、OAuth/OIDC、IAM、server、database 和 cloud deployment 继续后置到 integration 层，不进入下一阶段 core 主线。

## Safety/Auth 覆盖审查

| 主题 | 目标 | 当前状态 | 说明 |
| --- | --- | --- | --- |
| Runtime-side policy boundary | Model 不能自授权，runtime 在 action 分发前检查 policy。 | 已完成 | PR-0019 已在 `tool_call` / `submit_job` 分发前接入 InMemory policy gate。 |
| Session-scoped CapabilityGrant | 先支持 Session-scoped grant，默认 deny。 | 已完成 | PR-0019 已实现 `AuthContext`、`CapabilityGrant`、`InMemoryCapabilityGrantStore` 和 `InMemoryPolicyGate`。 |
| Authorization denial | hard deny 是 dataized runtime outcome，写 Event 和 Checkpoint。 | 已完成 | PR-0019 已追加 `authorization_denied` Event，并跳过 tool/job dispatch。 |
| ApprovalRequest durable record | approval-required 需要 durable record 和 deterministic id。 | 已完成 | PR-0021 已实现 `ApprovalRequest`、`ApprovalStatus`、`approval_request_id` 和 InMemory store。 |
| Approval-required runner branch | 需要审批时暂停原 action，追加 `approval_requested` Event。 | 已完成 | PR-0022 已对 `tool_call` / `submit_job` 创建 ApprovalRequest、写 Event/Checkpoint，并使用 `waiting`。 |
| Approval result runtime flow | `approval_result` Signal 回灌，approved dispatch，denied skip，stale ignored。 | 已完成 | PR-0023 已实现专用 runner 分支，不调用 model，并覆盖 duplicate / stale 行为。 |
| Event Log / Checkpoint boundary | policy、approval request、approval result 必须可审计和可恢复。 | 已完成 | PR-0019 到 PR-0023 均写入 Event 和 Checkpoint；测试覆盖 Checkpoint state。 |

## 仍不属于当前 core 的内容

- 真实 identity provider、OAuth/OIDC、IAM、secrets manager。
- production policy DSL、RBAC 管理界面、cloud audit export。
- agent-scoped、global、cross-session grant。
- capability delegation。
- expired / canceled approval 的外部入口。
- 对 timer request、external Signal admission 或 child session creation 的授权 gate。

这些不是当前实现缺陷，而是明确后置的集成层或后续 ADR 方向。

## 下一阶段方向比较

| 方向 | 当前判断 | 原因 |
| --- | --- | --- |
| Parent/Child Session | 优先 | Memory + Context 和 Safety/Auth 已补齐，早前阻塞项已解除；这是 durable Session runtime 的下一块核心编排语义。 |
| Capability delegation | 后置 | delegation 需要先知道 Parent 如何创建 Child、Child 如何回灌 Parent，以及 reducer merge 权限边界。 |
| 真实 identity provider / production policy | 后置 | 属于 integration / product layer；没有第一个真实调用方时会让 core 变成业务权限平台。 |
| Server / database / provider adapter | 后置 | 仍违反当前 InMemory-first、FakeModel 和 provider-independent 主线。 |

## Parent/Child Session ADR 必须回答

1. Parent 如何创建 Child：新的 Decision kind、runtime API，还是外部 Signal？
2. Child result 如何回灌 Parent：普通 Signal、JobResult 类似 Signal，还是 reducer-specific Event？
3. reducer merge 是 runtime action、model Decision，还是独立 reducer policy？
4. Parent / Child 是否共享 context 和 memory，还是只通过显式 child result 通信？
5. CapabilityGrant 和 ApprovalRequest 是否可以委派给 Child；如果可以，委派范围和审计边界是什么？
6. Event Log 和 Checkpoint 如何表达 parent-child relationship、child completion 和 parent merge 恢复点？
7. 同一个 Parent 同时等待多个 Child 时，writer / ordering / idempotency 如何保持确定性？

## 下一步

下一步不要直接实现 Parent/Child runtime。先执行 PR-0025 / T-0027，新增 Parent/Child Session ADR；ADR accepted 后再拆本地 InMemory 实现切片。
