# T-0027: ADR 定义 Parent/Child Session 语义

> 状态: 待开始
> PR: PR-0025
> 最近更新: 2026-06-27

## 目标

为下一阶段 Parent/Child Session 先写 ADR，定义父子 Session 的创建、事件、结果回灌、Checkpoint、reducer merge 和 Safety/Auth 边界；本任务不实现 runtime 代码。

## 范围

范围内：

- 定义 Parent 如何请求创建 Child Session。
- 定义 Child result 如何以 Signal / Event 形式回灌 Parent。
- 定义 Parent reducer merge boundary，以及它是否需要新的 Decision kind。
- 定义 Parent / Child 是否共享 context、memory、capability grant 或 approval。
- 定义 Event Log、Checkpoint 和恢复语义。
- 明确 InMemory-first、FakeModel 和 deterministic tests 后续实现边界。

范围外：

- 不实现 Parent/Child runtime。
- 不实现 capability delegation。
- 不实现真实 worker、queue、database、server、provider、GUI 或 cloud。
- 不引入生产 IAM、OAuth/OIDC、RBAC 管理界面或 policy DSL。

## 依赖

- PR-0016 / PR-0017 Memory + Context 本地确定性闭环已完成。
- PR-0019 到 PR-0023 Safety/Auth 本地确定性闭环已完成。

## 验证

- ADR review。
- `make check`。
