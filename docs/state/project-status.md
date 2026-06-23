# 项目状态

> 状态: PR-0020 approval flow ADR 已完成
> 最近更新: 2026-06-23

## 当前阶段

SessGraph 已完成初始规划 bootstrap、review follow-up、中文文档本地化修正、PR-0002 P0 core data structures、PR-0003 InMemory stores、PR-0004 最小 Activation Runner 循环、PR-0005 同步 tool execution flow、PR-0006 wait/resume user flow、PR-0007 P0 收尾审查、PR-0008 checkpoint recovery example/test、PR-0009 第二阶段规划、PR-0011 async job/timer ADR、PR-0012 InMemory timer flow、PR-0013 InMemory async job flow、PR-0014 P1 后续方向重评估、PR-0015 Memory + Context ADR、PR-0016 InMemory context builder、PR-0017 deterministic memory compaction example/test、PR-0018 Safety/Auth ADR、PR-0019 InMemory capability policy gate，以及 PR-0020 approval flow ADR。Owner 已明确 license 决策先延后，因此 PR-0010 package/release hygiene 延后。

## 当前开发主线

**主线:** Safety/Auth 本地确定性实现。

当前 PR 队列中的 P0 本地核心闭环已完成：data model、InMemory stores、Activation Runner、FakeModel、Checkpoint save/load recovery example、同步 tool execution、wait/resume 和确定性测试均已落地。第二阶段 / P1 已完成 async job/timer 公开语义、InMemory timer flow 和 InMemory async job flow；package/release hygiene 已随 license 延后。Memory + Context 本地确定性闭环已完成。Safety/Auth 已完成 ADR-0007，并已落地第一个 InMemory capability policy gate：`tool_call` / `submit_job` 在 action 分发前检查 Session-scoped grant，默认 deny，拒绝结果会写入 Event 和 Checkpoint。Approval flow 已由 ADR-0008 明确为 runtime policy outcome：ApprovalRequest 是 durable record，审批结果通过普通 `approval_result` Signal 回灌。尚未实现 ApprovalRequest store、approval result runtime flow、真实 identity provider 或 production policy。

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
- Memory + Context ADR 任务：`docs/tasks/T-0017-memory-context-adr.md`。
- InMemory context builder 任务：`docs/tasks/T-0018-inmemory-context-builder.md`。
- memory compaction example/test 任务：`docs/tasks/T-0019-memory-compaction-example.md`。
- Safety/Auth ADR 任务：`docs/tasks/T-0020-safety-auth-adr.md`。
- InMemory capability policy gate 任务：`docs/tasks/T-0021-inmemory-capability-policy-gate.md`。
- Approval flow ADR 任务：`docs/tasks/T-0022-approval-flow-adr.md`。
- 第一个 core data model ADR：`docs/adr/0001-p0-core-data-model.md`。
- 第一个 runner ADR：`docs/adr/0002-p0-activation-runner.md`。
- 第一个 tool ADR：`docs/adr/0003-sync-tool-execution.md`。
- 第一个 wait/resume ADR：`docs/adr/0004-wait-resume-user-flow.md`。
- async job/timer ADR：`docs/adr/0005-async-job-timer-semantics.md`。
- Memory + Context ADR：`docs/adr/0006-memory-context-semantics.md`。
- Safety/Auth ADR：`docs/adr/0007-safety-auth-semantics.md`。
- Approval flow ADR：`docs/adr/0008-approval-flow-semantics.md`。

## 下一步

PR-0010 license/package 决策继续挂起。下一步不要直接实现未排队能力；如果继续 Safety/Auth，建议基于 ADR-0008 拆 ApprovalRequest store / approval result flow 的本地确定性实现切片。

## 一致性说明

- 项目名是 SessGraph。
- P0 是本地、确定性运行：FakeModel、InMemory stores、无真实 provider。
- 架构级变化必须先写 ADR，再实现。
- 现有面向贡献者和 AI agent 的 Markdown 文档应以中文为主；英文技术名词可保留为稳定术语。
