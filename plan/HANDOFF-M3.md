# HANDOFF M2 → M3（交接快照，2026-10-07）

> 续接方式：新对话输入 `/goal 读取 "<项目绝对路径>\plan\HANDOFF-M3.md" 继续完成任务`
> （路径由用户侧拼绝对路径；本文件内一律相对路径）。

## 1. 当前进度

- **M2 已完成**（2026-10-07）：公式引擎全部落地并测试全绿（**115 passed** @3.8.8 venv）
  - 查表模块 `engine/tables.py`：从 raw/ 原文表图**双读转录**入仓——表A.0.6 φ 全 251 档（λ>250 用 φ=7320/λ²）、表A.0.1 gk 全矩阵（单/双排，域内线性插入按表注）、表5.2.8 μ（精确匹配无插值）、表A.0.5 挡风系数；`verify_anchors()` 与 thresholds.json 登记锚点逐一对账
  - 验算模块 `engine/m_*.py`：M-1 立杆稳定（不组合风）/ M-2（组合风）/ M-3 纵横向水平杆 / M-4 连墙件 / M-5 立杆地基 / M-6 模板支架立柱稳定+地基（JGJ162）；契约 `calc(card, kn) -> CalcResult`（checks 含 expr/substituted/ratio/limit/verdict/clause_refs，detail 与算例 intermediate 键名对齐）
  - 加载器 `engine/loader.py`：模块依赖面（MODULE_DEPS）+ **双层待核对硬拦截**（模块级 unverified → blocked；取值级 threshold() 再拦）；显式 --data-dir/SFC_DATA 不合法立即报错不回退（决策 #21）
  - 参数卡 `engine/card.py`：构造时合法性校验（正数/枚举/必填/类型），非法即 CardError；JGJ162 步距>1.8m 可算但带规范限值 warning（构造整改归 M3 核查）
  - CLI：`sfc calc <card.json> [--module M-x] [--data-dir] [--indent]`，模块自动识别（category→foundation/member/tie_length/wind 逐层分派）；退出码 0=完成 / 1=blocked 降级 / 2=输入不可用
  - 标量纪律：f=205/215、Rc=8.0、N0、分项系数 1.2/1.4、γ0=0.9、截面特性全部**运行时从 thresholds.json 取用**（status 拦截覆盖）；代码内仅 k=1.155、E=206000、M-6 步距上限 1.8 三处结构量（tests 对账台账）
- git 状态：M2 单次提交入 main；远程仓库仍**尚未创建**（M6 动作）

## 2. 下一里程碑 M3 待办（DoD 见 plan/05 §5 M3）

1. `parse/`：docx/pdf → 参数卡（python-docx + pypdf，文本路线零识图；低置信度槽位进 unknown_slots）
2. `rules/`：构造限值核查规则表（rules/checks.json）+ 三级判定（提示/不合格/严重）+ **类目门控跨 check_type 生效**（threshold/presence/consistency/grading 全部走 only_if 门控）
3. `consistency/`：两张皮一致性（方案卡×验算书卡字段对齐，容差=字段定义，安全方向定级）
4. `grading/`：危大分级判定器（消费 `data/knowledge/clauses/panorama.json` ×9 条目；判定=工程类型识别→参数提取→逐级条件比较→结论+义务+依据摘录）
5. `sfc check` / `sfc grade` 子命令（退出码口径沿用 0/1/2）
6. 合成基准 dev 版：12 冻结 fixtures（5 类注入×2+干净对照×2）跑"解析+核查"，按"全部非 pass 集合"对账（真值=主期望+also_expect）
7. 分级边界值用例（如 23.9/24.0/24.1、49.9/50.0/50.1）100%；门控跨类目隔离测试；低置信度"待人工确认"降级测试
8. 回写：plan/00/05/06 + README 基准表 + HANDOFF-M4

## 3. 既定口径清单（动了会打挂测试/基准，改前先对照）

1. **CLI 退出码** 0=完成 / 1=降级完成 / 2=输入不可用或参数错误——锁进 `tests/test_cli.py`；argparse 未知子命令自行 SystemExit(2)；`sfc calc` 对 blocked 返回 1、CardError/KnowledgeError 返回 2（tests/test_cli_calc.py）
2. **包名/命令/版本**：包 `scaffold_formwork_checker`、命令 `sfc`、`__version__` 与 pyproject 一致（test_version_matches_pyproject 守门）
3. **Python 底线 3.8**：运行时语法不用 3.9+ 特性（engine 全程 %-格式化、无海象/无 match）；本机 3.8.8 venv 实测
4. **EOL**：`* text=auto eol=lf`；全树文本 CR 门测试常驻（tests/test_eol_gate.py）
5. **版权红线**：规范全文只存 `data/knowledge/raw/`（gitignored）；入仓=要点+条款号+短摘录+出处+status；**表值矩阵（φ/gk/μ/挡风系数）属参数取值事实数据，已入 engine/tables.py**（M1 thresholds meta 既定）
6. **条文纪律**：status=待核对 的数值不得进入计算路径——引擎双层拦截（tests/test_engine_gate.py 8 组参数化锁死）；新加模块依赖必须同步 loader.MODULE_DEPS **与** tests/test_clause_library.py::test_engine_module_dependencies_all_verified 两处
7. **零 LLM 通路**：基准零 API；数值结论永远来自确定性规则
8. **λ 查表口径（决策 #18）**：λ=ceil(l0/i) 向上取整查表A.0.6 离散档、禁插值；λ>250 用 φ=7320/λ²（λ 取实际值非档位）；φ 锚点 {85:0.692, 95:0.626, 191:0.197, 197:0.186, 236:0.131} 由 test_engine_tables + test_examples_truth 双锁；JGJ130 f=205 / JGJ162 f=215 不得混用
9. **μ/gk 查表口径**：表5.2.8 离散档精确匹配（无插值注，双排 lb∈{1.05,1.30,1.55}）；表A.0.1 域内线性插入（有表注），域外拒收；gk 可由卡显式给值（优先）或查表（tests/test_engine_regression.py::test_gk_table_lookup_equivalence 锁两路等价）
10. **算例负担模型（真值）**：脚手板每层负担面积=la×lb/2、栏杆道数=脚手板层数、安全网 0.01×la×H；横向水平杆简支 l0=lb、负担宽度=la；纵向水平杆三跨连续梁（M=0.175P·la、支座-0.150P·la、内支座反力 1.15P）——改动=改真值，须重跑 tools/gen_examples.py 并整目录提交
11. **算例真值库 schema（决策 #20）**：input_card 含路由字段 rows/member/地基轴力显式值；13 例 regress 锚定 item 名（lizhigan_stability/bending_strength/deflection/antislip/tie_strength/tie_stability/foundation_bearing/column_stability）与 detail 键名
12. **合成 fixtures 冻结**：data/synthetic/ 禁手改；seed=20261006；真值语义=主期望+also_expect，按"全部非 pass 集合"对账（M3 评测直接消费）
13. **测试基线**：M2 收尾 **115 passed**（3.8 venv）；后续收尾全量测试须 ≥ 此数且全绿，收集数差异逐项归因
14. **GUI 只消费引擎 API**（M5）；报告产物无时间戳（M4）
15. **模块自动识别分派序**：formwork_support→M-6；coupler 卡 foundation→M-5 > member→M-3 > tie_length/tie_type→M-4 > wind 不组合→M-1 否则 M-2（engine/detect_module，13 例回归锁死）

## 4. 本机环境坑（只记实测）

- `py -0p`：本机**只有** 3.8.8-64（一律 `py -3.8` 或 venv 内 python.exe）
- pip 姿势：`PYTHONDONTWRITEBYTECODE=1 NO_PROXY="*" no_proxy="*" ./.venv/Scripts/python.exe -m pip install ... -i https://pypi.tuna.tsinghua.edu.cn/simple`
- Git Bash `/tmp` 与 Windows Python 路径**不通**：跨工具传文件一律先进仓库 `output/`（gitignored）再处理
- **pillow 已装入 venv**（M2 表图转录辅助，不在任何 extras 里）；品茗规范库表格/公式是 JPG 原图：正文文本可 grep，表值必须读图转录；小字号表头/行值用 PIL 裁剪放大后再读
- **sfc.exe 冒烟注意**：`sfc calc data/examples/EX-*.json` 直接喂算例文件会报"无法识别 category"——算例 JSON 是完整真值记录（卡片在 `input_card` 键下），须先抽出卡片（CLI 测试即如此）；M4 bench 才做整文件消费
- pytest 参数化 readouterr() 只能消费一次（二次调用 err 为空）；load_knowledge 传**data 目录**（含 knowledge/clauses），不是仓库根
- 全程 `PYTHONDONTWRITEBYTECODE=1`（含 pip install）；venv 可执行文件用 `./.venv/Scripts/<name>.exe`

## 5. 关键命令速查

```bash
# 环境（首次或重建）
PYTHONDONTWRITEBYTECODE=1 py -3.8 -m venv .venv
PYTHONDONTWRITEBYTECODE=1 NO_PROXY="*" no_proxy="*" ./.venv/Scripts/python.exe -m pip install -U pip -i https://pypi.tuna.tsinghua.edu.cn/simple
PYTHONDONTWRITEBYTECODE=1 NO_PROXY="*" no_proxy="*" ./.venv/Scripts/python.exe -m pip install -e ".[dev]" -i https://pypi.tuna.tsinghua.edu.cn/simple

# 测试与 CLI 冒烟（M3 收尾必跑）
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -m pytest tests -q
./.venv/Scripts/sfc.exe --version && ./.venv/Scripts/sfc.exe selfcheck
# sfc calc 冒烟（先抽卡）
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -X utf8 -c "import json; json.dump(json.load(open('data/examples/EX-lizhigan-nw-001.json',encoding='utf-8'))['input_card'], open('output/card.json','w',encoding='utf-8'), ensure_ascii=False)"
./.venv/Scripts/sfc.exe calc output/card.json

# 数据工具（改体例/重生成后必须 --check 位级一致）
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -X utf8 tools/gen_examples.py --check
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -X utf8 tools/gen_synthetic.py --check

# git 链前三核对（防 cwd 劫持）
pwd && git log --oneline -1 && git remote -v
```

## 6. M2 DoD 复核（逐项，详证见 plan/05 M2 节）

- [x] ①算例真值通过率 100%：13/13（checks 容差内 + 中间量逐项对账 + 模块自动识别一致，tests/test_engine_regression.py）
- [x] ②参数扫描回归锁定：H/活载/步距/横距/层数/风压/板厚单调性 + M-4 抗滑越界 + M-5 面积反比 + λ=250 边界连续（tests/test_engine_card_sweep.py）
- [x] ③待核对拦截测试：8 组参数化（公式×阈值 × 各模块），blocked 零数值 + 第二层取值拦截（tests/test_engine_gate.py）
- [x] ④参数非法拒收测试：M-1 20 组变异 + M-5/M-6 专项（tests/test_engine_card_sweep.py）
- [x] 附加：CLI calc 10 测试（exit 0/1/2 全语义+13 例逐张过 CLI）；表值与台账对账 12 测试；115 passed 全绿（基线 32 不回退）；gen_examples/gen_synthetic --check 位级一致
