# SessGraph

面向长期运行 AI agent 的 durable Session runtime。

SessGraph 是一个计划中的开源运行时内核，用于构建 durable（持久化）、stateful（有状态）、event-driven（事件驱动）、recoverable（可恢复）、parallel（可并行）的长期运行 AI agent。项目的核心观点是：Agent 不是一个长期运行的进程，而是一个可被 Signal 激活、可记录 Event、可保存 Checkpoint、可中断恢复的 durable Session 状态机。

## 当前阶段

仓库已完成规划/bootstrap、P0 data model、InMemory stores、最小 Activation Runner、同步 tool execution、wait/resume user flow、P0 收尾审查、checkpoint recovery example/test，以及第二阶段规划。当前目标不是快速堆实现，而是按小 PR 切片继续推进已立项的 durable Session runtime core 工作。

权威入口：

- [`docs/state/project-status.md`](docs/state/project-status.md)：当前状态和下一步。
- [`docs/state/project-state.md`](docs/state/project-state.md)：项目目标、边界、核心原则。
- [`docs/state/phase-two-plan.md`](docs/state/phase-two-plan.md)：P0 后第二阶段规划。
- [`docs/DEVELOPMENT_PROCESS.md`](docs/DEVELOPMENT_PROCESS.md)：统一开发流程。
- [`docs/state/pr-queue.md`](docs/state/pr-queue.md)：产品 PR 队列。
- [`docs/tasks/`](docs/tasks/)：可独立验收任务规格。
- [`AGENTS.md`](AGENTS.md) / [`CLAUDE.md`](CLAUDE.md)：AI agent 工作约束。

## P0 / P1 方向

P0 只做本地、确定性、可测试的 runtime core：

- AgentDefinition、Session、Signal、Event、Decision、Checkpoint 数据模型已完成。
- Session Inbox、InMemory stores、FakeModel adapter、最小 Activation Runner、checkpoint recovery example/test、同步 Tool execution 和 wait/resume 已完成。
- 其他后续能力应重新立项后再进入实现。
- 确定性测试和最小可运行 example。

第二阶段 / P1 聚焦本地调度语义与开源可用性：license/package hygiene 已延后，async job/timer ADR、InMemory timer flow 和 InMemory async job flow 已完成。真实 provider、database、production queue、server、cloud、GUI、memory/context 和 parent/child session 仍需后续单独立项。

P0 明确不做：真实 LLM provider、数据库、Web server、云部署、GUI、复杂多 Agent 编排、业务逻辑。

当前 P0 代码最低运行版本为 Python 3.12。

## 开发方式

所有工作通过 `docs/state/`、`docs/tasks/`、ADR、提交和 PR 协调。一个改动没有完成状态回写和提交，就不算完成。

新会话开工前请先读：

1. `docs/state/project-status.md`
2. `docs/state/pr-queue.md`
3. `docs/DEVELOPMENT_PROCESS.md`
4. `AGENTS.md` 或对应工具指令文件
