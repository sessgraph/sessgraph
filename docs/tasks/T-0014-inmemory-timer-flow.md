# T-0014: InMemory timer flow

> 状态: 已完成
> PR: PR-0012
> 最近更新: 2026-06-20

## 目标

基于 async job/timer ADR，实现本地、确定性的 timer flow，让 timer 到期后以 Signal 形式唤醒 Session。

## 范围

范围内：

- InMemory timer store 或等价本地 timer 队列。
- deterministic clock 驱动的 due timer 查询。
- timer 到期后生成 `timer` Signal。
- Event 和 Checkpoint 记录。
- 单元测试和最小 example 或 smoke test。

范围外：

- 不使用真实 wall-clock scheduler。
- 不使用 cron、OS timer、background thread 或 production queue。
- 不新增 database、server、cloud 或网络调用。
- 不实现 async job。

## 依赖

- PR-0011 async job/timer ADR 已完成。

## 验证

- timer enqueue/due/list/idempotency 测试。
- runner 被 timer Signal 唤醒的测试。
- `make check`。

## 完成记录

- 新增 `src/sessgraph/timers.py`，包含 `TimerRecord`、`TimerStatus`、`InMemoryTimerStore` 和 `TimerDispatcher`。
- 新增 `examples/timer_session.py`，演示 due timer 转换为 `timer` Signal 并唤醒 Session。
- 新增 `tests/test_timers.py`，覆盖 timer round-trip、schedule/list_due/idempotency、mark_fired、dispatcher 一次性入队，以及 timer Signal 触发 Activation Runner。
- 遵循 ADR-0005：未新增 timer Decision kind，timer 激活复用现有 `signal_received` / `decision_produced` Event 和 Checkpoint 保存路径。
- 未实现真实 wall-clock scheduler、cron、background thread、production queue、database、server、cloud 或 async job。
