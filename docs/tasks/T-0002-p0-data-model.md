# T-0002: 定义 P0 核心数据结构

> 状态: 拟议
> PR: PR-0002
> 最近更新: 2026-06-12

## 目标

定义最小 P0 数据结构，让 SessGraph 成为 durable Session runtime，而不是业务应用框架。

## 范围

范围内：

- AgentDefinition。
- Session。
- Signal。
- Event。
- Decision。
- Checkpoint。
- 针对构造、校验和序列化的确定性单元测试。

范围外：

- Activation Runner 行为。
- Tool execution。
- Wait/resume。
- InMemory stores。
- Provider integrations。
- Database/web/cloud 代码。
- Parent/child Session 编排。

## 架构约束

- Session 是 durable state center。
- Signal 是唯一外部触发边界。
- Event 是 append-only fact record。
- Checkpoint 是恢复边界。
- Model output 以 Decision 对象表示。
- 数据结构必须与 provider 解耦，并且测试必须确定性。

## 实现前开放问题

1. P0 core data structures 应使用 dataclasses 还是 Pydantic？
2. Event 和 Checkpoint 的初始公开序列化格式是什么？
3. Signal ID 和 Event ID 需要哪些字段来支持幂等性？

## 验证

- 有效和无效对象构造的单元测试。
- 如果本 PR 包含序列化，则加入序列化 round-trip 测试。
- 不使用网络、API key、数据库或真实 model 调用。
