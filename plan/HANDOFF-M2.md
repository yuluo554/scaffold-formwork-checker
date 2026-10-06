# HANDOFF M1 → M2（交接快照，2026-10-07）

> 续接方式：新对话输入 `/goal 读取 "<项目绝对路径>\plan\HANDOFF-M2.md" 继续完成任务`
> （路径由用户侧拼绝对路径；本文件内一律相对路径）。

## 1. 当前进度

- **M1 已完成**（2026-10-07）：数据先行全部落地并守门测试全绿
  - 原文获取：37号令（mohurd 官方直连）、31号文（官方正文+waizi 全文+深圳gov 附件2 双渠道）、JGJ130-2011/JGJ162-2008（品茗规范库全文 HTML+表格/公式原图 99/132 张，关键表逐张视觉转录）；全文只存 `data/knowledge/raw/`（gitignored），sha256 台账登记
  - 条款库 `data/knowledge/clauses/`：74 条款块（130×44/162×15/37号令×7/31号文×8）+ formulas.json×22 + thresholds.json×34 + panorama.json（危大清单×9 条目，附件1/2 逐条挂原文摘录）；**5 验算模块所需条目全部 status=已核对**（唯一待核对=F-J162-sidepressure，首期模块不依赖）
  - 算例真值库 `data/examples/`：**13 例**覆盖 M-1~M-6+2 条不合格路径，`tools/gen_examples.py` 逐中间量复算断言；教材算例四渠道受限实录后降级（规范条文算例为主力，决策 #15）
  - 合成生成器 `src/scaffold_formwork_checker/synth/`（SplitMix64 确定性 RNG，禁 stdlib random/set 序/时钟）+ `data/synthetic/` 12 冻结 fixtures（5 类注入×2 + 干净对照×2，docx 无时间戳，manifest 带 sha256）
  - 守门测试：`tests/test_synth_freeze.py`（RNG 序列锁/两次构建位级一致/仓库 fixtures 位级复现/无时间戳/真值语义）+ `tests/test_eol_gate.py`（全树文本 CR 门）+ `tests/test_examples_truth.py` + `tests/test_clause_library.py`
- git 状态：M1 单次提交入 main；远程仓库仍**尚未创建**（M6 动作）

## 2. 下一里程碑 M2 待办（DoD 见 plan/05 §5 M2）

1. `engine/` 5+1 验算模块：M-1 立杆稳定（不组合风）/ M-2（组合风）/ M-3 纵横向水平杆 / M-4 连墙件 / M-5 立杆地基 / M-6 模板支架立杆稳定（JGJ162）；契约 `calc(card, tables) -> CalcResult`（plan/04 §3）
2. 条款库加载器：**待核对硬拦截**（任一依赖条目 status=待核对 → 模块返回"不可验算（依据未核对）"，测试锁死）
3. 查表模块：表A.0.6 φ 全 251 档、表A.0.1 gk 全矩阵、表5.2.8 μ——从 raw/ 原文表图转录入引擎（口径见决策 #18：λ=ceil(l0/i) 向上取整查档、禁插值、λ>250 用 φ=7320/λ²）
4. `sfc calc` 子命令：参数卡 JSON → 验算结果（应力比/结论/条款号），退出码 0/1/2 语义沿用
5. 参数非法拒收测试（合法性范围校验在卡片构造时执行）
6. 算例真值回归：`bench examples` 形态的比对（M4 才做正式 sfc bench，M2 先做 pytest 级回归：13 例全过、容差内）+ 参数扫描回归（关键参数扫描锁定单调性与边界）
7. 回写：plan/00/05/06 + README 基准表初版 + HANDOFF-M3

## 3. 既定口径清单（动了会打挂测试/基准，改前先对照）

1. **CLI 退出码** 0=完成 / 1=降级完成 / 2=输入不可用或参数错误——锁进 `tests/test_cli.py`；argparse 未知子命令自行 SystemExit(2)
2. **包名/命令/版本**：包 `scaffold_formwork_checker`、命令 `sfc`、`__version__` 与 pyproject 一致（test_version_matches_pyproject 守门）
3. **Python 底线 3.8**：运行时语法不用 3.9+ 特性（类型注解新语法必须字符串化）；本机 3.8.8 venv 实测
4. **EOL**：`* text=auto eol=lf`；全树文本 CR 门测试常驻（tests/test_eol_gate.py）
5. **版权红线**：规范全文只存 `data/knowledge/raw/`（gitignored）；入仓=要点+条款号+短摘录+出处+status
6. **条文纪律**：status=待核对 的数值不得进入计算路径（M2 加载器硬校验，tests/test_clause_library.py::test_engine_module_dependencies_all_verified 已锁公式/阈值面）
7. **零 LLM 通路**：基准零 API；数值结论永远来自确定性规则
8. **extras 完整性**：dev extras 已含 pytest+python-docx（synth 测试 import docx）；M2 测试期新 import 的可选依赖必须进 extras 且 CI `.[dev]` 覆盖
9. **测试基线**：M1 收尾 **32 passed**（3.8 venv）；后续收尾全量测试须 ≥ 此数且全绿，收集数差异逐项归因
10. **算例复算口径（决策 #18）**：λ=ceil(l0/i) 向上取整查表A.0.6 离散档，禁线性插值；φ 锚点 {85:0.692, 95:0.626, 191:0.197, 197:0.186, 236:0.131} 由 tests/test_examples_truth.py 锁定；JGJ130 f=205 / JGJ162 f=215 不得混用
11. **算例负担模型**：脚手板每层负担面积=la×lb/2（内外立杆各半）、栏杆道数=脚手板层数、安全网 0.01×la×H；横向水平杆简支 l0=lb（图5.2.4）、负担宽度=la；纵向水平杆三跨连续梁跨中集中力（M=0.175P·la、支座-0.150P·la、内支座反力 1.15P）——改动=改真值，须重跑 tools/gen_examples.py 并整目录提交
12. **合成 fixtures 冻结**：data/synthetic/ 禁手改；改体例→`tools/gen_synthetic.py` 重生成整目录提交+台账 sha256 同步；真值语义=主期望+also_expect，评测按"全部非 pass 集合"对账；seed=20261006
13. **GUI 只消费引擎 API**（M5）；报告产物无时间戳（M4）

## 4. 本机环境坑（只记实测）

- `py -0p`：本机**只有** 3.8.8-64（一律 `py -3.8` 或 venv 内 python.exe）
- pip 姿势：`PYTHONDONTWRITEBYTECODE=1 NO_PROXY="*" no_proxy="*" ./.venv/Scripts/python.exe -m pip install ... -i https://pypi.tuna.tsinghua.edu.cn/simple`
- Git Bash `/tmp` 与 Windows Python 路径**不通**：跨工具传文件一律先复制进仓库 `output/`（gitignored）再处理
- **搜索引擎批量限流实录（M1）**：360 so.com 连续查询即 302；百度移动间歇 HTTP 000；Bing 经 WebFetch 中文查询被词典结果污染；WebSearch 只给域名级链接。可靠通道=官方站点直连（mohurd/gov.cn 地方站）+ 品茗规范库（pmgd.cn，站点结构 `/?m=home&c=View&a=index&aid=N`）+ waizi.org.cn（/doc/N.html）；bzko/建标库反爬或不可达
- mohurd 附件下载是 JS 动态加载（页面 grep 不到直链）；官方 2018 年原始 URL 已 404，现行内容在 gzk（规章库）/wjk（文件库）新路径
- **品茗规范库表格/公式是 JPG 原图**：正文文本可 grep，表值必须读图转录；题注与图片在 HTML 中错位，按"题注 ASCII 片段→其后首个 img"定位
- 全程 `PYTHONDONTWRITEBYTECODE=1`（含 pip install）；venv 可执行文件用 `./.venv/Scripts/<name>.exe`

## 5. 关键命令速查

```bash
# 环境（首次或重建）
PYTHONDONTWRITEBYTECODE=1 py -3.8 -m venv .venv
PYTHONDONTWRITEBYTECODE=1 NO_PROXY="*" no_proxy="*" ./.venv/Scripts/python.exe -m pip install -U pip -i https://pypi.tuna.tsinghua.edu.cn/simple
PYTHONDONTWRITEBYTECODE=1 NO_PROXY="*" no_proxy="*" ./.venv/Scripts/python.exe -m pip install -e ".[dev]" -i https://pypi.tuna.tsinghua.edu.cn/simple

# 测试与 CLI 冒烟（M2 收尾必跑）
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -m pytest tests -q
./.venv/Scripts/sfc.exe --version && ./.venv/Scripts/sfc.exe selfcheck

# 数据工具（改体例/重生成后必须 --check 位级一致）
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -X utf8 tools/gen_examples.py --check
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -X utf8 tools/gen_synthetic.py --check

# git 链前三核对（防 cwd 劫持）
pwd && git log --oneline -1 && git remote -v
```

## 6. M1 DoD 复核（逐项，详证见 plan/05 M1 节）

- [x] ①条款条目 100% 挂出处或"待核对"（74 条款+22 公式+34 阈值全部有 status+source；panorama basis 全部已核对）
- [x] ②生成器两次运行位级一致（test_two_builds_bit_identical + test_repo_fixtures_regenerate_bit_identical）
- [x] ③fixtures CR 守门测试入仓（test_eol_gate.py 全树 CR 门 + 冻结目录非空校验）
- [x] ④EOL/冻结纪律测试全绿（**32 passed** @3.8.8 venv，M0 基线 8 项不回退）
- [x] 附加：CLI 三通路复验；raw/ gitignore 生效（git status 零泄漏）；教材算例偏差已留档（决策 #15）
