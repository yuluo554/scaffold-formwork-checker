# HANDOFF M3 → M4（交接快照，2026-10-07）

> 续接方式：新对话输入 `/goal 读取 "<项目绝对路径>\plan\HANDOFF-M4.md" 继续完成任务`
> （路径由用户侧拼绝对路径；本文件内一律相对路径）。

## 1. 当前进度

- **M3 已完成**（2026-10-07）：方案核查与分级全部落地并测试全绿（**223 passed** @3.8.8 venv）
  - `parse/`：docx/pdf → 参数卡（python-docx + pypdf，文本路线零识图零 LLM）。`SchemeCard` 条目制 schema（entries[name]={value,unit,confidence,evidence} + unknown_slots）；置信度分层：参数表逐行 0.99 / 正文正则与关键词在位 0.85 / 多值冲突强制 0.5 → CONFIDENCE_MIN=0.7 以下进 unknown_slots；**搭设高度章节限定提取**（工程概况/危大工程管理节，避开构造措施模板句"24m及以上（若适用）"污染）；参数表缺失时表格槽位显式收尾进 unknown_slots；验算书卡独立解析（"验算取值：步距X m，立杆纵距Y m，立杆横距Z m"句式）——两张皮在解析层就分卡
  - `rules/`：`checks.json` 规则表 ×12（入包 src/…/rules/checks.json，随代码走）+ 运行器。四类 check_type：threshold（限值经 limit_ref 挂 thresholds.json 不写死；表6.4.2 分支选择+参数化限值 "3h"/"3la" 现算）/ presence / consistency（委托 consistency 包）/ grading（分级联动：超规模须专家论证=严重、危大须专项方案=不合格）。**only_if 门控=关键词 AND 全命中 project_type，跨全部 check_type 一致生效**；待核对双层拦截与引擎同口径（规则 status!=已核对 或 limit_ref 阈值条目待核对 → 跳过记 confirmation）；三级判定 提示/不合格/严重
  - `consistency/`：两卡字段对齐，容差=字段定义（长度类 0.01m）；**超容差即 verdict=violation（两方向都是，真值口径决策 #22）**，方向只定 level：方案实况劣于验算书=不合格（实况未被验算覆盖）、验算书偏保守=提示；任一侧缺字段→待人工确认
  - `grading/`：panorama.json ×9 条目消费；自研三值条件求值器（True/False/None=参数缺失，OR/AND 短路，不 eval）；类型识别关键词序（工具式模板→承重支撑→模板支撑→附着→悬挑→吊篮→卸料→异型→落地兜底）；**判定序 chaoguimo→weida→none**（超规模条件成立时危大条件必然成立，决策 #25）；basis 全部已核对才出确定结论；rule_id 映射 G-pan-luodi-50（真值锁定）/G-pan-luodi-24/默认 G-<item_id>
  - `bench/`（dev 版）：`run_synthetic_suite()` 非 pass 集合对账评测器（rule_id+verdict+数值字段容差 1e-6+条款号包含四重对账），M4 `sfc bench` 直接复用
  - CLI：`sfc check <docx|pdf>`（0=无违规无待确认 / 1=有违规或待确认 / 2=输入不可用）、`sfc grade <docx|pdf> [--param name=value]`（0=判定完成 / 1=pending / 2=输入不可用）；`--data-dir` 显式不回退沿 M2 口径
- 数据变更：thresholds.json ×34→**×36**（T-JGJ130-step-max 1.8 挂 6.1.1 / T-JGJ130-step-max-loose 2.0 挂 A.0.1，均已核对）；**SY-walltie-over-02.truth.json limit_value 修正** 5.4→4.5（生成器 `_truth` 硬编码 3×1.8 改随池步距，docx 字节不变，决策 #23）
- git 状态：M3 单次提交入 main；远程仓库仍**尚未创建**（M6 动作）

## 2. 下一里程碑 M4 待办（DoD 见 plan/05 §5 M4）

1. `bench/` 正式化：三套件（examples 算例回归 / synthetic 合成基准 / grading 分级基准）+ `sfc bench` 一条命令跑完，指标写 README 表（synthetic 与 grading 评测逻辑已在 bench/ 与 tests 就位，组装即可）
2. `report/`：验算书 docx + 核查报告 docx（python-docx 生成；封面/参数卡表/逐项验算/违规清单/分级结论/待人工确认项/**免责声明强制**）
3. DoD：①基准零 API 可重复（断网跑通）；②报告 0 外链断言测试（docx 内无 `TargetMode="External"` 超链关系）；③产物无时间戳位级一致测试（zip 元数据豁免表——参照 synth/generator.py `_normalize_zip` 的覆写做法）；④指标写入 README
4. 回写：plan/00/05/06 + README 基准表 + data/README + HANDOFF-M5

## 3. 既定口径清单（动了会打挂测试/基准，改前先对照）

1. **CLI 退出码** 0=完成 / 1=降级完成 / 2=输入不可用或参数错误——锁进 `tests/test_cli.py`；calc：blocked→1、CardError/KnowledgeError→2（test_cli_calc）；**check：violation>0 或 confirmations>0 → 1**（test_cli_check）；**grade：definite→0（含非危大）、pending→1**；argparse 未知子命令自行 SystemExit(2)
2. **包名/命令/版本**：包 `scaffold_formwork_checker`、命令 `sfc`、`__version__` 与 pyproject 一致（test_version_matches_pyproject 守门）
3. **Python 底线 3.8**：运行时语法不用 3.9+ 特性（M3 全程 %-格式化）；本机 3.8.8 venv 实测
4. **EOL**：`* text=auto eol=lf`；全树文本 CR 门测试常驻（tests/test_eol_gate.py）——新文件（含 checks.json）一律 LF
5. **版权红线**：规范全文只存 `data/knowledge/raw/`（gitignored）；表值矩阵在 engine/tables.py（M1 既定）；**checks.json 规则表在包内**（决策 #25），M5 打包 spec 须入白名单
6. **条文纪律**：待核对数值不得进入计算/判定路径——引擎双层拦截 + **规则运行器同口径双层拦截**（规则 status + limit_ref 阈值条目 status，tests/test_rules_checks.py 两测试锁定）；grading basis 全部已核对才出确定结论
7. **零 LLM 通路**：解析=正则/关键词/表格行匹配、核查=规则表、分级=三值条件求值器（不 eval）；基准零 API
8. **限值不写死**：checks.json 规则一律 limit_ref 挂 thresholds.json（表6.4.2 分支限值 "3h"/"3la" 由运行器从阈值表取串现算，表值即事实源）；步距双限值 1.8（6.1.1 常用档）/2.0（A.0.1 全域档）已在 thresholds ×36
9. **真值对账口径（决策 #17/#20/#23）**：合成基准按"全部非 pass 集合"对账（真值=main_expect+also_expect），matcher 四重：rule_id + verdict + 数值字段（容差 1e-6）+ truth clause_ref ∈ finding clause_refs；fixtures seed=20261006 冻结，改生成器→重生成整目录提交
10. **两张皮定级（决策 #22）**：超容差即 violation（两方向），方向只定 level（实况劣于验算书=不合格/验算书偏保守=提示）——two-sheets 两例真值均 violation 锁死
11. **分级判定序（决策 #25）**：chaoguimo→weida→none 首个 True（模板支撑类目超规模⊃危大）；三值逻辑 None=参数缺失（OR 短路可出确定结论，否则 pending）
12. **门控语义（决策 #24）**：only_if 关键词 AND 全命中 scheme.project_type（方案标题行）；扣件架族关键词="扣件"（兼容"落地式扣件钢管脚手架"简写、排除碗扣式）；落地步距规则另加"落地式"
13. **解析置信度**：参数表 0.99/正文 0.85/多值冲突 0.5，CONFIDENCE_MIN=0.7；搭设高度只在工程概况/危大工程管理节提取（模板句防污染）；参数表缺失时表格槽位显式进 unknown_slots
14. **测试基线**：M3 收尾 **223 passed**（3.8 venv）；后续收尾全量测试须 ≥ 此数且全绿，收集数差异逐项归因
15. **GUI 只消费引擎 API**（M5）；报告产物无时间戳（M4）；模块自动识别分派序（M2 决策 #15）不变
16. **dev extras 覆盖测试期依赖**：pytest + python-docx + **pypdf**（M3 加入，决策 #25 后续）；CI `.[dev]` 全覆盖

## 4. 本机环境坑（只记实测）

- `py -0p`：本机**只有** 3.8.8-64（一律 `py -3.8` 或 venv 内 python.exe）
- pip 姿势：`PYTHONDONTWRITEBYTECODE=1 NO_PROXY="*" no_proxy="*" ./.venv/Scripts/python.exe -m pip install ... -i https://pypi.tuna.tsinghua.edu.cn/simple`
- Git Bash `/tmp` 与 Windows Python 路径**不通**：跨工具传文件一律先进仓库 `output/`（gitignored）再处理
- **pypdf 5.9.0 已装入 venv**（M3 PDF 文本路线）；品茗规范库表格/公式是 JPG 原图：正文文本可 grep，表值必须读图转录（PIL 裁剪放大辅助）
- **sfc.exe 冒烟注意**：`sfc calc data/examples/EX-*.json` 直接喂算例文件会报"无法识别 category"——须先抽 `input_card`（M4 bench 才做整文件消费）；`sfc check/grade` 直接喂 data/synthetic/SY-*.docx 即可
- pytest 参数化 readouterr() 只能消费一次（二次调用 err 为空）；load_knowledge 传**data 目录**（含 knowledge/clauses），不是仓库根；grading.load_panorama 同
- 全程 `PYTHONDONTWRITEBYTECODE=1`（含 pip install）；venv 可执行文件用 `./.venv/Scripts/<name>.exe`
- 解析管线改动后必跑 `tools/gen_synthetic.py --check`（fixtures 位级一致守门）+ `tests/test_m3_synthetic_eval.py`（基准指标）

## 5. 关键命令速查

```bash
# 环境（首次或重建）
PYTHONDONTWRITEBYTECODE=1 py -3.8 -m venv .venv
PYTHONDONTWRITEBYTECODE=1 NO_PROXY="*" no_proxy="*" ./.venv/Scripts/python.exe -m pip install -U pip -i https://pypi.tuna.tsinghua.edu.cn/simple
PYTHONDONTWRITEBYTECODE=1 NO_PROXY="*" no_proxy="*" ./.venv/Scripts/python.exe -m pip install -e ".[dev]" -i https://pypi.tuna.tsinghua.edu.cn/simple

# 测试与 CLI 冒烟（M4 收尾必跑）
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -m pytest tests -q
./.venv/Scripts/sfc.exe --version && ./.venv/Scripts/sfc.exe selfcheck

# M3 通路冒烟（直接喂合成 fixtures）
./.venv/Scripts/sfc.exe check data/synthetic/SY-clean-01.docx              # exit 0
./.venv/Scripts/sfc.exe check data/synthetic/SY-two-sheets-01.docx         # exit 1（两张皮）
./.venv/Scripts/sfc.exe grade data/synthetic/SY-grading-missing-01.docx    # 超规模+义务+依据

# sfc calc 冒烟（先抽卡）
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -X utf8 -c "import json; json.dump(json.load(open('data/examples/EX-lizhigan-nw-001.json',encoding='utf-8'))['input_card'], open('output/card.json','w',encoding='utf-8'), ensure_ascii=False)"
./.venv/Scripts/sfc.exe calc output/card.json

# 合成基准指标（M4 组装进 sfc bench）
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -X utf8 -c "from scaffold_formwork_checker.bench import run_synthetic_suite; print(run_synthetic_suite()['metrics'])"

# 数据工具（改体例/重生成后必须 --check 位级一致）
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -X utf8 tools/gen_examples.py --check
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -X utf8 tools/gen_synthetic.py --check

# git 链前三核对（防 cwd 劫持）
pwd && git log --oneline -1 && git remote -v
```

## 6. M3 DoD 复核（逐项，详证见 plan/05 M3 节）

- [x] ①合成基准 dev 版达标：检出率 100%（14/14）、误报 0（干净对照 0）、F1=1.0、5 类注入逐类 100%（tests/test_m3_synthetic_eval.py）
- [x] ②分级边界值用例 100%：落地 23.9/24.0/24.1、49.9/50.0/50.1 + 悬挑 20m/附着 150m/承重 7kN/模板支撑 5 条件全边界 + 三值 pending（tests/test_grading.py）
- [x] ③门控跨类目隔离测试：悬挑≠落地步距规则、模板支撑≠扣件架规则、碗扣式≠扣件族，正反两向（tests/test_rules_checks.py）
- [x] ④低置信度"待人工确认"降级测试：多值冲突→unknown_slots→核查记 confirmation 不硬判、分级 pending→exit 1（tests/test_parse_degrade.py + test_cli_check.py）
- [x] 附加：CLI check/grade 12 测试（exit 0/1/2 全语义）；待核对双层拦截（规则级+阈值级）；223 passed 全绿（M2 基线 115 不回退）；gen_synthetic/gen_examples --check 位级一致；CLI calc/check/grade 三通路冒烟全通
