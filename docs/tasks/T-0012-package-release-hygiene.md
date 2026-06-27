# T-0012: package/release hygiene

> 状态: 已完成
> PR: PR-0010
> 最近更新: 2026-06-27

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

- ACT-0002：Owner 已确认使用 Apache-2.0。

## 验证

- `make check`。
- 本地 import smoke test。
- example smoke test。

## 完成记录

- Owner 已确认 license 使用 Apache-2.0。
- 新增根目录 `LICENSE`。
- 新增最小 `pyproject.toml`，声明 package metadata、Python 3.12 下限和 Apache-2.0 license。
- 新增 import smoke test，覆盖 `sessgraph` public package import。
- README 新增本地 editable install、测试、example 和 license 说明。
- `.gitignore` 新增本地 venv、build、dist 和 egg-info 产物。
- 未发布到 PyPI，未新增 CI，未引入 runtime 依赖，未修改 runtime 语义。
