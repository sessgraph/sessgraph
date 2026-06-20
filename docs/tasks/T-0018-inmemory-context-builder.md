# T-0018: InMemory context builder

> 状态: 拟议
> PR: PR-0016
> 最近更新: 2026-06-20

## 目标

基于 Memory + Context ADR，实现本地、确定性的 context builder，让 Activation Runner 可以获得稳定、可测试的 context 输入。

## 范围

范围内：

- InMemory context / memory store 或等价本地结构。
- 从 Session、Signal、Event Log、Checkpoint 和 memory records 构造 deterministic context。
- Context ordering、windowing 和 schema round-trip 测试。
- 与 FakeModel / ActivationRunner 的最小集成测试。

范围外：

- 不实现真实 embedding、vector search、LLM summarizer、database、server、cloud 或网络调用。
- 不实现 Safety/Auth。
- 不实现 Parent/Child Session。
- 不改变 Memory + Context ADR 未定义的公开协议。

## 依赖

- PR-0015 Memory + Context ADR 已完成。

## 验证

- context builder deterministic tests。
- ActivationRunner context integration test。
- `make check`。
