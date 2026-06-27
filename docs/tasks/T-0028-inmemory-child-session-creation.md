# T-0028: InMemory child session creation flow

> 状态: 已完成
> PR: PR-0026
> 最近更新: 2026-06-27

## 目标

基于 ADR-0009，实现 Parent 通过 `START_CHILD_SESSION` Decision 创建 Child Session 的最小 InMemory runtime flow。该任务只覆盖 child session creation 和 durable relationship，不处理 child result 回灌或 reducer merge。

## 范围

范围内：

- 新增 `DecisionKind.START_CHILD_SESSION` 及 payload 校验。
- 新增 `ChildSessionRecord`、child status enum、deterministic `child_session_id` 和 `InMemoryChildSessionStore`。
- `ActivationRunner` 在处理 `start_child_session` Decision 时创建 Child Session、Child initial `child_start` Signal 和 child relationship。
- Parent Event Log 追加 `child_session_started` Event。
- Parent Checkpoint state 记录 child relationship metadata。
- `start_child_session` action 在创建 Child 前接入现有 Safety/Auth policy gate；hard deny / approval-required 复用现有语义。
- 覆盖 deterministic tests：创建成功、idempotent duplicate、不授权拒绝、approval-required 暂停、Event append-only、Checkpoint round-trip。

范围外：

- 不实现 `child_result` Signal dispatcher。
- 不实现 Parent reducer merge、shared memory、cross-session context 或 capability delegation。
- 不实现 Child cancellation、timeout、fan-out/fan-in helper API。
- 不引入真实 worker、queue、database、server、provider、GUI 或 cloud。

## 依赖

- PR-0025 / ADR-0009 已完成并 accepted。
- PR-0019 到 PR-0023 Safety/Auth 本地确定性闭环已完成。
- 现有 Activation Runner、InMemory stores、FakeModel、Checkpoint 和 deterministic tests 已完成。

## 验证

- `make check`。
- 新增 child session creation 单元测试和 runner 集成测试。
- 不发起真实网络调用或真实 LLM 调用。

## 完成记录

- 新增 `DecisionKind.START_CHILD_SESSION` 及 payload 校验。
- 新增 `ChildSessionRecord`、`ChildSessionStatus`、deterministic `child_session_id_for_decision` 和 `InMemoryChildSessionStore`。
- `ActivationRunner` 支持创建 Child Session、enqueue `child_start` Signal，并在 Parent Event Log 追加 `child_session_started`。
- Parent Checkpoint state 记录 `child_session_record`、created Child Session 和 `child_start` Signal。
- `start_child_session` 接入现有 Safety/Auth policy gate，覆盖 hard deny、approval-required pause 和 approved dispatch。
- 新增 deterministic tests 覆盖 child record/store、runtime creation、authorization denial、grant allow、approval-required、approved dispatch、Event append-only 和 Checkpoint state。
- 未实现 `child_result` Signal dispatcher、Parent reducer merge、shared memory、capability delegation、真实 queue、database、server、provider 或 cloud。
