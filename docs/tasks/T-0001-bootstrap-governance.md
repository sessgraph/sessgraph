# T-0001: 建立规划与治理文件

> 状态: 已完成
> PR: PR-0001
> 最近更新: 2026-06-12

## 目标

将最初的 SessGraph 产品/流程讨论转换为仓库文件，让未来 AI 会话和人类贡献者共享同一个事实源。

## 范围

范围内：

- 更新 README，说明项目定位并链接规划文件。
- 为 Codex 兼容 agent 和 Claude Code 增加根目录 AI 指令文件。
- 增加 `docs/state/` 文件，记录项目状态、当前状态、队列、行动项、风险、inbox 和维护规则。
- 增加初始任务规格，覆盖治理 bootstrap 和第一个 P0 实现切片。

范围外：

- Runtime 代码。
- Python 包骨架。
- CI/tooling 配置。
- 真实 LLM、数据库、server、cloud、GUI 或多 Agent 实现。
- 最终 license 决策。

## 预计修改文件

- `README.md`。
- `AGENTS.md`。
- `CLAUDE.md`。
- `docs/state/README.md`。
- `docs/state/project-state.md`。
- `docs/state/project-status.md`。
- `docs/state/pr-queue.md`。
- `docs/state/action-queue.md`。
- `docs/state/risks.md`。
- `docs/state/inbox.md`。
- `docs/tasks/T-0001-bootstrap-governance.md`。
- `docs/tasks/T-0002-p0-data-model.md`。

## 验证

- 人工检查 Markdown 内部一致性。
- 运行文件列表检查，确认预期规划文件存在。
- 提交前运行 `git diff --check`。

## 完成定义

- 规划文件存在，并且当前状态与下一步 PR 一致。
- README 指向规划文件。
- 根目录 AI 指令文件已覆盖 Codex 兼容 agent 和 Claude Code。
- 风险和原始讨论笔记已记录。
- 变更已提交。
