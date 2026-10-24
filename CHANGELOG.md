# Changelog

本文件记录对外可见的版本变更；格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [SemVer](https://semver.org/lang/zh-CN/)。

## [2.0.1] — 2026-10-24

**修正 v2.0.0 发布物的内嵌数据未同步（不影响任何数值结论与判定逻辑）。**

### Fixed（发布物）

- **v2.0.0 的 exe 附件里，7 个条款库 JSON 全部是 v1.0.0 的旧副本**：
  `data/knowledge/clauses/*.json` 逐字节等于 tag `v1.0.0` 的对应文件，
  因此 v2.0.0 宣称新增的 `meta.review`（复核元数据）**在下载到的 exe 里完全不存在**。
  逐文件字节数（旧 → 应发布）：`decree37` 6,648→7,411、`formulas` 14,935→16,350、
  `jgj130` 35,049→36,015、`jgj162` 13,846→14,601、`notice31` 8,536→9,564、
  `panorama` 12,624→13,830、`thresholds` 19,122→20,243。
- **根因**：v2.0.0 迭代的时序是「先重建 exe（18:34）→ 后改条款库（`e6ba924`，19:13）」，
  提交时两者一起入库，但 `dist/` 未再重建；此后对 `dist/sfc` 的 `tools/build_exe.py --check`
  沿用旧结果，发布前的「冒烟四连」只读版本/自检/基准/GUI 探针，**没有一项读 `meta.review`**，
  于是旧数据一路绿灯发出。
- **本版修正**：全量重建 onedir（`BUILD_CHECKS_OK`）并对新附件**逐字节**核对 45 个内嵌 data
  条目与 `HEAD` 一致（0 条不符）。
- **给 v2.0.0 下载者**：请在条款库层面改用本版附件。v2.0.0 的 exe **算出的数值结论是正确的**
  （条款数值、阈值、算例真值三者未变），差异只在复核元数据的缺失。

### Changed

- 版本号 `2.0.0` → `2.0.1`（`pyproject.toml` + `__init__.py`）。
- README 自述测试数与附件名同步实测值（`319 tests` → `329 tests`，附件名 → `v2.0.1`）。
- PEP 639 许可证元数据迁移（`license = "MIT"` + `license-files = ["LICENSE"]`，
  `setuptools>=77`）；**`requires-python` 未变**，pip 安装条件不变。

## [2.0.0] — 2026-10-19

**破坏性变更：不再支持 Python 3.8 / 3.9，最低要求 Python 3.10。**

### Changed（破坏性）

- `requires-python` 由 `>=3.8` 提升到 **`>=3.10`**；`classifiers` 改为 3.10 / 3.11 / 3.12；
  CI 矩阵由 `ubuntu/windows × 3.8/3.12` 改为 **`ubuntu/windows × 3.10/3.12`**。
  用旧解释器（3.8/3.9）通过 pip 安装 v2.0.0 将不再可行——Windows 用户可直接用免安装 exe。
- 依赖线重评（原上限是被 Python 3.8 逼出来的，不是设计选择）：
  - `gui`：`PySide6>=6.6,<6.7` → **`PySide6>=6.6,<7`**（实测 6.12.0）
  - `build`：`pyinstaller>=5.13,<6` → **`pyinstaller>=6,<7`**（实测 6.22.3 重建 exe 通过）
  - `dev`/`parse`/`report` 下限：`pytest>=7`→`>=8`、`python-docx>=0.8.11`→`>=1.1`、`pypdf>=3`→`>=5`
    （实测解析到 pytest 9.1.1 / python-docx 1.2.0 / pypdf 6.21.1）
- 交付物重建：`sfc-v2.0.0-windows-x64-onedir.zip` 由 **Python 3.12.10 + PyInstaller 6.22.3** 打包
  （v1.0.0 的 exe 是 Python 3.8.8 打的，该解释器已停止安全支持）。

### Added

- **条款库复核机制**：7 个条款库 JSON 的 `meta.review` 登记「来源发布日 / 本次复核日 /
  下次复核日 / 复核周期 / 权威出处 URL / 现行性结论」；新守门测试 `tests/test_clause_review.py`
  （复核元数据非空、URL 必填、panorama 条目级 `status` 与 `basis` 级一致、待核对公式必须
  显式声明 `not_used_by` 且与真实依赖面一致、所有 `fetched` 取回日期非空）。
- README「判定依据」表（依据名 + 版本 + 生效日 + 本次复核日结论）与 `DEVELOPMENT.md`
  （里程碑/架构/基准/打包流程索引）。
- `panorama.json` 9 个条目补条目级 `status`（此前只有 `basis[]` 级，机器扫不到）。
- `formulas.json` 的 `F-J162-sidepressure` 补 `not_used_by`（本版本 6 个模块均不引用）与
  `pending_reason`（已完成项 = 公式本体按原文公式图目读一致；未完成项 = 参数表取值来源登记）。

### Notes（依据现行性复核，2026-10-19 权威渠道直连）

- **JGJ 130-2011**：仍现行；但其 16 条强制性条文自 **2022-10-01** 起由 **GB 55023-2022**
  《施工脚手架通用规范》（强制性）废止。本工具计算所用条文不在废止清单内；库中
  `6.2.3 / 6.4.4 / 6.6.3` 三条的强制性条文地位已被取代，其构造要求现由 GB 55023-2022
  4.4.6 / 4.4.7 承接（本工具未把这三条用于数值计算路径）。
- **JGJ 162-2008**：仍现行（未检索到替代/废止公告；GB 55008-2021 与 GB 55023-2022 的废止
  强制性条文清单中均无本规范）。
- **住建部令第 37 号**：现行（2019 年部令第 47 号修正版）。
- **建办质〔2018〕31 号**：现行；建办质〔2021〕48 号（专项施工方案编制指南）、
  建办质〔2024〕63 号（方案严重缺陷清单·试行）为配套补充，非替代。

### Known issues

- GB 55023-2022 表 4.2.4-2（混凝土结构模板支撑脚手架施工荷载 ≥2.5 kN/m²）与 JGJ 162-2008
  4.1.2（计算支架立柱取 1.0 kN/m²）口径不一致，GB 55023-2022 为强制性规范。本版本未改数值
  （会牵动冻结算例/fixture/基准真值），列为独立决策项。
- `F-J162-sidepressure` 仍为 `待核对`（本版本不依赖，见上）。

## [1.0.0] — 2026-10-07

首个正式发布（M6 收官）。

### Added

- 数据先行：JGJ 130-2011 / JGJ 162-2008 / 住建部令第 37 号 / 建办质〔2018〕31 号条款库
  （74 条款 + 22 公式 + 36 阈值 + 9 危大条目，逐条挂出处与核对状态）、13 例算例真值库、
  12 份合成专项方案冻结 fixtures（确定性生成器 + 位级一致守门）。
- 公式引擎：6 个验算模块（立杆稳定两工况、水平杆抗弯挠度、连墙件、立杆地基、模板支架立柱
  与地基），参数卡校验 + `status=待核对` 双层硬拦截。
- 方案核查与危大分级：docx/PDF 文本解析为参数卡、12 条核查规则（构造限值/在位/两张皮/分级
  联动）、三级危大判定（附义务与依据摘录）。
- 内置基准 `sfc bench`（零 API、离线、确定性）与 docx 报告导出 `sfc report`（无时间戳、零外链）。
- 桌面 GUI（PySide6 五页签）与 PyInstaller onedir 双 exe（数据内嵌、构建后禁区扫描 + sha256 对账）。
- CLI 退出码契约（0/1/2）自 M0 起锁定。

### Notes

- 发布资产：`sfc-v1.0.0-windows-x64-onedir.zip`（52,146,144 字节，
  sha256 `28eaa48dacd8d9140cf4c6683d883c72d576f725c4834fb0d81b6c080132fbf2`），
  由 Python 3.8.8 打包（该解释器于 2024-10 停止安全支持，v2.0.0 已修正）。

## [0.1.0] — 2026-10-06

M0 骨架：pyproject/src 布局、CLI 入口（`sfc`，退出码 0/1/2 契约）、测试与 CI 四矩阵、
`.gitattributes`（LF 纪律）、LICENSE、README、`plan/` 计划文档（00-06）。

[2.0.0]: https://github.com/yuluo554/scaffold-formwork-checker/releases/tag/v2.0.0
[1.0.0]: https://github.com/yuluo554/scaffold-formwork-checker/releases/tag/v1.0.0
[0.1.0]: https://github.com/yuluo554/scaffold-formwork-checker/commits/main