# 项目状态

> 状态: PR-0024 Safety/Auth 收尾审查与下一阶段重评估已完成
> 最近更新: 2026-06-27

## 当前阶段

SessGraph 已完成初始规划 bootstrap、review follow-up、中文文档本地化修正、PR-0002 P0 core data structures、PR-0003 InMemory stores、PR-0004 最小 Activation Runner 循环、PR-0005 同步 tool execution flow、PR-0006 wait/resume user flow、PR-0007 P0 收尾审查、PR-0008 checkpoint recovery example/test、PR-0009 第二阶段规划、PR-0010 package/release hygiene、PR-0011 async job/timer ADR、PR-0012 InMemory timer flow、PR-0013 InMemory async job flow、PR-0014 P1 后续方向重评估、PR-0015 Memory + Context ADR、PR-0016 InMemory context builder、PR-0017 deterministic memory compaction example/test、PR-0018 Safety/Auth ADR、PR-0019 InMemory capability policy gate、PR-0020 approval flow ADR、PR-0021 InMemory ApprovalRequest store、PR-0022 approval-required runner flow、PR-0023 approval result runtime flow，以及 PR-0024 Safety/Auth 收尾审查与下一阶段重评估。Owner 已确认 license 使用 Apache-2.0。

## 当前开发主线

**主线:** Parent/Child Session 语义规划。

当前 PR 队列中的 P0 本地核心闭环已完成：data model、InMemory stores、Activation Runner、FakeModel、Checkpoint save/load recovery example、同步 tool execution、wait/resume 和确定性测试均已落地。第二阶段 / P1 已完成 package/release hygiene、async job/timer 公开语义、InMemory timer flow 和 InMemory async job flow。Memory + Context 本地确定性闭环已完成。Safety/Auth v0.5 本地确定性闭环也已完成：ADR、Session-scoped capability gate、Authorization denial、ApprovalRequest store、approval-required runner branch 和 approval result runtime flow 均已落地。PR-0024 结论是下一阶段优先进入 Parent/Child Session，先写 ADR，不直接实现 runtime。

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
- package/release hygiene 任务：`docs/tasks/T-0012-package-release-hygiene.md`。
- async job/timer ADR 任务：`docs/tasks/T-0013-async-job-timer-adr.md`。
- InMemory timer flow 任务：`docs/tasks/T-0014-inmemory-timer-flow.md`。
- InMemory async job flow 任务：`docs/tasks/T-0015-inmemory-async-job-flow.md`。
- P1 后续方向重评估任务：`docs/tasks/T-0016-post-p1-reevaluation.md`。
- Memory + Context ADR 任务：`docs/tasks/T-0017-memory-context-adr.md`。
- InMemory context builder 任务：`docs/tasks/T-0018-inmemory-context-builder.md`。
- memory compaction example/test 任务：`docs/tasks/T-0019-memory-compaction-example.md`。
- Safety/Auth ADR 任务：`docs/tasks/T-0020-safety-auth-adr.md`。
- InMemory capability policy gate 任务：`docs/tasks/T-0021-inmemory-capability-policy-gate.md`。
- Approval flow ADR 任务：`docs/tasks/T-0022-approval-flow-adr.md`。
- InMemory ApprovalRequest store 任务：`docs/tasks/T-0023-inmemory-approval-request-store.md`。
- Approval-required runner flow 任务：`docs/tasks/T-0024-approval-required-runner-flow.md`。
- Approval result runtime flow 任务：`docs/tasks/T-0025-approval-result-runtime-flow.md`。
- Safety/Auth 收尾重评估：`docs/state/post-safety-auth-reevaluation.md`。
- Safety/Auth 收尾重评估任务：`docs/tasks/T-0026-safety-auth-closeout-reevaluation.md`。
- Parent/Child Session ADR 任务：`docs/tasks/T-0027-parent-child-session-adr.md`。
- 第一个 core data model ADR：`docs/adr/0001-p0-core-data-model.md`。
- 第一个 runner ADR：`docs/adr/0002-p0-activation-runner.md`。
- 第一个 tool ADR：`docs/adr/0003-sync-tool-execution.md`。
- 第一个 wait/resume ADR：`docs/adr/0004-wait-resume-user-flow.md`。
- async job/timer ADR：`docs/adr/0005-async-job-timer-semantics.md`。
- Memory + Context ADR：`docs/adr/0006-memory-context-semantics.md`。
- Safety/Auth ADR：`docs/adr/0007-safety-auth-semantics.md`。
- Approval flow ADR：`docs/adr/0008-approval-flow-semantics.md`。

## 下一步

下一步执行 PR-0025 / T-0027：先写 Parent/Child Session ADR，定义 parent/child 创建、result 回灌、reducer merge、Checkpoint 和 Safety/Auth 边界；ADR accepted 前不要实现 Parent/Child runtime。

## 一致性说明

- 项目名是 SessGraph。
- P0 是本地、确定性运行：FakeModel、InMemory stores、无真实 provider。
- 架构级变化必须先写 ADR，再实现。
- 现有面向贡献者和 AI agent 的 Markdown 文档应以中文为主；英文技术名词可保留为稳定术语。
