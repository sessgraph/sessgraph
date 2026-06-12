# CLAUDE.md

## 项目身份

SessGraph 是基础设施项目：一个面向长期运行 agent 的 durable Session runtime。
它不是业务应用，仓库中不应包含业务特定逻辑。

## 核心心智模型

Agent 不是一个长期运行的进程。Agent 是一个 durable Session 状态机：

外部输入变成 Signal；Signal 进入 Session Inbox；Activation Runner 唤醒 Session；model adapter 产出 Decision；Runtime 校验 Decision、分发动作、写入 Event、保存 Checkpoint，然后让 Session 暂停、等待或完成。

## 不可妥协的约束

- Session 是中心。
- Signal 是唯一外部触发入口。
- 同一个 Session 同一时间只有一个 writer。
- Event Log 只能追加。
- Checkpoint 支持恢复。
- Model adapter 不直接执行工具。
- Tool 不直接修改 Session。
- Child Session 不直接修改 Parent Session。
- Reducer 是 child result 进入 parent 语义的唯一归并点。
- Core 必须与 model provider 解耦。
- Core 必须无需 API key 即可运行。

## 当前范围

除非用户明确要求，否则只关注 P0：

- InMemory stores。
- FakeModel。
- Session 生命周期。
- Signal inbox。
- Activation Runner。
- Checkpoint save/load。
- Event logging。
- 确定性单元测试。

P0 不实现真实 LLM adapter、FastAPI server、Postgres store、Redis queue、云部署、GUI 或复杂多 Agent 系统。

## 开发工作流

编辑前必须说明：计划、预计修改文件、风险、验证策略。

编辑后必须说明：变更摘要、已运行检查、已修改文件、剩余风险。

每个新会话都必须从 `docs/state/project-status.md`、`docs/state/pr-queue.md` 和 `docs/DEVELOPMENT_PROCESS.md` 开始阅读。

## 安全与文档

- 不读取或修改 secrets、credentials、`.env` 或 `.env.*`。
- 不新增真实网络、真实 LLM、数据库或云服务依赖。
- 如果引入或改变公开概念，必须更新文档。
- 如果改变架构边界或公开协议，必须先写 ADR/RFC。
