# ADR-0002: P0 Activation Runner 最小循环

> 状态: Accepted
> 日期: 2026-06-14
> 相关任务: PR-0004 / `docs/tasks/T-0006-p0-activation-runner.md`

## 背景

PR-0002 已定义 P0 核心数据结构，PR-0003 已实现 InMemory stores。PR-0004 需要把 Signal、Session、Event、Decision 和 Checkpoint 连成最小可运行闭环，同时保持 provider-independent，不实现 tools、wait/resume、database、server 或真实 LLM provider。

## 决策

1. `ActivationRunner.run_once(session_id)` 每次最多处理一个 pending Signal。
2. 没有 pending Signal 时返回 inactive result，不调用 model，不写 Event，也不更新 Session。
3. Runner 读取 Session 后，构造 `running` Session 快照作为 model context；Decision 校验通过后，才以乐观并发方式提交 store 写入。
4. Model adapter 接收 `ActivationContext`，只能返回 `Decision`。
5. Runtime 校验 Decision 的 `session_id` 必须匹配当前 Session，且 P0 只分发 `final_answer` 和 `noop`。
6. 每次 activation 追加两个 Event：`signal_received` 和 `decision_produced`。
7. `final_answer` 将 Session 置为 `completed`；`noop` 将 Session 置回 `idle`。
8. 每次 activation 保存一个 Checkpoint，state 包含 session、signal、decision 和 event_ids。
9. Checkpoint id、Event id 和 FakeModel Decision id 使用确定性字符串，不使用随机数。
10. Decision 校验失败时不消耗 pending Signal，不写 Event，也不保存 Checkpoint。

## 理由

- 单次只处理一个 Signal 可以保持 P0 runner 小而可测，并符合“同一个 Session 同一时间只能有一个 writer”的约束。
- 让 model 只产出 Decision，避免 provider 或 FakeModel 直接修改 Session、Event Log 或 Checkpoint。
- 校验通过后再提交写入，避免坏 Decision 消耗 Signal 或留下不完整 Event Log。
- `signal_received` / `decision_produced` 是足够证明最小闭环的 Event 集合；tool、wait/resume、job/timer 事件留给后续 PR。
- Checkpoint state 选择直接保存可序列化 dict，便于后续 checkpoint recovery 测试复用。

## 后果

- P0 runner 当前不提供通用事务；如果 model 自身在校验前后抛出异常，错误会向调用方抛出。更完整的失败恢复语义后续单独立项。
- `final_answer` 与 `noop` 之外的 Decision kind 必须先扩展核心协议和测试。
- 真实 provider adapter、tool dispatch、wait/resume 和 async job/timer 不属于本 ADR。
