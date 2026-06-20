# T-0016: P1 后续方向重评估

> 状态: 已完成
> PR: PR-0014
> 最近更新: 2026-06-20

## 目标

在 PR-0013 完成后，重新评估 Memory + Context、Safety/Auth、Parent/Child Session 三个候选方向，确定下一组可独立 review 的 PR 切片。

## 范围

范围内：

- 对照项目里程碑、当前 runtime 能力和风险，评估三个候选方向。
- 固化推荐顺序、非目标和下一步 PR。
- 更新 `docs/state/`、PR 队列和文档索引。

范围外：

- 不实现 Memory + Context runtime 代码。
- 不实现 Safety/Auth。
- 不实现 Parent/Child Session。
- 不恢复 PR-0010 package/release hygiene，除非 Owner 完成 license 决策。

## 验证

- 文档 diff review。
- `git diff --check`。
- `make check`。

## 完成记录

- 新增 `docs/state/post-p1-reevaluation.md`。
- 结论：下一阶段优先进入 Memory + Context，先做 ADR，再做本地确定性实现。
- 新增后续 PR 切片：PR-0015 Memory + Context ADR、PR-0016 InMemory context builder、PR-0017 deterministic memory compaction example/test。
- Safety/Auth 和 Parent/Child Session 暂不启动，后续各自先走 ADR。
- 未实现 runtime 代码，未引入新依赖、provider、database、server、GUI 或 cloud。
