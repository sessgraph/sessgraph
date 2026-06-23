# T-0021: InMemory capability policy gate

> 状态: 已完成
> PR: PR-0019
> 最近更新: 2026-06-23

## 目标

基于 ADR-0007，实现第一个本地、确定性的 Safety/Auth runtime-side policy gate，让 Activation Runner 在分发敏感 action 前可以检查 Session-scoped CapabilityGrant。

## 范围

范围内：

- `AuthContext`、`CapabilityGrant`、policy decision 和 InMemory grant store。
- 对 `tool_call` 和 `submit_job` Decision 做 runtime-side authorization gate。
- 默认 deny；明确 grant 才允许分发。
- 授权拒绝时追加 dataized Event，保存 Checkpoint，并且不执行 tool / 不创建 job。
- 确定性 id、幂等 store 行为和 runner 集成测试。

范围外：

- 不实现 approval flow 或 ApprovalRequest store。
- 不接入真实 identity provider、OAuth/OIDC、IAM、secrets manager 或网络服务。
- 不实现 production policy DSL、RBAC 管理界面、cloud audit export。
- 不实现 Parent/Child Session 或 capability delegation。
- 不修改已有 `tool_call` / `submit_job` Decision payload 结构。

## 依赖

- PR-0018 Safety/Auth ADR 已完成。

## 验证

- Auth model / store deterministic tests。
- ActivationRunner policy gate integration tests。
- `make check`。

## 完成记录

- 新增本地 `AuthContext`、`CapabilityGrant`、`PolicyDecision`、`InMemoryCapabilityGrantStore` 和 `InMemoryPolicyGate`。
- Activation Runner 在 `tool_call` / `submit_job` Decision schema 校验后、action 分发前执行 policy gate。
- policy gate 默认 deny；只有匹配 Session-scoped active grant 时才允许执行 tool 或创建 job。
- 授权拒绝会追加 `authorization_denied` Event、保存 Checkpoint 中的 `policy_decision`，并跳过 tool execution / job creation。
- 新增 auth model/store 和 runner integration deterministic tests；`make check` 通过。
- 未实现 approval flow、ApprovalRequest store、真实 identity provider、OAuth/OIDC、IAM、policy DSL、Parent/Child Session 或 capability delegation。
