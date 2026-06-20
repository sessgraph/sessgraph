# T-0012: package/release hygiene

> 状态: 延后
> PR: PR-0010
> 最近更新: 2026-06-20

## 目标

补齐最小 Python package hygiene，让外部开发者可以本地安装、导入、运行测试和 example，同时不进行真实发布。

## 范围

范围内：

- 最小 Python package 元数据。
- 本地 editable install 或等价开发安装说明。
- import smoke test。
- README 中的安装、测试和 example 命令。
- 如 Owner 已确认 license，则新增对应 license 文件。

范围外：

- 不发布到 PyPI。
- 不新增 CI。
- 不新增真实 provider、database、queue、server 或 cloud。
- 不引入非必要外部依赖。
- 不修改 runtime 语义。

## 依赖

- ACT-0002：Owner 已明确延后 license 决策；本任务随 license 决策延后。

## 验证

- `make check`。
- 本地 import smoke test。
- example smoke test。
