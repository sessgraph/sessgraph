# 状态文件维护指南

`docs/state/` 是 SessGraph 规划事实源层。AI 会话和人类贡献者开工前都应阅读这些文件，因为不同 AI 会话不能依赖共享聊天记忆。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `project-state.md` | 稳定的项目目标、范围边界和不变量。 |
| `project-status.md` | 当前阶段、当前主线和下一步的第一入口。 |
| `phase-two-plan.md` | P0 后第二阶段的目标、非目标、成功标准和建议 PR 切片。 |
| `pr-queue.md` | 产品 PR 队列的权威来源。 |
| `action-queue.md` | 跨主题的运营、文档或流程行动项。 |
| `risks.md` | 当前风险和缓解措施。 |
| `inbox.md` | 未整理的输入、会议记录和讨论摘要。 |

相关稳定流程文件位于 `docs/state/` 之外：

| 文件 | 用途 |
| --- | --- |
| `docs/DEVELOPMENT_PROCESS.md` | 仓库统一开发流程。 |
| `docs/README.md` | 文档索引。 |
| `docs/adr/` | 架构决策记录。 |
| `docs/openapi/` | 未来对外 API 契约。 |

## 更新规则

1. 未完成 triage 的原始讨论先追加到 `inbox.md`。
2. 可独立 review 的工作提升到 `pr-queue.md`；必要时新增 `docs/tasks/T-XXXX-*.md` 任务规格。
3. 每个完成的 PR 后，保持 `project-status.md` 与队列一致。
4. 新发现的风险写入 `risks.md`，不要埋在聊天记录里。
5. 优先保持 PR 切片小到可以作为一个连贯变更被 review、测试和提交。
