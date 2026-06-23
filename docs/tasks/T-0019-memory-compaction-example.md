# T-0019: deterministic memory compaction example/test

> 状态: 已完成
> PR: PR-0017
> 最近更新: 2026-06-23

## 目标

基于 Memory + Context ADR 和 InMemory context builder，补齐 deterministic memory compaction 的示例和测试，证明长 Session 可以在本地压缩 context 并保留恢复边界。

## 范围

范围内：

- deterministic compaction policy 的最小实现或 fixture。
- compaction 输入、输出、Event 和 Checkpoint 边界测试。
- 最小 example 或 smoke test。
- 明确 compaction 后 activation 仍保持 provider-independent。

范围外：

- 不调用真实 LLM summarizer。
- 不使用 embedding、vector database、server、cloud 或网络调用。
- 不实现 Safety/Auth。
- 不实现 Parent/Child Session。
- 不实现生产级 token accounting。

## 依赖

- PR-0015 Memory + Context ADR 已完成。
- PR-0016 InMemory context builder 完成后执行。

## 验证

- deterministic compaction tests。
- example smoke test。
- `make check`。

## 完成记录

- 新增 deterministic `MemoryCompactor`、`DeterministicCompactionPolicy` 和 `MemoryCompactionResult`，仅使用 InMemory stores 和本地确定性输入。
- Compaction 输出 `MemoryRecord`，追加 `memory_compacted` Event，并保存引用 memory、active memory ids、source event ids 和 compaction Event id 的 Checkpoint。
- `ContextBuilder` 改为只读取 active memory records，被新 MemoryRecord supersede 的旧 memory 不再进入后续 context。
- 新增 `examples/memory_compaction_session.py` 和 deterministic compaction / example smoke tests。
- 已运行 `make check`。
