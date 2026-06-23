# T-0022: Approval flow ADR

> 状态: 已完成
> PR: PR-0020
> 最近更新: 2026-06-23

## 目标

在 ADR-0007 已定义 Safety/Auth 总体边界、PR-0019 已完成 InMemory capability policy gate 之后，补齐 approval-required 的 durable record、Event、Signal、Checkpoint 和恢复语义，先固定协议再进入 runtime 实现。

## 范围

范围内：

- 定义 ApprovalRequest 的最小 durable record 字段、状态机和幂等边界。
- 定义 approval-required 时的 Event、Checkpoint 和 Session waiting 边界。
- 定义 approval result 通过普通 Signal 回灌 Session 的 payload 边界。
- 定义审批通过、拒绝、过期、取消后的 action dispatch / recovery 语义。
- 明确后续实现仍保持 InMemory、FakeModel 和 deterministic tests。

范围外：

- 不实现 runtime 代码。
- 不新增真实 identity provider、OAuth/OIDC、IAM、secrets manager 或网络服务。
- 不实现 production policy DSL、RBAC 管理界面或 cloud audit export。
- 不实现 Parent/Child Session、capability delegation 或跨 Session approval。
- 不修改现有 `tool_call` / `submit_job` Decision payload 结构。

## 依赖

- PR-0018 Safety/Auth ADR 已完成。
- PR-0019 InMemory capability policy gate 已完成。

## 验证

- ADR review。
- 文档状态一致性检查。
- `make check`。

## 完成记录

- 新增 `docs/adr/0008-approval-flow-semantics.md`。
- 决定 approval-required 是 runtime policy outcome，不新增 Decision kind。
- 决定 ApprovalRequest 是 durable record，approval result 通过普通 `approval_result` Signal 回灌。
- 决定 approval request / resolved 都必须追加 Event，并保存 Checkpoint 作为恢复边界。
- 未实现 runtime 代码、ApprovalRequest store、真实 identity provider、production policy、Parent/Child Session 或 capability delegation。
