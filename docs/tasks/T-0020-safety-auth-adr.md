# T-0020: Safety/Auth ADR

> 状态: 已完成
> PR: PR-0018
> 最近更新: 2026-06-23

## 目标

为 v0.5 Safety/Auth 写 ADR，先定义 authorization、approval、capability grant、actor/AuthContext 与 runtime action dispatch 的边界，再决定后续实现切片。

## 范围

范围内：

- 定义 Safety/Auth 在 runtime 中的位置。
- 定义 capability grant 的作用域和最小字段方向。
- 定义 approval 是 runtime-side policy gate，还是 Decision / Signal 协议扩展。
- 定义授权失败、需要审批、审批通过后的 Event / Checkpoint 边界。
- 明确后续实现仍保持 InMemory、FakeModel 和 deterministic tests。

范围外：

- 不实现 runtime 代码。
- 不接入真实 identity provider、OAuth/OIDC、IAM、secrets manager 或网络服务。
- 不实现 production policy DSL、RBAC 管理界面、cloud audit export。
- 不实现 Parent/Child Session。

## 依赖

- PR-0017 deterministic memory compaction example/test 已完成。
- Memory + Context 本地确定性闭环已完成。

## 验证

- ADR review。
- 文档状态一致性检查。
- `make check`。

## 完成记录

- 新增 `docs/adr/0007-safety-auth-semantics.md`。
- 决定 Safety/Auth 是 runtime-side policy boundary，model 不能自授权。
- 决定 approval 不新增 Decision kind；后续实现应使用 runtime-side ApprovalRequest 和普通 approval result Signal。
- 决定 policy denial / approval-required 是数据化 runtime outcome，不等同 runtime invariant failure。
- 未实现 runtime 代码、真实 identity provider、OAuth/OIDC、policy DSL、Safety/Auth store 或 Parent/Child Session。
