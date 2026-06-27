# T-0023: InMemory ApprovalRequest store

> 状态: 已完成
> PR: PR-0021
> 最近更新: 2026-06-27

## 目标

基于 ADR-0008，实现本地、确定性的 ApprovalRequest durable record 和 InMemory store，为后续 approval result runtime flow 提供存储边界。

## 范围

范围内：

- `ApprovalRequest`、`ApprovalStatus` 和 deterministic approval id helper。
- `InMemoryApprovalRequestStore`，覆盖 create idempotency、get/list lookup、pending ordering、resolve concurrency 和 terminal immutability。
- public package exports。
- deterministic unit tests。

范围外：

- 不实现 Activation Runner 的 approval-required 分支。
- 不处理 `approval_result` Signal dispatch。
- 不追加 `approval_requested` / `approval_resolved` Event。
- 不保存 approval Checkpoint。
- 不接入真实 identity provider、OAuth/OIDC、IAM、secrets manager 或网络服务。
- 不实现 production policy DSL、RBAC 管理界面、cloud audit export、Parent/Child Session 或 capability delegation。

## 依赖

- PR-0020 approval flow ADR 已完成。

## 验证

- ApprovalRequest model/store deterministic tests。
- `make check`。

## 完成记录

- 新增 `ApprovalStatus`、`ApprovalRequest` 和 deterministic `approval_request_id`。
- 新增 `InMemoryApprovalRequestStore`，覆盖 create idempotency、get/list lookup、pending ordering、resolve concurrency 和 terminal immutability。
- 新增 public package exports。
- 新增 deterministic approval model/store tests。
- 未实现 Activation Runner approval-required 分支、`approval_result` Signal dispatch、approval Event 或 Checkpoint 保存。
