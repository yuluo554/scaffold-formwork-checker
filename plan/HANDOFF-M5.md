# HANDOFF M4 → M5（交接快照，2026-10-07）

> 续接方式：新对话输入 `/goal 读取 "<项目绝对路径>\plan\HANDOFF-M5.md" 继续完成任务`
> （路径由用户侧拼绝对路径；本文件内一律相对路径）。

## 1. 当前进度

- **M4 已完成**（2026-10-07）：内置基准与报告导出全部落地并测试全绿（**255 passed** @3.8.8 venv，M3 基线 223 + 新增 32）
  - `bench/` 正式化：三套件一条命令
    - `examples_suite.py`：算例真值库 13 例逐例过引擎（与 test_engine_regression 同口径：模块识别一致 + checks 容差对账 + 中间量 0.02 容差 + 条款号非空）；指标=通过率
    - `grading_suite.py`：`GRADING_CASES` 用例表 ×35（落地 10 + 悬挑/附着/承重 9 + 模板支撑 14 + pending 2），`judge()` 全路径，pending 用例核对 unknown_params 非空；指标=通过率
    - `__init__.py`：synthetic 套件（M3 评测器原样转正）+ `run_all(data_dir)` 汇总 + `BENCH_TARGETS` 达标门限
  - `sfc bench [--data-dir] [--indent]`：输出 JSON（suites/targets/all_pass）；**exit 0=全达标 / 1=有指标未达标（完整指标仍输出） / 2=数据目录不可用**；BENCH_TARGETS：examples 通过率 100%、synthetic F1≥0.95 且误报 0、grading 通过率 100%（决策 #26①）
  - `report/`：`docx_writer.py`（规范化落盘 + 共享常量）+ `calc_report.py`（验算书：封面/参数卡表/逐项验算/中间量 4 位小数/结论汇总/签署栏手填/免责声明强制；blocked 不渲染任何计算数值仅载说明）+ `check_report.py`（核查报告：概要/参数卡+unknown_slots 显式列出/逐项核查全表/违规清单含级别+整改建议+条款+原文摘录（knowledge 回填，查不到静默跳过）/分级结论含义务+依据摘录/待人工确认项/解析告警/免责声明强制）
  - `sfc report calc <card.json> -o out.docx [--module] [--title]`、`sfc report check <docx|pdf> -o out.docx [--title]`：**exit 0=报告生成且无违规/待确认（calc 为 ok）/ 1=报告已落盘但内容含违规或待确认（calc 为 blocked）/ 2=输入不可用**（决策 #26③，产物可用性与内容健康度分离）；report 是纯渲染器（吃 result dict），引擎编排留在 CLI——M5 GUI 同样只消费引擎 API + report 生成器
  - DoD 全过：①断网可重复（子进程带不可路由代理跑 bench 全绿 + run_all 两次 JSON 一致）；②0 外链断言（全 rels 无 TargetMode="External"）；③无时间戳位级一致（zip 全条目 date_time=(1980,1,1,0,0,0)+core/app.xml 覆写，同输入两次生成字节相同）；④README 基准表 M4 正式版口径
- git 状态：M4 单次提交入 main；远程仓库仍**尚未创建**（M6 动作）

## 2. 下一里程碑 M5 待办（DoD 见 plan/05 §5 M5）

1. `gui/`：PySide6 五页签（验算/方案核查/一致性/危大分级/基准），**只消费引擎 API**（calc/check/grade/bench 同款函数调用 + report 生成器导出按钮）；页签结构见 plan/04 §8
2. PyInstaller onedir 双 exe：`sfc.exe`（CLI）+ GUI exe；数据内嵌分支（sys._MEIPASS，loader.find_data_dir 的 M5 冻结位）；spec 白名单：checks.json 入包、**data/knowledge/raw/ 绝不入包**（版权红线）
3. 演示物：exe 双通路冒烟（GUI 全流程 + CLI 控制台五连 calc/check/grade/bench/report）+ 演示 GIF/截图 + 技术报告 md（docs/）
4. DoD：①GUI offscreen 测试绿（QT_QPA_PLATFORM=offscreen）；②exe 干净验证（中立目录+剥离 PATH，不在仓库树内跑）；③数据内嵌分支测试锁死；④dist 无禁区成分扫描+内嵌数据对账断言；⑤spec 白名单守门
5. 回写：plan/00/05/06 + README（GUI/exe 用法）+ data/README（无变更则记"无"）+ HANDOFF-M6

## 3. 既定口径清单（动了会打挂测试/基准，改前先对照）

1. **CLI 退出码** 0=完成 / 1=降级完成 / 2=输入不可用或参数错误——锁进 `tests/test_cli.py`；calc：blocked→1、CardError/KnowledgeError→2；check：violation>0 或 confirmations>0 → 1；grade：definite→0（含非危大）、pending→1；**bench：all_pass→0、未达标→1、数据目录不可用→2**（test_cli_bench）；**report：calc 同 calc 口径、check 同 check 口径（报告已落盘但含违规/待确认→1）**（test_cli_report）；argparse 未知子命令/缺必选参 SystemExit(2)
2. **包名/命令/版本**：包 `scaffold_formwork_checker`、命令 `sfc`、`__version__` 与 pyproject 一致（test_version_matches_pyproject 守门）
3. **Python 底线 3.8**：运行时语法不用 3.9+ 特性（全程 %-格式化惯例）；本机 3.8.8 venv 实测
4. **EOL**：`* text=auto eol=lf`；全树文本 CR 门测试常驻（tests/test_eol_gate.py）——新文件一律 LF
5. **版权红线**：规范全文只存 `data/knowledge/raw/`（gitignored）；表值矩阵在 engine/tables.py；checks.json 规则表在包内（决策 #25）——M5 打包 spec 白名单两处都须覆盖，raw/ 绝不入包
6. **条文纪律**：待核对数值不得进入计算/判定路径——引擎双层拦截+规则运行器同口径+grading basis 全已核对；**report 延伸：blocked 验算书不渲染任何计算数值**（test_report_calc.py 锁定）
7. **零 LLM 通路**：解析=正则/关键词/表格行匹配、核查=规则表、分级=三值条件求值器（不 eval）；基准零 API（断网守门测试 test_bench_offline_with_broken_proxies）
8. **限值不写死**：checks.json 一律 limit_ref 挂 thresholds.json；步距双限值 1.8/2.0 在 thresholds ×36
9. **真值对账口径（决策 #17/#20/#23）**：synthetic 按"全部非 pass 集合"对账，matcher 四重；fixtures seed=20261006 冻结
10. **两张皮定级（决策 #22）**：超容差即 violation（两方向），方向只定 level
11. **分级判定序（决策 #25）**：chaoguimo→weida→none 首个 True；三值 None=参数缺失 pending
12. **门控语义（决策 #24）**：only_if 关键词 AND 全命中 project_type；扣件架族关键词="扣件"
13. **解析置信度**：0.99/0.85/0.5 分层，CONFIDENCE_MIN=0.7
14. **bench 达标门限（决策 #26①）**：BENCH_TARGETS=examples 100%/synthetic F1≥0.95 且 FP=0/grading 100%——grading 用例表 35 例锁规模（test_bench_suites 断言 ==35），改 panorama 阈值或加用例须同步
15. **报告确定性（决策 #26②）**：内容零时间戳（签署栏手填）、零外链、落盘 zip 规范化（report/docx_writer.py 自持 normalize，**与 synth 生成器同做法不共享代码，刻意解耦**）；免责声明强制节；同输入位级一致（test_report_calc/check 双锁）
16. **测试基线**：M4 收尾 **255 passed**（3.8 venv）；后续收尾全量测试须 ≥ 此数且全绿，收集数差异逐项归因
17. **GUI 只消费引擎 API**（M5）：report/ 是纯渲染器（吃 result dict 不做引擎编排），GUI 导出按钮按 CLI 同款编排后调 generate_calc_report/generate_check_report
18. **dev extras 覆盖测试期依赖**：pytest + python-docx + pypdf；CI `.[dev]` 全覆盖；M5 加 PySide6 时 extras 下限写法见 pyproject 注释（3.8 上限 6.6.3.x）

## 4. 本机环境坑（只记实测）

- `py -0p`：本机**只有** 3.8.8-64（一律 `py -3.8` 或 venv 内 python.exe）
- pip 姿势：`PYTHONDONTWRITEBYTECODE=1 NO_PROXY="*" no_proxy="*" ./.venv/Scripts/python.exe -m pip install ... -i https://pypi.tuna.tsinghua.edu.cn/simple`
- Git Bash `/tmp` 与 Windows Python 路径**不通**：跨工具传文件一律先进仓库 `output/`（gitignored）再处理
- **sfc.exe 冒烟注意**：`sfc calc data/examples/EX-*.json` 直接喂算例文件会报"无法识别 category"——须先抽 `input_card`；`sfc check/grade` 直接喂 data/synthetic/SY-*.docx；`sfc report calc` 同 calc（先抽卡）
- **pytest readouterr() 只能消费一次**（二次调用 err 为空，M4 踩过）——需同时断言 out/err 时一次接住 `captured = capsys.readouterr()`
- pytest 无 `__init__.py` 布局下 tests 内可 `from report_helpers import ...`（tests/report_helpers.py 共用断言）
- load_knowledge 传**data 目录**（含 knowledge/clauses），不是仓库根；grading.load_panorama/bench 各套件同
- 全程 `PYTHONDONTWRITEBYTECODE=1`（含 pip install）；venv 可执行文件用 `./.venv/Scripts/<name>.exe`
- 解析管线改动后必跑 `tools/gen_synthetic.py --check`（位级一致）+ `tests/test_m3_synthetic_eval.py`；**改动 report/docx_writer.py 后必跑位级一致测试**（test_report_calc/check）
- PySide6 未装（M5 装，注意 3.8 上限 6.6.3.x）；PyInstaller 未装（M5 `.[build]`）

## 5. 关键命令速查

```bash
# 环境（首次或重建）
PYTHONDONTWRITEBYTECODE=1 py -3.8 -m venv .venv
PYTHONDONTWRITEBYTECODE=1 NO_PROXY="*" no_proxy="*" ./.venv/Scripts/python.exe -m pip install -U pip -i https://pypi.tuna.tsinghua.edu.cn/simple
PYTHONDONTWRITEBYTECODE=1 NO_PROXY="*" no_proxy="*" ./.venv/Scripts/python.exe -m pip install -e ".[dev]" -i https://pypi.tuna.tsinghua.edu.cn/simple

# 测试与 CLI 冒烟（M5 收尾必跑）
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -m pytest tests -q
./.venv/Scripts/sfc.exe --version && ./.venv/Scripts/sfc.exe selfcheck

# M4 通路冒烟
./.venv/Scripts/sfc.exe bench                                    # exit 0（全达标）
./.venv/Scripts/sfc.exe report calc output/card.json -o output/r.docx   # card.json=算例 input_card 抽取
./.venv/Scripts/sfc.exe report check data/synthetic/SY-two-sheets-01.docx -o output/ts.docx  # exit 1（含违规）

# M3 通路冒烟（直接喂合成 fixtures）
./.venv/Scripts/sfc.exe check data/synthetic/SY-clean-01.docx              # exit 0
./.venv/Scripts/sfc.exe grade data/synthetic/SY-grading-missing-01.docx    # 超规模+义务+依据

# sfc calc 冒烟（先抽卡）
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -X utf8 -c "import json; json.dump(json.load(open('data/examples/EX-lizhigan-nw-001.json',encoding='utf-8'))['input_card'], open('output/card.json','w',encoding='utf-8'), ensure_ascii=False)"
./.venv/Scripts/sfc.exe calc output/card.json

# 基准指标（sfc bench 的库层入口）
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -X utf8 -c "from scaffold_formwork_checker.bench import run_all; import json; print(json.dumps(run_all()['suites'], ensure_ascii=False, indent=1))"

# 数据工具（改体例/重生成后必须 --check 位级一致）
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -X utf8 tools/gen_examples.py --check
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -X utf8 tools/gen_synthetic.py --check

# git 链前三核对（防 cwd 劫持）
pwd && git log --oneline -1 && git remote -v
```

## 6. M4 DoD 复核（逐项，详证见 plan/05 M4 节）

- [x] ①基准零 API 可重复：断网代理环境子进程跑 `sfc bench` 全绿 + run_all 两次运行 JSON 一致（tests/test_cli_bench.py、test_bench_suites.py）
- [x] ②报告 0 外链断言：calc/check 两报告全 rels 无 TargetMode="External"（tests/report_helpers.py::assert_no_external_links）
- [x] ③产物无时间戳位级一致：zip 全条目 (1980,1,1,0,0,0)+core/app.xml 固定；同输入两次生成字节相同（tests/test_report_calc.py、test_report_check.py）
- [x] ④指标写入 README：评测基准节 M4 正式版（三套件表格+门限+sfc bench 说明）
- [x] 附加：bench 三套件全绿（examples 13/13、synthetic F1=1.0/FP=0、grading 35/35）；sfc bench/report 退出码语义全锁（15 项 CLI 测试）；255 passed 全绿（M3 基线 223 不回退）；gen_synthetic/gen_examples --check 位级一致
