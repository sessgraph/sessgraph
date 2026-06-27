# 产品 PR 队列

> 状态: 当前
> 最近更新: 2026-06-27

本文件是可独立 review 的产品工作的权威队列。每个 PR 都应足够小，可以作为一个连贯变更被 review 和测试。

## 队列

| ID | 状态 | 标题 | 任务规格 | 范围 | 验证方式 |
| --- | --- | --- | --- | --- | --- |
| PR-0001 | 已完成 | 建立规划与 AI 治理文件 | `docs/tasks/T-0001-bootstrap-governance.md` | 仅 docs/state；不实现 runtime | Markdown/文件一致性检查；git diff review |
| PR-0001F | 已完成 | 处理规划 review 意见并新增中文统一流程 | `docs/tasks/T-0003-review-planning-files.md` | 仅 docs/process/index/ADR/OpenAPI 占位；不实现 runtime | Markdown/文件一致性检查；git diff review |
| PR-0001G | 已完成 | 将 agent 指令和规划文档统一为中文 | `docs/tasks/T-0004-localize-agent-docs.md` | root agent 指令、README、docs/state、docs/tasks 的中文化；不实现 runtime | Markdown/文件一致性检查；git diff review |
| PR-0002 | 已完成 | 定义 P0 核心数据结构 | `docs/tasks/T-0002-p0-data-model.md` | AgentDefinition、Session、Signal、Event、Decision、Checkpoint 数据类型和测试 | 构造、校验、序列化单元测试 |
| PR-0003 | 已完成 | 实现 InMemory stores | `docs/tasks/T-0005-p0-inmemory-stores.md` | SessionStore、InboxStore、EventStore、CheckpointStore | 包含幂等性的确定性 store 测试 |
| PR-0004 | 已完成 | 构建最小 Activation Runner 循环 | `docs/tasks/T-0006-p0-activation-runner.md` | FakeModel + final_answer Decision + basic example | 单元测试和 example smoke test |
| PR-0005 | 已完成 | 增加同步 tool execution flow | `docs/tasks/T-0007-sync-tool-execution.md` | ToolSpec、ToolRegistry、SyncToolExecutor | Tool 成功/失败测试 |
| PR-0006 | 已完成 | 增加 wait/resume user flow | `docs/tasks/T-0008-wait-resume-user-flow.md` | ask_user Decision 和 user_message Signal resume | waiting/resume 测试 |
| PR-0007 | 已完成 | P0 收尾审查与后续立项整理 | `docs/tasks/T-0009-p0-closeout-review.md` | 审查 PR-0002 到 PR-0006 的实现、测试、ADR 和状态一致性 | `make check`、basic example、compileall |
| PR-0008 | 已完成 | 增加 checkpoint recovery example/test | `docs/tasks/T-0010-checkpoint-recovery-example.md` | 从 latest Checkpoint 加载并恢复 Session 边界 | checkpoint recovery deterministic test 和 example smoke test |
| PR-0009 | 已完成 | 规划第二阶段 | `docs/tasks/T-0011-phase-two-planning.md` | 固化第二阶段目标、非目标、成功标准和后续 PR 切片 | 文档 diff review；`make check` |
| PR-0010 | 已完成 | package/release hygiene | `docs/tasks/T-0012-package-release-hygiene.md` | 最小 Python package 元数据、安装说明、import smoke test；license 使用 Apache-2.0 | `make check`、import smoke、example smoke |
| PR-0011 | 已完成 | ADR 定义 async job/timer 语义 | `docs/tasks/T-0013-async-job-timer-adr.md` | Signal/Event/Decision/Checkpoint/store 边界；不实现 runtime | ADR review |
| PR-0012 | 已完成 | InMemory timer flow | `docs/tasks/T-0014-inmemory-timer-flow.md` | 本地 timer store、due 查询、timer Signal 唤醒 Session | deterministic timer tests；`make check` |
| PR-0013 | 已完成 | InMemory async job flow | `docs/tasks/T-0015-inmemory-async-job-flow.md` | 本地 job lifecycle、job result Signal 回灌 Session | deterministic job tests；`make check` |
| PR-0014 | 已完成 | P1 后续方向重评估 | `docs/tasks/T-0016-post-p1-reevaluation.md` | 评估 Memory + Context、Safety/Auth、Parent/Child Session 并固化后续顺序；不实现 runtime | 文档 diff review；`make check` |
| PR-0015 | 已完成 | ADR 定义 Memory + Context 语义 | `docs/tasks/T-0017-memory-context-adr.md` | Context builder、memory record、compaction、Event/Checkpoint 边界；不实现 runtime | ADR review |
| PR-0016 | 已完成 | InMemory context builder | `docs/tasks/T-0018-inmemory-context-builder.md` | 基于 ADR 构造 deterministic ActivationContext 输入 | deterministic context tests；`make check` |
| PR-0017 | 已完成 | deterministic memory compaction example/test | `docs/tasks/T-0019-memory-compaction-example.md` | 本地 memory compaction 边界、Event/Checkpoint 示例和测试 | deterministic compaction tests；example smoke；`make check` |
| PR-0018 | 已完成 | ADR 定义 Safety/Auth 语义 | `docs/tasks/T-0020-safety-auth-adr.md` | Authorization、approval、capability grant、AuthContext 边界；不实现 runtime | ADR review；`make check` |
| PR-0019 | 已完成 | InMemory capability policy gate | `docs/tasks/T-0021-inmemory-capability-policy-gate.md` | 本地 AuthContext、CapabilityGrant 和 tool/job authorization gate | auth deterministic tests；runner integration tests；`make check` |
| PR-0020 | 已完成 | ADR 定义 approval flow 语义 | `docs/tasks/T-0022-approval-flow-adr.md` | ApprovalRequest、approval_result Signal、approval Event/Checkpoint 边界；不实现 runtime | ADR review；`make check` |
| PR-0021 | 已完成 | InMemory ApprovalRequest store | `docs/tasks/T-0023-inmemory-approval-request-store.md` | ApprovalRequest record、deterministic id、InMemory store；不实现 runner flow | approval store tests；`make check` |
| PR-0022 | 已完成 | Approval-required runner flow | `docs/tasks/T-0024-approval-required-runner-flow.md` | policy outcome 创建 ApprovalRequest、追加 `approval_requested` Event、Checkpoint 并暂停 action；不处理 `approval_result` | approval-required runner tests；`make check` |

## PR-0001 / PR-0001F / PR-0001G 完成记录

- `docs/state/` 包含当前项目状态、项目边界、队列、行动项、风险、inbox 和维护指南。
- 初始任务规格已覆盖治理 bootstrap、第一个 P0 data-model 工作、中文统一流程补齐和中文文档本地化修正。
- README 指向状态文件和开发流程。
- 根目录 `AGENTS.md` 和 `CLAUDE.md` 记录 AI 协作约束，并已改为中文。
- `docs/DEVELOPMENT_PROCESS.md` 记录中文统一开发流程。
- `docs/README.md` 索引文档表面。
- `docs/adr/0000-template.md` 和 `docs/openapi/README.md` 保留架构决策与契约事实源位置。
- 规划/bootstrap 变更均以文档提交完成。

## PR-0002 完成记录

- 新增 P0 core data structures：`AgentDefinition`、`Session`、`Signal`、`Event`、`Decision`、`Checkpoint`。
- 新增 ADR-0001，记录 Python 3.12、dataclasses、JSON-compatible `schema_version: 1`、Signal/Event 幂等字段和 Checkpoint 恢复边界。
- 新增标准库 `unittest` 覆盖构造校验、序列化 round-trip 和严格 JSON payload。
- 未实现 Activation Runner、InMemory stores、tool execution、wait/resume、provider integration、database 或 server mode。

## PR-0003 完成记录

- 新增 `InMemorySessionStore`、`InMemoryInboxStore`、`InMemoryEventStore`、`InMemoryCheckpointStore`。
- Store 层覆盖 Session revision 乐观并发、Signal idempotency、Event append-only sequence 和 Checkpoint latest lookup。
- 新增标准库 `unittest` 覆盖 store 行为和边界条件。
- 未实现 Activation Runner、FakeModel、tool execution、wait/resume、provider integration、database 或 server mode。

## PR-0004 完成记录

- 新增 `ActivationRunner`、`ActivationContext`、`ActivationResult` 和 `FakeModel`。
- Runner 支持一个 pending Signal 激活一次 Session，分发 `final_answer` / `noop` Decision，记录 `signal_received` / `decision_produced` Event，并保存 Checkpoint。
- 新增 ADR-0002，记录 P0 Activation Runner 最小循环语义。
- 新增 `examples/basic_session.py` 和 example smoke test。
- 未实现 tool execution、wait/resume、async job/timer、provider integration、database 或 server mode。

## PR-0005 完成记录

- 新增 `DecisionKind.TOOL_CALL`、`ToolSpec`、`ToolRegistry`、`SyncToolExecutor` 和 `ToolResult`。
- Runner 支持同步分发 `tool_call` Decision，记录 `tool_call_requested` / `tool_result_produced` Event，并将 ToolResult 回灌为 `tool_result` Signal。
- 新增 ADR-0003，记录同步 tool execution 语义。
- 新增标准库 `unittest` 覆盖工具注册、成功执行、失败结果、未知工具和 runner tool flow。
- 未实现 wait/resume、async job/timer、approval/authorization、provider integration、database 或 server mode。

## PR-0006 完成记录

- 新增 `DecisionKind.ASK_USER` 和 ask_user payload 校验。
- Runner 支持 `ask_user` Decision，将 Session 置为 `waiting` 并保存 Checkpoint。
- `user_message` Signal 可恢复 waiting Session 并继续 activation。
- 新增 ADR-0004，记录 P0 wait/resume user flow 语义。
- 新增标准库 `unittest` 覆盖 ask_user、waiting inactive 和 user_message resume。
- 未实现 UI、timeout/timer、approval/authorization、provider integration、database 或 server mode。

## PR-0007 完成记录

- 对照 P0 范围、任务规格和 ADR 审查 PR-0002 到 PR-0006。
- 确认基本 runtime core 已覆盖 data model、InMemory stores、Activation Runner、FakeModel、Checkpoint save、同步 tool execution 和 wait/resume。
- 运行 `make check`、basic example 和 compileall，均通过。
- 将 `checkpoint recovery example/test` 缺口整理为 PR-0008 / T-0010。
- 未实现新的 runtime 行为、provider、database、server、GUI 或 async job/timer。

## PR-0008 完成记录

- 新增 `examples/checkpoint_recovery.py`，演示从 latest Checkpoint 恢复 Session snapshot。
- 新增 `tests/test_checkpoint_recovery.py`，覆盖 latest checkpoint load、Session recovery、event boundary 和 Checkpoint round-trip recovery。
- 不新增 public helper，不改变 Checkpoint 公开序列化格式。
- 未实现 file persistence、database、queue、crash recovery framework、provider、server、GUI 或 async job/timer。

## PR-0009 完成记录

- 新增 `docs/state/phase-two-plan.md`，定义第二阶段 / P1 为 “本地调度语义与开源可用性”。
- 新增 PR-0010 到 PR-0013 拟议切片，覆盖 package/release hygiene、async job/timer ADR、InMemory timer flow 和 InMemory async job flow。
- 明确第二阶段仍不实现真实 provider、database、production queue、server、cloud、GUI、memory/context 或 parent/child session。
- 未实现 runtime 代码。

## PR-0010 延后记录

- Owner 已明确 license 决策先延后，因此 PR-0010 package/release hygiene 随 ACT-0002 延后。
- 延后期间不能声称仓库已具备完整开源发布卫生。

## PR-0010 完成记录

- Owner 已确认 license 使用 Apache-2.0。
- 新增根目录 `LICENSE`。
- 新增最小 `pyproject.toml`，声明 package metadata、Python 3.12 下限、Apache-2.0 license 和 `src/` package discovery。
- README 新增本地 editable install、测试、example 和 license 说明。
- 新增 import smoke test 覆盖 `sessgraph` public package import。
- `.gitignore` 新增本地 venv、build、dist 和 egg-info 产物。
- 未发布到 PyPI，未新增 CI，未引入 runtime 依赖，未修改 runtime 语义。

## PR-0011 完成记录

- 新增 ADR-0005，定义 P1 async job/timer 语义。
- Timer 决策：P1 由 runtime-side InMemory timer store 管理，到期后 enqueue `timer` Signal；不新增 timer Decision kind。
- Async job 决策：新增 `DecisionKind.SUBMIT_JOB`，runtime 创建 JobRecord，完成后 enqueue `job_result` Signal。
- Job failure 决策：作为 `job_result` 数据化结果，不自动将 Session 置为 `failed`。
- 明确 PR-0012 / PR-0013 仍只允许 InMemory stores、FakeModel 和 deterministic tests，不引入真实 queue、database、worker、server 或 provider。

## PR-0012 / PR-0013 ADR 约束记录

- PR-0012 和 PR-0013 必须遵循 ADR-0005。
- PR-0012 与 PR-0013 应拆开实现，避免在一个 PR 中同时修改 timer 和 job 两个核心机制。

## PR-0012 完成记录

- 新增 `TimerRecord`、`TimerStatus`、`InMemoryTimerStore` 和 `TimerDispatcher`。
- `TimerDispatcher` 将 due TimerRecord 转换为普通 `timer` Signal 并 enqueue 到 Session inbox。
- Runner 被 timer Signal 唤醒后复用现有 `signal_received` / `decision_produced` Event 和 Checkpoint 语义。
- 新增 `examples/timer_session.py` 和 `tests/test_timers.py`。
- 未新增 timer Decision kind，未实现 async job、真实 scheduler、production queue、database、server 或 cloud。

## PR-0013 完成记录

- 新增 `DecisionKind.SUBMIT_JOB`，并校验 `job_type`、`arguments` 和可选 `idempotency_key`。
- 新增 `JobRecord`、`JobStatus`、`InMemoryJobStore` 和 `JobResultDispatcher`。
- Runner 对 `submit_job` Decision 只创建本地 JobRecord，记录 `job_submitted` Event，并将 Session 返回 `idle`。
- `JobResultDispatcher` 将 succeeded/failed JobRecord 转换为普通 `job_result` Signal，并记录 `job_result_enqueued` Event。
- 新增 `examples/async_job_session.py` 和 `tests/test_jobs.py`。
- 未实现真实 worker pool、production queue、database、server、cloud、provider adapter、timer flow 或 approval/auth。

## PR-0014 完成记录

- 新增 `docs/state/post-p1-reevaluation.md`，对比 Memory + Context、Safety/Auth、Parent/Child Session。
- 结论：下一阶段优先进入 Memory + Context；先做 ADR，再做本地确定性实现。
- 新增 PR-0015 到 PR-0017 拟议切片，覆盖 Memory + Context ADR、InMemory context builder 和 deterministic memory compaction example/test。
- Safety/Auth 暂不混入 Memory + Context，后续单独 ADR。
- Parent/Child Session 暂缓，等 context、capability/approval 和 reducer merge boundary 更清楚后再立项。

## PR-0015 完成记录

- 新增 ADR-0006，定义 Memory + Context 语义。
- 决定 P1 后续先支持 Session-scoped memory；Agent-scoped / cross-session memory 后续单独 ADR。
- 决定 ContextSnapshot 是 activation-time 派生对象，不作为独立 durable store 主记录。
- 决定 compaction 输出写入 MemoryRecord，并追加 `memory_compacted` Event、保存 Checkpoint 作为恢复边界。
- 决定 model adapter 接收 ContextSnapshot 作为 canonical context，现有 `ActivationContext.events` 迁移为 event window 兼容视图。
- 未实现 runtime 代码，未引入真实 summarizer、embedding、vector database、Safety/Auth 或 Parent/Child Session。

## PR-0016 完成记录

- 新增 `MemoryRecord`、`InMemoryMemoryStore`、`ContextSnapshot`、`ContextBuilder` 和 deterministic `memory_id_for_record`。
- `ContextBuilder` 从 Event Log、Session-scoped memory records 和 latest Checkpoint 构造 activation-time ContextSnapshot。
- Event window 按 `sequence` 升序，memory records 按 `(created_at, memory_id)` 升序；支持 `max_events` window metadata。
- `ActivationRunner` 可接入 `ContextBuilder`，并将 `ContextSnapshot.event_window` 作为 `ActivationContext.events` 兼容视图。
- Activation Checkpoint state 会记录本次 context snapshot metadata，包括 event ids、memory ids、latest checkpoint、ordering 和 limits。
- 新增 context round-trip、deterministic ordering/windowing、memory store 幂等性和 runner 集成测试；`make check` 通过。
- 未实现 memory compaction、真实 summarizer、embedding、vector database、Safety/Auth、Parent/Child Session、providers、databases 或 server mode。

## PR-0017 完成记录

- 新增 `MemoryCompactor`、`DeterministicCompactionPolicy` 和 `MemoryCompactionResult`，用于本地 deterministic memory compaction fixture。
- Compaction 输出 durable `MemoryRecord`，追加 `memory_compacted` Event，并保存 compaction Checkpoint。
- `memory_compacted` Event payload 包含 `memory_id`、`source_event_ids`、`supersedes_memory_ids` 和 policy metadata。
- Compaction Checkpoint state 记录新 memory、active memory ids、source event ids、supersedes memory ids 和 compaction Event id。
- `InMemoryMemoryStore` 支持 active memory view；`ContextBuilder` 只把未被 supersede 的 memory records 放入 ContextSnapshot。
- 新增 `examples/memory_compaction_session.py` 和 deterministic compaction / example smoke tests；`make check` 通过。
- 未实现真实 summarizer、embedding、vector database、production token accounting、Safety/Auth、Parent/Child Session、providers、databases 或 server mode。

## PR-0018 完成记录

- 新增 ADR-0007，定义 Safety/Auth 语义。
- 决定 Safety/Auth 是 runtime-side policy boundary，model 不能通过 Decision、prompt 或 payload 自授权。
- 决定首个实现先支持 Session-scoped CapabilityGrant；Agent/global/cross-session grants 后续单独 ADR。
- 决定 AuthContext 由宿主 runtime 在 Signal 进入边界时提供，不信任 model payload 自报身份。
- 决定 Approval 是 runtime-side policy gate，不新增 Decision kind；approval result 通过普通 Signal 回灌。
- 决定 authorization denial / approval-required 是数据化 runtime outcome，记录 Event 和 Checkpoint，不等同 runtime invariant failure。
- 未实现 runtime 代码、真实 identity provider、OAuth/OIDC、IAM、policy DSL、ApprovalRequest store 或 Parent/Child Session。

## PR-0019 完成记录

- 新增 `AuthContext`、`CapabilityGrant`、`PolicyDecision`、`InMemoryCapabilityGrantStore` 和 `InMemoryPolicyGate`。
- `AuthContext` 是 activation-time 输入；`ActivationRunner.run_once(..., auth_context=...)` 将其传入 model context 和 policy gate。
- Runtime 在 `tool_call` / `submit_job` Decision schema 校验后、action 分发前执行 authorization gate。
- policy gate 默认 deny；只有匹配 Session-scoped active grant、actor subject、action kind、resource subset 和 required scopes 时才允许分发。
- 拒绝授权时追加 `authorization_denied` Event，把 `policy_decision` 写入 Checkpoint，并跳过 tool execution / job creation。
- 新增 deterministic auth model/store tests 和 runner integration tests；`make check` 通过。
- 未实现 approval flow、ApprovalRequest store、真实 identity provider、OAuth/OIDC、IAM、production policy DSL、Parent/Child Session 或 capability delegation。

## PR-0020 完成记录

- 新增 ADR-0008，定义 approval flow 语义。
- 决定 approval-required 是 runtime policy outcome，不新增 Decision kind。
- 决定 ApprovalRequest 是 durable record；approval result 通过普通 `approval_result` Signal 回灌 Session。
- 决定 approval request / resolved 都必须追加 Event，并保存 Checkpoint 作为恢复边界。
- 明确后续首个实现应保持 InMemory、FakeModel 和 deterministic tests。
- 未实现 runtime 代码、ApprovalRequest store、真实 identity provider、production policy、Parent/Child Session 或 capability delegation。

## PR-0021 完成记录

- 新增 `ApprovalStatus`、`ApprovalRequest` 和 deterministic `approval_request_id`。
- 新增 `InMemoryApprovalRequestStore`，覆盖 create idempotency、get/list lookup、pending ordering、resolve concurrency 和 terminal immutability。
- 新增 public package exports。
- 新增 deterministic approval model/store tests。
- 未实现 Activation Runner approval-required 分支、`approval_result` Signal dispatch、approval Event 或 Checkpoint 保存。

## PR-0022 完成记录

- `PolicyDecision` 新增 `requires_approval` outcome 标志，hard deny 行为保持 `authorization_denied` 不变。
- `InMemoryPolicyGate` 可通过 CapabilityGrant `constraints.requires_approval=true` 返回 approval-required outcome。
- `ActivationRunner` 对 approval-required 的 `tool_call` / `submit_job` 创建 `ApprovalRequest`、追加 `approval_requested` Event、保存 Checkpoint，并将 Session 置为 `waiting`。
- approval-required 时不会执行 tool，也不会创建 job。
- 新增 deterministic policy/runner tests；`make check` 通过。
- 未实现 `approval_result` Signal dispatch、approved dispatch、denied skip、duplicate result idempotency 或 stale result ignored。

## 队列纪律

- 一个 PR 只实现一个切片。
- 如果切片触及公开协议语义，先新增或更新 ADR。
- 如果 PR 预计超过约 800 行变更，先拆分再实现。
