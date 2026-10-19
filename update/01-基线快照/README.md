# 改前基线快照（v1.0.0，2026-10-19）

> 采集方式：仓库自带 `.venv`（Python 3.8.8），输出经 `tr -d '\r'` 转 LF 后落盘
> （仓库 `tests/test_eol_gate.py` 对全树文本做 CR 门，快照也受约束）。

## 1. 源码态（仓库自带 3.8.8 venv）

| 项 | 命令 | 结果 |
|---|---|---|
| 测试 | `.venv/Scripts/python -m pytest tests -q` | **314 passed in 44.90s**，EXIT=0（原始输出 `pytest-before.txt`） |
| 自检 | `.venv/Scripts/sfc selfcheck` | EXIT=0（`selfcheck-before.txt`：extras parse/report/gui 全可用） |
| 基准 | `.venv/Scripts/sfc bench` | EXIT=0，`"all_pass": true`（`bench-before.json`） |
| 版本 | `.venv/Scripts/sfc --version` | `sfc 1.0.0`（`version-before.txt`） |

## 2. v1.0.0 发布附件

| 项 | 值 |
|---|---|
| 文件 | `sfc-v1.0.0-windows-x64-onedir.zip` |
| 字节数 | **52,146,144** |
| sha256 | **`28eaa48dacd8d9140cf4c6683d883c72d576f725c4834fb0d81b6c080132fbf2`** |
| 取得方式 | `gh release download v1.0.0 -p 'sfc-v1.0.0-windows-x64-onedir.zip' -D update/01-基线快照`，随后 `sha256sum` |

> 附件本体在核对 sha256 后已从工作树删除（52MB 二进制不入仓，Release 上仍可随时下载）。
