# 产品 PR 队列

> 状态: 当前
> 最近更新: 2026-06-12

本文件是可独立 review 的产品工作的权威队列。每个 PR 都应足够小，可以作为一个连贯变更被 review 和测试。

## 队列

| ID | 状态 | 标题 | 任务规格 | 范围 | 验证方式 |
| --- | --- | --- | --- | --- | --- |
| PR-0001 | 已完成 | 建立规划与 AI 治理文件 | `docs/tasks/T-0001-bootstrap-governance.md` | 仅 docs/state；不实现 runtime | Markdown/文件一致性检查；git diff review |
| PR-0001F | 已完成 | 处理规划 review 意见并新增中文统一流程 | `docs/tasks/T-0003-review-planning-files.md` | 仅 docs/process/index/ADR/OpenAPI 占位；不实现 runtime | Markdown/文件一致性检查；git diff review |
| PR-0001G | 已完成 | 将 agent 指令和规划文档统一为中文 | `docs/tasks/T-0004-localize-agent-docs.md` | root agent 指令、README、docs/state、docs/tasks 的中文化；不实现 runtime | Markdown/文件一致性检查；git diff review |
| PR-0002 | 已完成 | 定义 P0 核心数据结构 | `docs/tasks/T-0002-p0-data-model.md` | AgentDefinition、Session、Signal、Event、Decision、Checkpoint 数据类型和测试 | 构造、校验、序列化单元测试 |
| PR-0003 | 拟议 | 实现 InMemory stores | TBD | SessionStore、InboxStore、EventStore、CheckpointStore | 包含幂等性的确定性 store 测试 |
| PR-0004 | 拟议 | 构建最小 Activation Runner 循环 | TBD | FakeModel + final_answer Decision + basic example | 单元测试和 example smoke test |
| PR-0005 | 拟议 | 增加同步 tool execution flow | TBD | ToolSpec、ToolRegistry、SyncToolExecutor | Tool 成功/失败测试 |
| PR-0006 | 拟议 | 增加 wait/resume user flow | TBD | ask_user Decision 和 user_message Signal resume | waiting/resume 测试 |

## PR-0001 / PR-0001F / PR-0001G 完成记录

- `docs/state/` 包含当前项目状态、项目边界、队列、行动项、风险、inbox 和维护指南。
- 初始任务规格已覆盖治理 bootstrap、第一个 P0 data-model 工作、中文统一流程补齐和中文文档本地化修正。
- README 指向状态文件和开发流程。
- 根目录 `AGENTS.md` 和 `CLAUDE.md` 记录 AI 协作约束，并已改为中文。
- `docs/DEVELOPMENT_PROCESS.md` 记录中文统一开发流程。
- `docs/README.md` 索引文档表面。
- `docs/adr/0000-template.md` 和 `docs/openapi/README.md` 保留架构决策与契约事实源位置。
- 规划/bootstrap 变更均以文档提交完成。

## PR-0002 完成记录

- 新增 P0 core data structures：`AgentDefinition`、`Session`、`Signal`、`Event`、`Decision`、`Checkpoint`。
- 新增 ADR-0001，记录 Python 3.12、dataclasses、JSON-compatible `schema_version: 1`、Signal/Event 幂等字段和 Checkpoint 恢复边界。
- 新增标准库 `unittest` 覆盖构造校验、序列化 round-trip 和严格 JSON payload。
- 未实现 Activation Runner、InMemory stores、tool execution、wait/resume、provider integration、database 或 server mode。

## 队列纪律

- 一个 PR 只实现一个切片。
- 如果切片触及公开协议语义，先新增或更新 ADR。
- 如果 PR 预计超过约 800 行变更，先拆分再实现。
