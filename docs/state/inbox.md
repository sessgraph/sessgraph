# Inbox

> 状态: 当前
> 最近更新: 2026-06-20

本文件保存未处理或部分处理的讨论输入。条目在 triage 到 project state、queue item、risk 或 task spec 前只追加、不删除。

## 2026-06-12 初始产品/流程讨论

来源：用户在任务请求中提供的 ChatGPT share link 和转录文本。Share 页面标题可见为“构建agent最小内核”，但当前环境无法在未登录情况下读取完整页面内容；因此用户提供的转录文本被视为权威来源。

### 提取出的决策

- 项目名：SessGraph。
- Package/repo/CLI 名称：`sessgraph`。
- 定位：面向长期运行 AI agent 的 durable session runtime。
- P0 从本地、确定性的 runtime primitives 开始，而不是 provider 或 deployment integrations。
- AI 开发必须受 issue/task card、allowed files、forbidden files、tests、PR review 和重大决策人类批准约束。
- Session lifecycle、Decision protocol、Event format、Checkpoint format、ToolSpec、storage interfaces、parent/child sessions 等架构变化需要 ADR/RFC 级处理。

### 提取出的初始任务序列

1. 建立仓库规划/治理文件。
2. 文档化核心概念。
3. 实现 P0 核心数据结构。
4. 实现 InMemory stores。
5. 用 FakeModel 和 final_answer Decision 实现最小 Activation Runner。
6. 增加同步 tool call flow。
7. 增加 wait/resume flow。
8. 增加 checkpoint recovery example/test。

## 2026-06-12 review follow-up

第一次 bootstrap PR 被认为不充分：它只是摘要化整理讨论，没有真正落地用户提供的中文统一开发流程。Follow-up 已将该流程转换为 `docs/DEVELOPMENT_PROCESS.md`，并补充文档索引、ADR/OpenAPI 事实源占位。

## 2026-06-12 中文文档本地化要求

Owner 明确要求：`AGENTS.md`、`CLAUDE.md` 也要中文，并且“都要中文的文档”。该要求已整理为 PR-0001G / T-0004，范围是现有面向贡献者和 AI agent 的 Markdown 文档中文化；不改变 runtime 规划和 P0 架构边界。

## 2026-06-20 P0 收尾审查整理

PR-0007 审查确认 PR-0002 到 PR-0006 的基本核心切片已完成。初始任务序列中的 “增加 checkpoint recovery example/test” 尚未实现，已整理为 PR-0008 / T-0010 拟议任务；license 决策仍保留在 ACT-0002。

## 2026-06-20 checkpoint recovery 立项完成

PR-0008 / T-0010 已补齐 checkpoint recovery example/test。初始任务序列中的 P0 本地核心闭环已完成；后续 package/release hygiene、async job/timer 或其他 v0.3+ 工作仍需重新立项。

## 2026-06-20 license 延后

Owner 明确表示 license 先延后，先做其他第二阶段工作。该输入已回写到 ACT-0002，并使 PR-0010 / T-0012 延后；后续优先推进 PR-0011 async job/timer ADR 以及 PR-0012 / PR-0013。
