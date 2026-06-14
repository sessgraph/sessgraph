# T-0006: 构建最小 Activation Runner 循环

> 状态: 已完成
> PR: PR-0004
> 最近更新: 2026-06-14

## 目标

实现最小 Activation Runner，让一个 pending Signal 可以激活 Session，经 FakeModel 产出 Decision，再由 runtime 校验 Decision、记录 Event、更新 Session，并保存 Checkpoint。

## 范围

范围内：

- `ActivationRunner`。
- `ActivationContext` / `ActivationResult`。
- `FakeModel`。
- `final_answer` 和 `noop` Decision 分发。
- Signal received / Decision produced Event 记录。
- Session revision 乐观更新。
- Checkpoint save。
- 最小 `examples/basic_session.py`。
- 确定性单元测试和 example smoke test。

范围外：

- Tool execution。
- Wait/resume。
- Async job/timer。
- Parent/child Session 编排。
- 真实 LLM provider。
- Database、queue、server 或 cloud backend。

## Runtime 语义

- Runner 每次只处理一个 Session 的一个 pending Signal。
- 没有 pending Signal 时返回 inactive result，不调用 model，不写 Event。
- Runner 构造 running Session 快照给 model，但只有 Decision 校验通过后才提交 store 写入。
- Model adapter 只返回 Decision；runtime 校验 Decision，不让 model 直接修改 store。
- P0 支持 `final_answer` 和 `noop`。
- 每次 activation 追加 `signal_received` 和 `decision_produced` 两个 Event。
- 每次 activation 保存一个 Checkpoint，Checkpoint state 包含 session、signal、decision 和 event_ids。
- Decision 校验失败时不消耗 pending Signal，不写 Event，也不保存 Checkpoint。

## 验证

- final_answer activation 测试。
- noop activation 测试。
- no pending signal 测试。
- invalid Decision 拒绝且不消耗 Signal 的测试。
- example smoke test。
- 不使用网络、API key、数据库或真实 model 调用。

## 完成记录

- 新增 `src/sessgraph/runtime.py`。
- 新增 `src/sessgraph/fake_model.py`。
- 新增 `tests/test_activation_runner.py`。
- 新增 `examples/basic_session.py`。
- 新增 `docs/adr/0002-p0-activation-runner.md`。
