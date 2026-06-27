# 第二阶段规划

> 状态: 当前
> 最近更新: 2026-06-27

## 阶段名称

**第二阶段 / P1: 本地调度语义与开源可用性。**

P0 已证明 durable Session runtime 的本地核心闭环：Session、Signal、Event、Decision、Checkpoint、InMemory stores、FakeModel、Activation Runner、同步 tool execution、wait/resume 和 checkpoint recovery example/test。

第二阶段的目标是在不引入生产基础设施的前提下，让这个本地核心具备下一类长期运行 agent 必需能力：可被 timer 或 async job result 再次唤醒，并让仓库更接近可被外部开发者本地安装、测试和 review。

## 阶段目标

1. **开源可用性基础**：Owner 已确认 Apache-2.0；package/release hygiene 已补齐最小文件和验证入口，让用户可以用稳定命令安装、导入、运行测试和 example。
2. **Async job/timer 语义先行**：先写 ADR 定义 job/timer 的 Signal、Event、Decision 和 Checkpoint 边界，再实现代码。
3. **仍然本地确定性**：第二阶段仍使用 FakeModel、InMemory stores 和 deterministic tests，不引入真实 queue、database、provider、server 或 cloud。
4. **保持 Session 中心原则**：timer、job result 和 tool result 一样，最终都必须以 Signal 形式唤醒 Session；外部执行器不能直接修改 Session state。

## 非目标

第二阶段不包含：

- 真实 LLM provider adapter。
- Database、Redis、production queue 或 file persistence backend。
- FastAPI/web server mode 或 OpenAPI 契约。
- Cloud deployment。
- GUI。
- Memory/context compaction。
- Parent/child Session 编排。
- 复杂 tool schema validation、approval 或 authorization。

## 成功标准

第二阶段完成时应满足：

- 仓库有明确 license/packaging 状态。
- `sessgraph` 可以用本地开发方式安装或导入，并保留 `make check` 作为确定性验证入口。
- async job/timer 的公开语义有 ADR 记录。
- timer 能通过本地 deterministic clock 触发 `timer` Signal 并唤醒 Session。
- async job 能通过 InMemory job store 表达 submitted/running/succeeded/failed 边界，并以 `job_result` Signal 回灌 Session。
- 每个能力都有 deterministic unit tests 和最小 example 或 smoke coverage。
- 未引入真实 provider、database、queue、server、cloud 或网络调用。

## 建议 PR 切片

| ID | 状态 | 标题 | 目标 |
| --- | --- | --- | --- |
| PR-0009 | 已完成 | 规划第二阶段 | 固化本文件和后续队列。 |
| PR-0010 | 已完成 | package/release hygiene | 使用 Apache-2.0，补齐最小 Python package 元数据、安装说明和 import smoke test。 |
| PR-0011 | 已完成 | ADR: async job/timer 语义 | 定义 timer/job 的 Signal、Event、Decision、Checkpoint 边界，不写 runtime 代码。 |
| PR-0012 | 已完成 | InMemory timer flow | 基于 ADR 实现本地 timer scheduling 和 deterministic tests。 |
| PR-0013 | 已完成 | InMemory async job flow | 基于 ADR 实现本地 async job lifecycle、job result Signal 回灌和 deterministic tests。 |

## 阶段顺序

1. PR-0010 已在 Owner 确认 Apache-2.0 后完成。
2. PR-0011 已完成，PR-0012 / PR-0013 已按 ADR-0005 拆分落地。
3. PR-0012 / PR-0013 完成后，PR-0014 已完成 P1 后续方向重评估；结论写入 `docs/state/post-p1-reevaluation.md`。

## 当前约束

- ACT-0002 已完成，PR-0010 已完成。
- 第二阶段仍不允许真实网络、真实 LLM、数据库或生产队列。
- 如果实现需要修改 Session、Signal、Event、Decision 或 Checkpoint 的公开字段，必须先更新或新增 ADR。

## 后续衔接

P1 后续方向重评估结论是优先进入 Memory + Context。PR-0015 Memory + Context ADR、PR-0016 InMemory context builder 和 PR-0017 deterministic memory compaction example/test 已完成。PR-0018 到 PR-0023 已完成 Safety/Auth ADR、InMemory capability policy gate、approval flow ADR、InMemory ApprovalRequest store、approval-required runner branch 和 approval result runtime flow。PR-0024 已完成 Safety/Auth 收尾审查，PR-0025 已完成 Parent/Child Session ADR；下一步进入最小 InMemory child session creation。真实 provider、production policy、database、server 和 cloud 仍需后续单独立项。
