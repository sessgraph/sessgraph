# T-0008: 增加 wait/resume user flow

> 状态: 已完成
> PR: PR-0006
> 最近更新: 2026-06-14

## 目标

实现最小 wait/resume user flow，让 model 可以返回 `ask_user` Decision，runtime 将 Session 置为 waiting；后续 `user_message` Signal 可以恢复同一个 Session 并继续 activation。

## 范围

范围内：

- `DecisionKind.ASK_USER`。
- `ask_user` Decision payload 校验。
- FakeModel deterministic ask_user。
- Activation Runner 对 `ask_user` 的分发。
- Session `waiting` 状态更新。
- `user_message` Signal resume 测试。
- Checkpoint 保存 waiting 和 resumed 状态。

范围外：

- UI。
- 人类审批系统。
- timeout/timer。
- async job。
- provider integration。
- database、queue、server 或 cloud backend。

## Runtime 语义

- `ask_user` Decision payload 必须包含非空 `question`。
- Runner 处理 `ask_user` 后，将 Session 状态置为 `waiting`。
- waiting Session 不会自动继续；只有新的 pending Signal 才会再次激活。
- `user_message` Signal 是 P0 resume 输入，不需要特殊 store 类型。
- resume 后 model 可以返回任意 P0 支持的 Decision，例如 `final_answer`。

## 验证

- `ask_user` Decision 构造校验测试。
- runner ask_user 进入 waiting 测试。
- no pending Signal 时 waiting Session 保持 inactive 测试。
- enqueue `user_message` 后 resume 并 final_answer 测试。
- 不使用网络、API key、数据库或真实 model 调用。

## 完成记录

- 扩展 `DecisionKind.ASK_USER`。
- 扩展 `FakeModel` 支持 deterministic ask_user。
- 扩展 `ActivationRunner` 支持 waiting 状态。
- 新增 `tests/test_wait_resume.py`。
- 新增 `docs/adr/0004-wait-resume-user-flow.md`。
