# 行动队列

> 状态: 当前
> 最近更新: 2026-06-27

本队列记录不属于单个产品 PR 切片的跨主题行动项。

| ID | 状态 | 负责人 | 行动 | 退出标准 |
| --- | --- | --- | --- | --- |
| ACT-0002 | 已完成 | Owner | 确认初始 license 选择。 | Owner 已确认使用 Apache-2.0；PR-0010 package/release hygiene 已完成。 |
| ACT-0003 | 已完成 | AI | 在第一次架构决策前补齐 ADR 模板。 | `docs/adr/0000-template.md` 已存在。 |
| ACT-0004 | 已完成 | AI | 补齐中文统一开发流程与文档索引。 | `docs/DEVELOPMENT_PROCESS.md` 和 `docs/README.md` 已存在。 |
| ACT-0005 | 已完成 | AI | 将 root agent 指令和已有文档统一为中文。 | `AGENTS.md`、`CLAUDE.md`、README、`docs/` 现有 Markdown 文档均以中文为主。 |
| ACT-0006 | 已完成 | AI | 确认 P0 后下一优先级：package/release hygiene、async job/timer 或其他 v0.3+ 工作。 | 第二阶段规划已写入 `docs/state/phase-two-plan.md`，PR-0010 到 PR-0013 已进入拟议队列。 |
| ACT-0007 | 已完成 | AI | 在 P1 timer/job 完成后，重新评估 Memory + Context、Safety/Auth、Parent/Child Session 的后续顺序。 | `docs/state/post-p1-reevaluation.md` 已记录结论：Memory + Context 已完成；Safety/Auth ADR 已完成；Parent/Child Session 后续单独 ADR。 |
