# T-0017: ADR 定义 Memory + Context 语义

> 状态: 已完成
> PR: PR-0015
> 最近更新: 2026-06-23

## 目标

为 Memory + Context 写 ADR，定义 context builder、memory record、memory compaction、Event 和 Checkpoint 边界，先固化公开语义再实现 runtime 代码。

## 范围

范围内：

- 定义 ActivationContext 与 context builder 的关系。
- 定义 memory record / context snapshot 的最小字段和确定性排序。
- 定义 compaction 何时发生、输入输出是什么、如何记录 Event 和 Checkpoint。
- 明确 provider-independent、InMemory、FakeModel 和 deterministic tests 边界。

范围外：

- 不实现 runtime 代码。
- 不接入真实 LLM summarizer、embedding、vector database、server、cloud 或网络调用。
- 不实现 Safety/Auth。
- 不实现 Parent/Child Session。

## 开放问题

1. Memory 是 Session-scoped、Agent-scoped，还是两者都需要？
2. ContextSnapshot 是 durable 对象，还是 activation-time 派生对象？
3. Compaction 结果写成 Event、Checkpoint state，还是单独 MemoryStore？
4. Model adapter 应接收完整 Event window、context snapshot，还是两者组合？

## 验证

- ADR review。
- 文档 diff review。
- `make check`。

## 完成记录

- 新增 `docs/adr/0006-memory-context-semantics.md`。
- 决定 P1 后续先支持 Session-scoped memory；Agent-scoped / cross-session memory 后续单独 ADR。
- 决定 ContextSnapshot 是 activation-time 派生对象，不作为独立 durable store 主记录。
- 决定 compaction 输出写入 MemoryRecord，并追加 `memory_compacted` Event、保存 Checkpoint 作为恢复边界。
- 决定 model adapter 接收 ContextSnapshot 作为 canonical context，现有 `ActivationContext.events` 迁移为 event window 兼容视图。
- 未实现 runtime 代码，未引入真实 summarizer、embedding、vector database、Safety/Auth 或 Parent/Child Session。
