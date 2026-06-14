# 项目状态

> 状态: P0 Activation Runner 已完成
> 最近更新: 2026-06-14

## 当前阶段

SessGraph 已完成初始规划 bootstrap、review follow-up、中文文档本地化修正、PR-0002 P0 core data structures、PR-0003 InMemory stores，以及 PR-0004 最小 Activation Runner 循环。初始产品讨论已经转换为仓库内持久的中文规划文件，后续 Codex、Claude Code 和人类会话共享同一事实源。

## 当前开发主线

**主线:** P0 durable session runtime core。

当前优先事项是 PR-0005：在已完成最小 Activation Runner 后，增加同步 tool execution flow。PR-0005 的任务规格仍为 TBD，启动实现前需要先补齐任务规格。

## 当前事实源

- 项目目标与边界：`docs/state/project-state.md`。
- 产品 PR 队列：`docs/state/pr-queue.md`。
- 统一开发流程：`docs/DEVELOPMENT_PROCESS.md`。
- 文档索引：`docs/README.md`。
- 跨主题行动项：`docs/state/action-queue.md`。
- 初始治理任务：`docs/tasks/T-0001-bootstrap-governance.md`。
- 中文文档本地化任务：`docs/tasks/T-0004-localize-agent-docs.md`。
- 第一个 runtime 任务：`docs/tasks/T-0002-p0-data-model.md`。
- 第一个 store 任务：`docs/tasks/T-0005-p0-inmemory-stores.md`。
- 第一个 runner 任务：`docs/tasks/T-0006-p0-activation-runner.md`。
- 第一个 core data model ADR：`docs/adr/0001-p0-core-data-model.md`。
- 第一个 runner ADR：`docs/adr/0002-p0-activation-runner.md`。

## 下一步

补齐 PR-0005 的任务规格，然后实现同步 tool execution flow。不要在该 PR 中实现 wait/resume、async job/timer、providers、databases 或 server mode。

## 一致性说明

- 项目名是 SessGraph。
- P0 是本地、确定性运行：FakeModel、InMemory stores、无真实 provider。
- 架构级变化必须先写 ADR，再实现。
- 现有面向贡献者和 AI agent 的 Markdown 文档应以中文为主；英文技术名词可保留为稳定术语。
