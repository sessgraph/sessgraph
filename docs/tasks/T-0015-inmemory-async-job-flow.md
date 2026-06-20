# T-0015: InMemory async job flow

> 状态: 拟议
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
