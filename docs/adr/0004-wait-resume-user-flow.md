# ADR-0004: P0 Wait/Resume User Flow

> 状态: Accepted
> 日期: 2026-06-14
> 相关任务: PR-0006 / `docs/tasks/T-0008-wait-resume-user-flow.md`

## 背景

PR-0004 已实现最小 Activation Runner，PR-0005 已实现同步 tool execution。PR-0006 需要让 Session 可以在需要用户输入时暂停，并在后续用户消息到达后恢复。该能力仍必须保持本地、确定性、provider-independent，不引入 UI、server、database、queue、真实 provider 或 timer。

## 决策

1. 新增 `DecisionKind.ASK_USER`，payload 必须包含非空 `question`。
2. Runtime 分发 `ask_user` 后，将 Session 状态置为 `waiting`。
3. `ask_user` 与其他 Decision 一样记录 `signal_received` 和 `decision_produced` Event，并保存 Checkpoint。
4. waiting Session 不自动继续；只有新的 pending Signal 才能再次激活。
5. P0 resume 使用普通 `user_message` Signal，不新增专用 resume store。
6. resume 后 model 可以返回任意当前支持的 Decision，例如 `final_answer`、`tool_call` 或再次 `ask_user`。

## 理由

- 将用户回复建模为 Signal，保持 “Signal 是唯一外部触发入口” 的核心原则。
- `waiting` 是 Session durable state，不依赖长运行进程或 UI 连接。
- 不引入专用 resume store，可以复用 InboxStore 的 idempotency 与 FIFO 行为。

## 后果

- P0 不处理 timeout、reminder、approval 或用户身份权限。
- 多轮 ask_user 可以通过重复 `ask_user` / `user_message` activation 表达。
- 后续如果要引入 UI/server，需要在 P0 runtime 之外适配 Signal 写入。
