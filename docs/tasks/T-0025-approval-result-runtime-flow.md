# T-0025: Approval result runtime flow

> 状态: 已完成
> PR: PR-0023
> 最近更新: 2026-06-27

## 目标

基于 ADR-0008，实现本地、确定性的 `approval_result` Signal runtime flow：处理审批结果、终止 ApprovalRequest、追加 Event、保存 Checkpoint，并在 approved 时分发原 action。

## 范围

范围内：

- `ActivationRunner` 专门处理 `Signal(signal_type="approval_result")`，不调用 model。
- 校验 `approval_result` payload：`approval_id`、`approved`、`resolved_by`、`reason` 和 JSON object `data`。
- 查找 matching pending `ApprovalRequest`；approved 时基于 ApprovalRequest 中保存的原 Decision 分发 `tool_call` / `submit_job`。
- denied 时 resolve ApprovalRequest、追加 `approval_resolved` Event、保存 Checkpoint，并跳过原 action。
- 找不到、Session 不匹配或已终止的 approval result 必须忽略，不得分发原 action；用确定性的 ignored Event 和 Checkpoint 记录原因。
- deterministic tests 覆盖 approved dispatch、denied skip、duplicate result idempotency、stale result ignored、Checkpoint round-trip 和 Event append-only。

范围外：

- 不新增 Decision kind 或 SessionStatus。
- 不实现 expired / canceled 的外部审批入口。
- 不实现真实 identity provider、OAuth/OIDC、IAM、secrets manager、审批服务或网络服务。
- 不实现 production policy DSL、RBAC 管理界面、cloud audit export、Parent/Child Session 或 capability delegation。

## 依赖

- PR-0020 approval flow ADR 已完成。
- PR-0021 InMemory ApprovalRequest store 已完成。
- PR-0022 approval-required runner flow 已完成。

## 验证

- approval result runtime integration tests。
- `make check`。

## 完成记录

- `ActivationRunner` 对 `approval_result` Signal 走专门 runtime 分支，不调用 model。
- Runtime 会校验 approval result payload，并查找 matching pending `ApprovalRequest`。
- approved 结果会 resolve ApprovalRequest、追加 `approval_resolved` Event、基于原 Decision 分发 `tool_call` / `submit_job`，并保存 Checkpoint。
- denied 结果会 resolve ApprovalRequest、追加 `approval_resolved` Event、跳过原 action，并保存 Checkpoint。
- 找不到、Session 不匹配或已终止的 approval result 会追加 `approval_result_ignored` Event、保存 Checkpoint，且不会分发原 action。
- 新增 deterministic tests 覆盖 approved dispatch、denied skip、duplicate result idempotency、stale result ignored、Checkpoint round-trip 和 Event append-only。
- 未实现 expired / canceled 外部入口、真实 identity provider、production policy、外部审批服务或 capability delegation。
