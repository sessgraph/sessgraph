# SessGraph 项目状态

> 状态: 当前
> 最近更新: 2026-06-12

## 项目身份

SessGraph 是一个开源 durable Session runtime，用于构建长期运行 AI agent。目标用户是需要 agent 应用具备恢复能力、状态转移审计、tool/job 分发、并行工作协调能力的开发者；runtime core 不绑定任何单一 model provider 或外部服务。

## 核心定位

- **项目名:** SessGraph
- **Repository/package/CLI 名称:** `sessgraph`
- **Tagline:** 面向长期运行 agent 的 durable session runtime。
- **一句话说明:** 开源 durable session runtime，用于构建 stateful、event-driven、recoverable、parallel 的 AI agent。

## 第一性原则

1. Session 是系统的 durable 中心。
2. Run 是短生命周期执行；Session 跨 Run 持久存在。
3. Signal 是唯一外部激活边界。
4. Event Log 记录事实，并且只能追加。
5. Checkpoint 是恢复边界。
6. Model adapter 产出 Decision；runtime 校验并分发 action。
7. Tool、job 和 child session 永远不能直接修改 parent Session state。
8. Core 保持 provider-independent，并且无需 API key 或网络即可运行。
9. P0 先用 FakeModel 和 InMemory stores 证明 runtime，再做 integrations。

## P0 范围

P0 可以包含：

- AgentDefinition。
- Session。
- Signal。
- Event。
- Decision。
- Session Inbox。
- Activation Runner。
- InMemory stores。
- FakeModel adapter。
- Checkpoint save/load。
- 确定性测试。
- 最小 basic-session example。

P0 不包含：

- 真实 LLM provider adapter。
- Database 或 queue backend。
- FastAPI/web server mode。
- Cloud deployment。
- GUI。
- 复杂 parent/child 多 Agent 编排。
- 业务特定逻辑。

## 规划里程碑边界

| 里程碑 | 重点 | 说明 |
| --- | --- | --- |
| v0.1.0 | Durable Session Core | Data model、InMemory stores、FakeModel、Activation Runner、checkpoint、example。 |
| v0.2.0 | Tool + Wait | v0.1 稳定后，再做 tool registry/executor 和用户 wait/resume。 |
| v0.3.0 | Async Job + Timer | Job/timer signal，不硬依赖生产 queue。 |
| v0.4.0 | Memory + Context | Runtime 语义证明后，再做 context builder 和 memory compaction。 |
| v0.5.0 | Safety + Auth | Guardrails、authorization、approval、capability grants。 |
| v0.6.0 | Parent / Child Session | Parallel child sessions 和 reducer merge boundary。 |
