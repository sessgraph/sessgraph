# T-0024: Approval-required runner flow

> 状态: 已完成
> PR: PR-0022
> 最近更新: 2026-06-27

## 目标

基于 ADR-0008，在 Activation Runner 中实现本地、确定性的 approval-required 分支：当 policy gate 要求审批时，runtime 创建 ApprovalRequest、追加 approval Event、保存 Checkpoint，并暂停原 action。

## 范围

范围内：

- 在 `PolicyDecision` 中表达 approval-required outcome，保持 hard deny 行为不变。
- `InMemoryPolicyGate` 支持基于 CapabilityGrant constraint 产生 approval-required outcome。
- `ActivationRunner` 在 `tool_call` / `submit_job` 分发前创建 `ApprovalRequest`。
- 追加 `approval_requested` Event，并在 Checkpoint state 中记录 pending approval metadata。
- approval-required 时 Session 使用现有 `waiting` 状态，且不得执行 tool 或创建 job。
- deterministic runner integration tests。

范围外：

- 不处理 `approval_result` Signal dispatch。
- 不实现 approved dispatch、denied skip、duplicate result idempotency 或 stale result ignored。
- 不新增 Decision kind 或 SessionStatus。
- 不接入真实 identity provider、OAuth/OIDC、IAM、secrets manager、审批服务或网络服务。
- 不实现 production policy DSL、RBAC 管理界面、cloud audit export、Parent/Child Session 或 capability delegation。

## 依赖

- PR-0020 approval flow ADR 已完成。
- PR-0021 InMemory ApprovalRequest store 已完成。

## 验证

- approval-required runner integration tests。
- `make check`。

## 完成记录

- `PolicyDecision` 新增 `requires_approval`，保持 hard deny 的 `allowed=False` 行为不变。
- `InMemoryPolicyGate` 支持通过 CapabilityGrant `constraints.requires_approval=true` 产生 approval-required outcome。
- `ActivationRunner` 在 `tool_call` / `submit_job` 分发前创建 `ApprovalRequest`，追加 `approval_requested` Event，并将 ApprovalRequest 写入 Checkpoint。
- approval-required 时 Session 使用现有 `waiting` 状态，原 tool/job action 不会执行。
- 新增 deterministic runner integration tests 覆盖 tool_call 和 submit_job 暂停路径。
- 未实现 `approval_result` Signal dispatch、approved dispatch、denied skip、duplicate result idempotency 或 stale result ignored。
