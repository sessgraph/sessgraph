# SessGraph 统一开发流程

> 状态: 当前
> 最近更新: 2026-06-12
> 适用对象: 所有在本仓库工作的 AI 会话（Codex、Claude Code、Cursor 等）与人类贡献者。
> 本文件只定义**流程**：工作如何进入、如何执行、如何退出。项目当前状态不写在这里，写在 `docs/state/`。

## 0. 角色分工

- **Owner（人类维护者）**：定方向、确认重大决策、验收结果、控制发布。
- **AI 会话**：执行者、整理器、冲突检查器。AI 不发明任务、不擅自扩大范围、不替 Owner 做重大决策。
- **多个 AI 会话**：彼此不可见，所有协调必须通过仓库文件、分支、Issue、PR、提交记录完成，不能依赖聊天记忆。

用户在当前会话里的明示指令优先于本文件；如果指令与流程冲突，先指出冲突，再按更高优先级执行。

## 1. 第一性原理

1. **稀缺的不是代码，是审查注意力。** 任何让人类或下一个 AI 会话更难读懂的巨型 diff、重复实现、隐式状态，都是负资产。
2. **只为已存在的需求写代码。** SessGraph 当前主线是长期运行 Agent 的 durable Session runtime；不要为想象中的平台能力预留空壳。
3. **同一事实只有一个权威来源。** 项目状态在 `docs/state/`，任务规格在 `docs/tasks/`，架构决策在 `docs/adr/`，接口契约在 `docs/openapi/`。
4. **进度的最小单位是已提交。** 未提交改动不是进度，是风险。
5. **P0 先证明内核，不做生态。** FakeModel、InMemory、确定性测试优先；真实模型、数据库、Web 服务、云部署后置。

## 2. 事实源地图

| 想知道 | 去哪看 |
| --- | --- |
| 项目目标、边界、核心原则 | `docs/state/project-state.md` |
| 当前状态总览和下一步 | `docs/state/project-status.md` |
| 产品 PR 队列 | `docs/state/pr-queue.md` |
| 跨主题行动项 | `docs/state/action-queue.md` |
| 任务详细规格 | `docs/tasks/T-XXXX-*.md` |
| 架构决策及理由 | `docs/adr/` |
| 对外接口契约 | `docs/openapi/` |
| 当前风险 | `docs/state/risks.md` |
| 未整理输入 | `docs/state/inbox.md` |
| 状态文件维护细则 | `docs/state/README.md` |
| AI agent 工作约束 | `AGENTS.md`、`CLAUDE.md` |

冲突处理：具体文件（`pr-queue.md`、任务规格、ADR）压倒汇总文件（`project-status.md`、README），并在同一 PR 中修正汇总文件。

## 3. 工作流总览

```text
想法 / 反馈 / 讨论记录
        │
        ▼
docs/state/inbox.md（原始输入，只追加）
        │  triage
        ▼
立项判定 ── 微改动 ───────────────┐
        │                         │
     标准 PR / 重大变更            │
        ▼                         ▼
pr-queue + task/ADR/RFC      执行循环
        │                         │
        └──────────────► 验证 ─► 提交 ─► 状态回写 ─► PR
```

每个新会话开工前：

1. 读 `docs/state/project-status.md` 和 `docs/state/pr-queue.md`；
2. 读 `AGENTS.md` 或对应工具的指令文件；
3. 执行 `git status --short`；
4. 如果请求不在队列中，先整理为 inbox/queue/task，再进入实现。

## 4. 立项判定

| 级别 | 判定标准 | 流程 |
| --- | --- | --- |
| 微改动 | ≤50 行；错别字、文档修正、小 bug；不改变对外行为或契约 | 说明改动点、验证方式，完成后提交 |
| 标准 PR | 一个可独立验收的功能切片 | 进入 `pr-queue.md`，必要时写 `docs/tasks/T-XXXX-*.md` |
| 重大变更 | 新增服务/包、外部依赖、中间件、公开协议破坏性变更、架构方向调整 | 先写 ADR/RFC，Owner 接受后再实现 |

吃不准时按更高一级处理。重大变更必须回答：为什么现有结构装不下、谁是第一个真实调用方、不做的代价是什么。

## 5. 标准 PR 执行循环

1. **复述任务**：目标、范围、范围外、文件、验证方式。
2. **一次只做一个 PR**：不要把多个机制模块塞进一个 diff。
3. **测试随行**：行为变化必须有确定性测试；优先测业务语义，不为覆盖率写空测试。
4. **范围纪律**：发现顺手优化超过 50 行时，记入 `inbox.md` 或新任务，不在当前 PR 做。
5. **diff 预算**：预计超过约 800 行时，先拆分。
6. **依赖变化先回写**：如果发现任务顺序或依赖变化，先更新 `pr-queue.md` / task，再继续。

## 6. 验证

- 有 `make check` 后，提交前必须运行并通过。
- 没有 `make check` 前，至少运行适合当前阶段的静态/文档检查，并如实说明没有运行代码测试的原因。
- 改对外接口契约时，更新 `docs/openapi/` 并运行契约漂移检查（待工具建立）。
- 不为通过门禁而修改门禁；门禁本身有问题，单独立项。

## 7. 提交

- 一个提交只做一件事，使用 conventional commits，例如 `docs: ...`、`feat(core): ...`、`test(runtime): ...`。
- 不提交无关文件、未跟踪临时文件、客户数据、secrets、IDE 副产物。
- 提交信息必须让下一个会话能理解“为什么改”和“改了什么”。

## 8. 状态回写

标准 PR 完成前必须检查：

1. `docs/state/pr-queue.md`：状态、验收方式、完成记录是否更新；
2. `docs/state/project-status.md`：当前状态和下一步是否仍正确；
3. `docs/state/risks.md`：新风险是否记录；
4. `docs/state/inbox.md`：未消化信息是否保留；
5. README / docs 索引是否指向新增文档。

不回写 = 没完成。下一个会话只认文件，不认聊天记录。

## 9. SessGraph 专用边界

默认预算为 0，必须先立项/ADR/RFC 的事项：

| 事项 | 原则 |
| --- | --- |
| 新增真实 LLM provider | P0 只用 FakeModel；真实 provider 后置到集成层。 |
| 新增数据库、Redis、队列、Web server | P0 只用 InMemory；外部系统需明确第一个调用方。 |
| 修改 Session / Signal / Event / Decision / Checkpoint 语义 | 属于公开协议或核心生命周期，必须 ADR/RFC。 |
| 新增多 Agent / Parent-Child Session | v0.6 方向，不能提前塞进 P0。 |
| 新增复杂抽象或插件系统 | 没有第二个真实调用方不抽象。 |

## 10. 红线

- 不把 token、secrets、客户数据写进代码、文档或提交。
- 不删除测试来让检查通过。
- 不在 core 中直接依赖 OpenAI、Anthropic、LangChain、LangGraph、FastAPI、Postgres、Redis、云 SDK。
- 不让 Tool 或 Child Session 直接改 Parent Session。
- 不绕过 ADR 修改公开协议。
- 不在一个 PR 中同时改多个核心机制模块。

## 11. 完成定义（DoD）

任务可声称完成，当且仅当：

1. 相关检查已运行并报告；
2. 新行为有测试，或明确说明当前 PR 为文档/规划无运行时代码；
3. diff 已提交；
4. 状态文件已回写；
5. 没有新增未记录的架构债或流程债。
