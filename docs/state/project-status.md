# 项目状态

> 状态: P0 基本核心实现已完成，checkpoint recovery 验证待补
> 最近更新: 2026-06-20

## 当前阶段

SessGraph 已完成初始规划 bootstrap、review follow-up、中文文档本地化修正、PR-0002 P0 core data structures、PR-0003 InMemory stores、PR-0004 最小 Activation Runner 循环、PR-0005 同步 tool execution flow、PR-0006 wait/resume user flow，以及 PR-0007 P0 收尾审查。初始产品讨论已经转换为仓库内持久的中文规划文件，后续 Codex、Claude Code 和人类会话共享同一事实源。

## 当前开发主线

**主线:** P0 durable session runtime core。

当前 PR 队列中的基本核心实现切片已完成，收尾审查未发现阻塞已完成切片的代码问题；checkpoint recovery example/test 仍是 P0 验证缺口，已整理为 PR-0008。下一步候选工作是 PR-0008 checkpoint recovery example/test；同时仍需 Owner 处理 license 决策，并在重新立项后再推进 package/release hygiene、async job/timer 或其他 v0.3+ 能力。

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
- 第一个 tool 任务：`docs/tasks/T-0007-sync-tool-execution.md`。
- 第一个 wait/resume 任务：`docs/tasks/T-0008-wait-resume-user-flow.md`。
- P0 收尾审查任务：`docs/tasks/T-0009-p0-closeout-review.md`。
- checkpoint recovery 拟议任务：`docs/tasks/T-0010-checkpoint-recovery-example.md`。
- 第一个 core data model ADR：`docs/adr/0001-p0-core-data-model.md`。
- 第一个 runner ADR：`docs/adr/0002-p0-activation-runner.md`。
- 第一个 tool ADR：`docs/adr/0003-sync-tool-execution.md`。
- 第一个 wait/resume ADR：`docs/adr/0004-wait-resume-user-flow.md`。

## 下一步

优先确认是否执行 PR-0008 checkpoint recovery example/test。不要在未立项前实现 async job/timer、providers、databases 或 server mode。

## 一致性说明

- 项目名是 SessGraph。
- P0 是本地、确定性运行：FakeModel、InMemory stores、无真实 provider。
- 架构级变化必须先写 ADR，再实现。
- 现有面向贡献者和 AI agent 的 Markdown 文档应以中文为主；英文技术名词可保留为稳定术语。
