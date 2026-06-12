# T-0004: 将 agent 指令和规划文档统一为中文

> 状态: 已完成
> PR: PR-0001G
> 最近更新: 2026-06-12

## 目标

响应 Owner “AGENTS.md、CLAUDE.md 也要中文；都要中文的文档”的要求，将现有面向贡献者和 AI agent 的 Markdown 文档改为中文为主，避免中英文混杂造成后续会话理解不一致。

## 范围

范围内：

- 将根目录 `AGENTS.md` 改为中文。
- 将根目录 `CLAUDE.md` 改为中文。
- 将 README、`docs/state/`、`docs/tasks/` 中仍以英文为主的标题、说明、表格字段和流程文字改为中文。
- 保留 SessGraph、P0、Session、Signal、Event、Decision、Checkpoint、ADR、OpenAPI 等稳定技术名词。
- 回写 `docs/state/project-status.md`、`docs/state/pr-queue.md` 和 `docs/state/action-queue.md`。

范围外：

- Runtime 代码。
- Python 包结构。
- CI / Makefile。
- 真实 LLM、数据库、Web server、云部署、多 Agent 实现。
- 改变 P0 任务顺序或架构边界。

## 验证

- `git diff --check`。
- Markdown 文件存在性检查。
- 使用文本搜索确认现有 Markdown 文档没有明显英文流程标题残留；技术名词除外。
