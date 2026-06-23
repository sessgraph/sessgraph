# ADR-0006: Memory + Context 语义

> 状态: Accepted
> 日期: 2026-06-23
> 相关任务: PR-0015 / `docs/tasks/T-0017-memory-context-adr.md`

## 背景

P0 已证明本地 durable Session runtime 的核心闭环。P1 已补齐 async job/timer 语义和 InMemory 实现。下一阶段需要让长期 Session 在 Event Log 变长后仍能构造稳定、可恢复、可测试的 model context，同时保持 provider-independent，不引入真实 LLM summarizer、embedding、vector database、server 或 cloud。

现有 `ActivationContext` 直接携带 `agent`、`session`、`signal`、完整 Session Event 列表和 `now`。这个结构足以证明 P0/P1 行为，但不能表达长期 Session 的 context window、durable memory record、compaction 边界和恢复语义。

任务规格中有四个实现前开放问题：

1. Memory 是 Session-scoped、Agent-scoped，还是两者都需要？
2. ContextSnapshot 是 durable 对象，还是 activation-time 派生对象？
3. Compaction 结果写成 Event、Checkpoint state，还是单独 MemoryStore？
4. Model adapter 应接收完整 Event window、context snapshot，还是两者组合？

## 决策

1. PR-0015 只定义语义，不实现 runtime 代码。
2. Memory + Context 不新增 Decision kind。Memory record 创建和 compaction 是 runtime-side 行为，不由 model 直接请求。
3. P1 后续实现先支持 Session-scoped memory。Agent-scoped、global 或 cross-session memory 后续单独 ADR。
4. MemoryRecord 是 durable record，至少包含 `schema_version`、`memory_id`、`session_id`、`memory_type`、JSON object `content`、`source_event_ids`、`created_at`、`idempotency_key` 和可选 `supersedes_memory_ids`。
5. MemoryRecord 的 `content` 必须是 JSON object，不限定为纯文本 summary；这样后续可以表达摘要、事实、计划、偏好或压缩后的 tool/job 结果。
6. MemoryRecord id 必须确定性生成，P1 不使用随机数。重复 compaction 输入必须通过 `memory_id` 或 `idempotency_key` 幂等返回同一 MemoryRecord。
7. ContextSnapshot 是 activation-time 派生对象，不作为独立 durable store 的主记录。
8. ContextSnapshot 至少包含 `session_id`、`signal_id`、`event_window`、`memory_records`、`latest_checkpoint_id`、`built_at` 和用于审计的 ordering/limit metadata。
9. Context builder 的 ordering 必须确定：Event 按 `sequence` 升序，MemoryRecord 按 `(created_at, memory_id)` 升序；同一输入必须产生相同 ContextSnapshot。
10. Model adapter 接收 ContextSnapshot 作为 canonical context。现有 `ActivationContext.events` 在迁移期保留为 ContextSnapshot 中 `event_window` 的兼容视图，不再默认表示完整 Event Log。
11. Context builder 可以使用最新 Checkpoint 辅助恢复，但不能把 Checkpoint 当作事实来源替代 Event Log 或 MemoryRecord。
12. Compaction 由 runtime-side deterministic policy 触发，例如显式 maintenance 调用、event window 超过本地阈值，或测试 fixture。P1 不调用真实 LLM summarizer。
13. Compaction 输入是一个 Session 的 Event window、已有 active MemoryRecord 和 policy 参数；输出是新的 MemoryRecord。
14. Compaction 完成时 runtime 必须追加 `memory_compacted` Event。Event payload 至少包含 `memory_id`、`source_event_ids`、`supersedes_memory_ids` 和 compaction policy metadata。
15. Compaction 完成后 runtime 必须保存 Checkpoint，Checkpoint state 至少引用新 MemoryRecord、active memory ids、source event ids 和 compaction Event id，作为恢复边界。
16. Compaction 不删除 Event Log，不重写历史 Event，不直接修改 Session 业务状态。
17. 被 supersede 的 MemoryRecord 可以在 MemoryStore 中标记为 inactive 或通过新 MemoryRecord 的 `supersedes_memory_ids` 被排除出 active context；Event Log 仍保留原事实。
18. Activation checkpoint state 应记录本次 activation 使用的 ContextSnapshot metadata，包括 event ids 和 memory ids，便于恢复和审计。
19. P1 后续实现仍只允许 InMemory stores、FakeModel、deterministic compactor fixture 和 deterministic tests。
20. 真实 summarizer、embedding、vector database、token accounting、Safety/Auth、Parent/Child Session、provider adapter、server integration 和 cloud 后续单独立项。

## 理由

- Session-scoped memory 与当前 runtime 的 durable 中心一致，能先证明一个 Session 内的长期上下文恢复边界，避免过早引入跨 Session 权限和共享语义。
- ContextSnapshot 作为派生对象可以保持 Event Log 和 MemoryRecord 作为事实源，避免创建第三套长期事实存储。
- MemoryRecord 作为 durable record 可以让 compaction 结果被后续 activation 重用，而不是只存在于某次 Checkpoint state 中。
- `memory_compacted` Event 让 compaction 成为 append-only 事实，Checkpoint 则提供恢复点，两者分别承担审计和恢复职责。
- 保留 `ActivationContext.events` 兼容视图可以让后续实现分阶段迁移 FakeModel 和 tests，不需要一次性破坏现有 adapter 协议。

## 后果

- PR-0016 需要新增 InMemory memory/context 结构，并扩展 ActivationRunner 的 context 构造路径。
- PR-0016 不应实现 compaction policy，只证明 deterministic context builder。
- PR-0017 需要补齐 deterministic compaction fixture、`memory_compacted` Event 和 Checkpoint 验证。
- 后续若需要 Agent-scoped memory、共享 memory、embedding retrieval 或 real summarizer，必须新增 ADR。
- Safety/Auth 和 Parent/Child Session 不得夹带进 PR-0016 / PR-0017。

## 备选方案

| 方案 | 为什么没有选择 |
| --- | --- |
| 同时支持 Session-scoped 和 Agent-scoped memory | 会立即引入共享范围、权限、隔离和跨 Session 污染问题，超出下一组本地确定性切片。 |
| ContextSnapshot 作为独立 durable store 主记录 | 会让 Event Log、MemoryRecord、ContextSnapshot 三者都像事实源，增加恢复语义复杂度。 |
| 只把 compaction 写入 Checkpoint state | Checkpoint 是恢复点，不是 append-only 事实；缺少 Event 会让 compaction 难以审计。 |
| 只追加 `memory_compacted` Event，不保存 MemoryRecord | 后续 activation 无法稳定复用 compaction 结果，只能反复从 Event payload 解析。 |
| Model 直接产出 memory/compaction Decision | 当前没有第一个真实调用方需要 model 管理 memory 生命周期；会过早扩大 Decision 协议。 |
| 引入真实 summarizer 或 embedding | 违反 provider-independent 和 deterministic tests 边界。 |

## 迁移说明

- 现有 P0/P1 对象和测试不需要迁移。
- PR-0016 扩展 `ActivationContext` 时，应保持现有 `events` 字段为 event window 兼容视图。
- 现有 Checkpoint state 可以继续读取；新 Checkpoint 可额外包含 context snapshot metadata。
- 现有 tool/job/timer/wait-resume 语义不变。

## 关联

- PR: PR-0015
- Task: `docs/tasks/T-0017-memory-context-adr.md`
- 后续任务: `docs/tasks/T-0018-inmemory-context-builder.md`、`docs/tasks/T-0019-memory-compaction-example.md`
