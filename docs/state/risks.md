# 风险

> 状态: 当前
> 最近更新: 2026-06-20

| ID | 状态 | 风险 | 缓解措施 |
| --- | --- | --- | --- |
| R-0001 | 打开 | AI 会话可能在 runtime 边界稳定前实现过多能力。 | 保持 P0 队列小切片；要求任务规格；P0 禁止真实 provider、数据库、Web server 和多 Agent 实现。 |
| R-0002 | 打开 | 如果临时修改 Decision、Event、Checkpoint 格式，架构概念会漂移。 | 公开协议或生命周期变化必须先写 ADR/RFC。 |
| R-0003 | 打开 | 多个 AI 工具可能并行工作，并通过隐藏聊天记忆产生冲突。 | 只通过已提交的状态文件、任务规格、分支和 PR 协调。 |
| R-0004 | 打开 | 早期集成可能把 core 耦合到某个 provider 或框架。 | Core 必须先使用接口、FakeModel、InMemory 和确定性测试。 |
| R-0005 | 打开 | 共享 ChatGPT 链接在当前环境中无法完整读取，除标题外内容不可用。 | 将用户提供的转录文本作为初始规划的权威来源，并把原始笔记保留在 `inbox.md`。 |
| R-0006 | 已缓解 | P0 已保存 Checkpoint，但还缺少显式 checkpoint recovery example/test，容易让 “save/load” 语义停留在隐含用法。 | PR-0008 / T-0010 已补齐 latest Checkpoint load、Session recovery、event boundary 和 round-trip recovery 验证；仍不声称存在完整 crash recovery framework。 |
| R-0007 | 打开 | 第二阶段可能过早引入真实 provider、database、production queue 或 server，导致 core 边界失焦。 | 第二阶段规划明确只做 package hygiene、ADR、InMemory timer/job 和 deterministic tests；真实集成必须重新立项。 |
| R-0008 | 打开 | 即使 ADR 已完成，timer/job 实现仍可能在 PR-0012 或 PR-0013 中漂移出 ADR-0005 的边界。 | PR-0012 / PR-0013 必须引用 ADR-0005，并在测试中证明仍只使用 InMemory、FakeModel 和 deterministic tests。 |
