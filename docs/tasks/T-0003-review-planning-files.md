# T-0003: 补齐中文流程规划文件

> 状态: 已完成
> PR: PR-0001-follow-up
> 最近更新: 2026-06-12

## 目标

修正首次规划 PR 过于偏摘要化、英文化的问题，把用户提供的“统一开发流程”真正落到仓库文档中，并补齐文档索引、ADR 模板和 OpenAPI 契约占位。

## 范围

范围内：

- 新增 `docs/DEVELOPMENT_PROCESS.md`，用中文定义 SessGraph 统一开发流程。
- 新增 `docs/README.md` 文档索引。
- 新增 `docs/adr/0000-template.md` ADR 模板。
- 新增 `docs/openapi/README.md`，明确 P0 暂无 OpenAPI 契约。
- 更新 README 和 agent 指令，让新会话优先阅读统一流程和事实源。
- 回写 `docs/state/` 状态、队列和行动项。

范围外：

- 运行时代码。
- Python 包结构。
- CI / Makefile。
- 真实 LLM、数据库、Web server、云部署、多 Agent 实现。

## 验证

- `git diff --check`。
- 文件存在性检查。
- 人工检查状态文件与新增文档链接一致。
