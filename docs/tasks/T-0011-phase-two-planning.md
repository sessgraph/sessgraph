# T-0011: 规划第二阶段

> 状态: 已完成
> PR: PR-0009
> 最近更新: 2026-06-20

## 目标

在 P0 本地核心闭环完成后，定义第二阶段的目标、非目标、成功标准和可独立 review 的后续 PR 切片，避免直接跳到未立项的 async job/timer、provider、database 或 server 实现。

## 范围

范围内：

- 新增第二阶段规划事实源。
- 更新 PR 队列，新增 PR-0009 完成记录和 PR-0010 到 PR-0013 拟议切片。
- 更新项目状态、行动队列、风险和文档索引。

范围外：

- 不实现 runtime 代码。
- 不新增 package metadata、license 文件或 release/version 文件。
- 不写 async job/timer ADR。
- 不实现 provider、database、queue、server、cloud、GUI、memory/context 或 parent/child session。

## 规划决策

1. 第二阶段命名为 “P1: 本地调度语义与开源可用性”。
2. 第二阶段先补 package/release hygiene，再以 ADR 方式定义 async job/timer 语义。
3. Timer 和 async job 分成不同 PR 实现，仍只使用 InMemory stores、FakeModel 和 deterministic tests。
4. License 仍由 Owner 决策；未确认前不新增 license 文件。

## 验证

- 文档 diff review。
- `git diff --check`。
- `make check`，确认规划变更未破坏现有测试。

## 完成记录

- 新增 `docs/state/phase-two-plan.md`。
- 将 PR-0009 标记为已完成。
- 将 PR-0010 到 PR-0013 写入拟议队列。
- 更新 `docs/state/project-status.md`、`docs/state/pr-queue.md`、`docs/state/action-queue.md`、`docs/state/risks.md`、`docs/state/README.md`、`docs/README.md` 和 README。
