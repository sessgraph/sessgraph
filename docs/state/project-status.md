# 项目状态

> 状态: PR-0014 P1 后续方向重评估已完成
> 最近更新: 2026-06-20

## 当前阶段

SessGraph 已完成初始规划 bootstrap、review follow-up、中文文档本地化修正、PR-0002 P0 core data structures、PR-0003 InMemory stores、PR-0004 最小 Activation Runner 循环、PR-0005 同步 tool execution flow、PR-0006 wait/resume user flow、PR-0007 P0 收尾审查、PR-0008 checkpoint recovery example/test、PR-0009 第二阶段规划、PR-0011 async job/timer ADR、PR-0012 InMemory timer flow、PR-0013 InMemory async job flow，以及 PR-0014 P1 后续方向重评估。Owner 已明确 license 决策先延后，因此 PR-0010 package/release hygiene 延后。

## 当前开发主线

**主线:** Memory + Context 语义规划。

当前 PR 队列中的 P0 本地核心闭环已完成：data model、InMemory stores、Activation Runner、FakeModel、Checkpoint save/load recovery example、同步 tool execution、wait/resume 和确定性测试均已落地。第二阶段 / P1 已完成 async job/timer 公开语义、InMemory timer flow 和 InMemory async job flow；package/release hygiene 已随 license 延后。P1 后续方向重评估已完成，结论是优先进入 Memory + Context，先写 ADR，再做本地确定性实现。

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
- checkpoint recovery 任务：`docs/tasks/T-0010-checkpoint-recovery-example.md`。
- 第二阶段规划：`docs/state/phase-two-plan.md`。
- P1 后续方向重评估：`docs/state/post-p1-reevaluation.md`。
- 第二阶段规划任务：`docs/tasks/T-0011-phase-two-planning.md`。
- package/release hygiene 延后任务：`docs/tasks/T-0012-package-release-hygiene.md`。
- async job/timer ADR 任务：`docs/tasks/T-0013-async-job-timer-adr.md`。
- InMemory timer flow 任务：`docs/tasks/T-0014-inmemory-timer-flow.md`。
- InMemory async job flow 任务：`docs/tasks/T-0015-inmemory-async-job-flow.md`。
- P1 后续方向重评估任务：`docs/tasks/T-0016-post-p1-reevaluation.md`。
- Memory + Context ADR 拟议任务：`docs/tasks/T-0017-memory-context-adr.md`。
- InMemory context builder 拟议任务：`docs/tasks/T-0018-inmemory-context-builder.md`。
- memory compaction example/test 拟议任务：`docs/tasks/T-0019-memory-compaction-example.md`。
- 第一个 core data model ADR：`docs/adr/0001-p0-core-data-model.md`。
- 第一个 runner ADR：`docs/adr/0002-p0-activation-runner.md`。
- 第一个 tool ADR：`docs/adr/0003-sync-tool-execution.md`。
- 第一个 wait/resume ADR：`docs/adr/0004-wait-resume-user-flow.md`。
- async job/timer ADR：`docs/adr/0005-async-job-timer-semantics.md`。

## 下一步

优先执行 PR-0015 Memory + Context ADR。不要在 ADR 前实现 context builder、memory compaction、Safety/Auth、Parent/Child Session、providers、databases 或 server mode。

## 一致性说明

- 项目名是 SessGraph。
- P0 是本地、确定性运行：FakeModel、InMemory stores、无真实 provider。
- 架构级变化必须先写 ADR，再实现。
- 现有面向贡献者和 AI agent 的 Markdown 文档应以中文为主；英文技术名词可保留为稳定术语。
