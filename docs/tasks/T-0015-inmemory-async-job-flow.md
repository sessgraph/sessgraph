# T-0015: InMemory async job flow

> 状态: 已完成
> PR: PR-0013
> 最近更新: 2026-06-20

## 目标

基于 async job/timer ADR，实现本地、确定性的 async job lifecycle，让 job result 以 Signal 形式回灌 Session。

## 范围

范围内：

- InMemory job store。
- job submitted/running/succeeded/failed 的最小状态转移。
- job result Signal 回灌。
- Event 和 Checkpoint 记录。
- 单元测试和最小 example 或 smoke test。

范围外：

- 不实现真实 worker pool。
- 不使用 production queue、database、server、cloud 或网络调用。
- 不实现 provider adapter。
- 不实现 timer flow。
- 不实现 approval/auth。

## 依赖

- PR-0011 async job/timer ADR 已完成。

## 验证

- job lifecycle store 测试。
- job result Signal 唤醒 Session 的 runner 测试。
- job failure 数据化结果测试。
- `make check`。

## 完成记录

- 新增 `DecisionKind.SUBMIT_JOB` 和 submit_job payload 校验。
- 新增 `src/sessgraph/jobs.py`，包含 `JobRecord`、`JobStatus`、`InMemoryJobStore` 和 `JobResultDispatcher`。
- Activation Runner 支持 `submit_job` Decision：只创建本地 JobRecord、记录 `job_submitted` Event，并将 Session 返回 `idle`。
- `JobResultDispatcher` 将 succeeded/failed JobRecord 转换为普通 `job_result` Signal，并记录 `job_result_enqueued` Event。
- 新增 `examples/async_job_session.py` 和 `tests/test_jobs.py`，覆盖 job lifecycle、result Signal 回灌、失败数据化结果，以及 runner 被 job_result Signal 唤醒。
- 遵循 ADR-0005：未实现真实 worker pool、production queue、database、server、cloud、provider adapter、timer flow 或 approval/auth。
