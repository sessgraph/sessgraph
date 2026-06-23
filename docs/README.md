# SessGraph 文档索引

> 状态: 当前
> 最近更新: 2026-06-23

## 开始阅读

1. `docs/state/project-status.md`：当前状态和下一步。
2. `docs/state/project-state.md`：项目目标、边界、P0 范围。
3. `docs/state/phase-two-plan.md`：P0 后第二阶段规划。
4. `docs/state/post-p1-reevaluation.md`：P1 后续方向重评估。
5. `docs/DEVELOPMENT_PROCESS.md`：统一开发流程。
6. `docs/state/pr-queue.md`：产品 PR 队列。
7. `docs/tasks/`：任务规格。

## 目录说明

| 路径 | 用途 |
| --- | --- |
| `docs/state/` | 当前事实源：状态、队列、风险、输入。 |
| `docs/tasks/` | 可独立验收任务的规格。 |
| `docs/adr/` | 架构决策记录；当前包含 P0 核心数据模型、Activation Runner、同步 Tool execution、wait/resume、P1 async job/timer 和 Memory + Context 语义决策。 |
| `docs/openapi/` | 未来对外 HTTP/API 契约；P0 暂无。 |
| `docs/DEVELOPMENT_PROCESS.md` | 仓库统一开发流程。 |

## 维护规则

- 新增顶层文档时，同步更新本索引。
- 当前状态不要写进稳定流程文档；写进 `docs/state/`。
- 架构决策不要只写在聊天里；写进 `docs/adr/`。
