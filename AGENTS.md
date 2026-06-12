# AGENTS.md

## 项目

SessGraph 是一个开源 durable Session runtime，用于构建长期运行、具备状态、事件驱动、可恢复、可并行的 AI agent。

SessGraph 是基础设施项目，不是业务应用。当前主线是 P0 durable Session runtime core。

## 稳定事实源

编辑任何代码或文档前，必须先阅读：

1. `docs/state/project-status.md`
2. `docs/state/pr-queue.md`
3. `docs/DEVELOPMENT_PROCESS.md`
4. 如果工作已排队，还要阅读对应的 `docs/tasks/T-XXXX-*.md`

凡是应该沉淀到仓库里的事实，不得依赖聊天记忆。

## 核心循环

1. Signal 触发 Session。
2. Activation Runner 唤醒 Session。
3. Model adapter 只产出 Decision 对象。
4. Runtime 校验 Decision，并分发动作。
5. Event Log 记录事实。
6. Checkpoint 保存恢复状态。
7. Tool、job、timer 或 child-session 的结果可以再次触发 Session。

## 当前开发范围

优先构建 P0：

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

除非已经明确排队并获得批准，否则不要实现生产数据库、Web server、真实 LLM provider、云部署、GUI 或复杂多 Agent 编排。

## 架构规则

1. Session 是 durable 中心。
2. Run 是短生命周期执行。
3. Signal 是唯一外部触发入口。
4. 同一个 Session 同一时间只能有一个 writer。
5. Model 只产出 Decision，不直接执行工具。
6. Runtime 校验并分发 action。
7. Tool 永远不能直接修改 Session。
8. Child Session 永远不能直接修改 Parent Session。
9. Event Log 只能追加。
10. Checkpoint 是恢复点。
11. Core 必须与 provider 解耦。
12. P0 必须完全依靠 FakeModel 和 InMemory stores 运行。

## 工作流

编辑代码或文档前：

1. 执行 `git status --short`。
2. 确认用户请求已出现在 `docs/state/pr-queue.md`、`docs/state/action-queue.md` 或 `docs/state/inbox.md`；如果没有，先按统一流程补齐队列或任务记录。
3. 将改动控制在一个可独立 review 的 PR 切片内。
4. 如果请求改变架构或公开协议，先创建或更新 ADR，再实现。

编辑后：

1. 运行相关检查。
2. 如果队列、状态或风险发生变化，更新状态文件。
3. 提交变更。
4. 报告测试结果和未解决风险。

## 编码与测试规则

- 一旦出现代码，优先使用简单、显式、带 type hints 的 Python。
- 未经批准不得新增外部依赖。
- 测试不得发起真实网络调用或真实 LLM 调用。
- 测试必须确定性。
- 未经 ADR 不得修改公开协议。
- 公开行为变化必须同步更新文档。

## 受保护文件与动作

除非任务明确要求，否则不要修改：

- `.env` 和 `.env.*`。
- `secrets/**` 和 `credentials/**`。
- release/version 文件。
- CI 文件。
- public exports。
- 状态为 Accepted 的 ADR。
