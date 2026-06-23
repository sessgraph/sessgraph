# P1 后续方向重评估

> 状态: 当前
> 最近更新: 2026-06-23

## 背景

P0 durable Session runtime core 已完成本地核心闭环。第二阶段 / P1 已补齐 async job/timer 语义和 InMemory 实现；PR-0010 package/release hygiene 因 Owner license 决策延后而继续延后。

当前需要在三个候选方向之间选择下一组可 review 切片：

- Memory + Context。
- Safety/Auth。
- Parent/Child Session。

## 结论

下一阶段优先进入 **Memory + Context**，先做 ADR，再做本地确定性实现。

推荐顺序：

1. PR-0015：ADR 定义 Memory + Context 语义。已完成。
2. PR-0016：InMemory context builder。已完成。
3. PR-0017：deterministic memory compaction example/test。已完成。
4. Safety/Auth 后续单独进入 ADR，不在 Memory + Context 切片中顺手实现。已完成。
5. Parent/Child Session 暂不启动；等 context、capability/approval 和 reducer 边界更清楚后再立项。

## 评估

| 方向 | 当前判断 | 原因 |
| --- | --- | --- |
| Memory + Context | 优先 | 项目里程碑中位于 v0.4，直接衔接现有 `ActivationContext`、Event Log 和 Checkpoint；可以继续保持 FakeModel、InMemory 和 deterministic tests。 |
| Safety/Auth | 后置 | tool/job/child 的权限模型很重要，但会牵涉 authorization、approval、capability grants 和 user identity；应先由 ADR 定义，不应夹在 context builder 中实现。 |
| Parent/Child Session | 暂缓 | 会修改 Session 关系、child result、parent reducer merge boundary，属于更宽的公开协议变化；没有 context 和 capability 边界前容易过早扩大 core。 |

## Memory + Context 建议边界

范围内：

- 定义 ActivationContext 应如何由 Session、Signal、Event Log、Checkpoint 和 memory records 组成。
- 定义 context snapshot / context builder 的稳定字段和 deterministic ordering。
- 定义 memory compaction 的触发边界、输入输出和 Event/Checkpoint 记录方式。
- 保持 provider-independent；不引入真实 embedding、vector database、LLM summarizer 或网络调用。
- 使用 InMemory stores、FakeModel 和 deterministic tests。

范围外：

- 不实现真实 model provider。
- 不实现 embedding、vector search、database、server、GUI 或 cloud。
- 不实现 tool/job authorization、approval 或 capability grants。
- 不实现 parent/child session。

## Safety/Auth 后续前置问题

- Capability grant 是绑定 AgentDefinition、Session、ToolSpec、JobType 还是 Signal 来源？
- Approval 是新的 Decision kind、Signal type，还是 runtime-side policy gate？
- 失败策略是拒绝 Decision、进入 waiting，还是生成 dataized result Signal？
- 用户身份和 actor 信息放在 Signal payload、metadata，还是单独 AuthContext？

## Parent/Child Session 后续前置问题

- Parent 如何创建 Child：Decision kind、runtime API，还是外部 Signal？
- Child result 如何回灌 Parent：普通 Signal、JobResult 类似 Signal，还是 reducer-specific Event？
- Reducer merge boundary 是否需要独立 Decision kind？
- Parent/Child 是否共享 memory/context，还是只通过显式 child result 通信？

## 当前推荐下一步

Safety/Auth ADR 已完成。后续不要直接实现未排队能力；需要先拆新的实现切片，例如 InMemory capability policy gate，或恢复 PR-0010 package/release hygiene 的 license/package 决策。
