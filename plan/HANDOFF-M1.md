# HANDOFF M0 → M1（交接快照，2026-10-06）

> **⚠️ 已过时仅作历史**：M1 已于 2026-10-07 完成（DoD 复核见本文件末尾追加节），续接请读 [HANDOFF-M2.md](HANDOFF-M2.md)。本文件保留 M0→M1 的交接口径与 M0 DoD 记录。

> 续接方式：新对话输入 `/goal 读取 "<项目绝对路径>\plan\HANDOFF-M<n>.md" 继续完成任务`
> （路径由用户侧拼绝对路径；本文件内一律相对路径）。

## 1. 当前进度

- **M0 已完成**：plan/ 计划文档 00-06 定稿（需求解读/架构选型/模块详设/数据与里程碑/决策记录 13 条）；可运行骨架落地并冒烟通过：
  - 仓库根=包根：`pyproject.toml`（src 布局，extras dev/parse/report/gui/build）+ `src/scaffold_formwork_checker/`（`__init__`/`cli.py`/`__main__.py`）+ `tests/`（8 项）+ `.github/workflows/ci.yml`（四矩阵）+ `.gitattributes`（eol=lf）+ MIT LICENSE + README 骨架
  - 数据目录骨架：`data/knowledge/clauses|examples|synthetic/`（.gitkeep），`data/knowledge/raw/` 已 gitignore（版权红线）
  - 冒烟实测（Python 3.8.8 venv）：`pip install -e ".[dev]"` 成功；**pytest 8 passed**；CLI 三通路正常（`--version`→0、`selfcheck`→0、未知命令→2、`python -m` 等价）
- git 状态：M0 骨架以单次提交入 main（HANDOFF 随同提交）；远程仓库**尚未创建**（M6 动作）。

## 2. 下一里程碑 M1 待办（DoD 见 plan/05 §5）

1. 规范原文获取与核对：JGJ 130-2011、JGJ 162-2008、37号令、31号文 → 逐字原文 curl/WebFetch 落盘 `data/knowledge/raw/`（本地），sha256 登记台账
2. 条款库 JSON（`data/knowledge/clauses/`）：条款块+公式表+阈值表，5 验算模块所需条目全部有 status；待核对条目显式标注
3. 危大阈值清单（31号文附件1/附件2 相关条目）逐条挂原文摘录
4. 算例真值库（`data/examples/`）≥10 例（教材/规范算例，登记书名/版次/例题号）
5. 合成专项方案生成器 v1（`data/synthetic/`）：自研确定性 RNG（splitmix64，禁 stdlib random/set 序/时钟）、≥3 类注入+干净对照、真值语义（主期望+also_expect）、落盘无时间戳
6. 字节冻结守门：生成器两次运行位级一致测试 + 冻结 fixtures CR 守门测试（EOL 门）
7. 数据台账回填（data/README.md 登记表）+ 回写 plan/00、05、06 + 本 HANDOFF 头部标注"已过时仅作历史"后写 HANDOFF-M2

## 3. 既定口径清单（动了会打挂测试/基准，改前先对照）

1. **CLI 退出码** 0=完成 / 1=降级完成 / 2=输入不可用或参数错误——锁进 `tests/test_cli.py::test_exit_code_semantics_are_locked`；argparse 未知子命令自行 SystemExit(2) 与口径一致
2. **包名/命令/版本**：包 `scaffold_formwork_checker`、命令 `sfc`、`__version__` 与 pyproject 必须一致（`test_version_matches_pyproject` 守门，改版本两处同步）
3. **Python 底线 3.8**：运行时语法不用 3.9+ 特性（本机只有 3.8.8-64；3.12 靠 CI 覆盖）；类型注解若用新语法必须字符串化
4. **EOL**：`.gitattributes` `* text=auto eol=lf` + 二进制类型显式声明；M1 fixtures 落地后补 CR 守门测试
5. **版权红线**：规范原文全文只存 `data/knowledge/raw/`（gitignored）；入仓条款库=要点+条款号+出处+status
6. **条文纪律**：status=待核对 的数值不得进入计算路径（M2 引擎加载器硬校验）
7. **零 LLM 通路**（plan/06 #8）：基准零 API；未来任何 LLM 兜底只能做"宁缺"槽位且不得覆盖确定性结论
8. **extras 完整性**：测试期 import 到的可选依赖必须进 extras 且 CI 显式安装（防"悄悄少跑"）
9. **测试基线**：M0 本机 3.8 venv = 8 passed；后续里程碑收尾全量测试须 ≥ 此数且全绿，dev 与 CI/干净环境收集数差异必须逐项归因
10. **GUI 只消费引擎 API**（M5）；报告产物无时间戳（M4）

## 4. 本机环境坑（只记实测）

- `py -0p`：本机**只有** 3.8.8-64（无 3.12；商店占位符 python 不可用，一律 `py -3.8` 或 `py`）
- `py -3.8 -m venv .venv` 一次成功；venv 内 pip 升 25.0.1
- pip 安装可用形式：`NO_PROXY="*" no_proxy="*" <python> -m pip install ... -i https://pypi.tuna.tsinghua.edu.cn/simple`（本次未触发代理报错，该形式作为默认姿势保留）
- 全程 `PYTHONDONTWRITEBYTECODE=1`（含 pip install）
- Git Bash 下调用 venv 可执行文件用 `./.venv/Scripts/<name>.exe` 相对形式可用

## 5. 关键命令速查

```bash
# 环境（首次或重建）
PYTHONDONTWRITEBYTECODE=1 py -3.8 -m venv .venv
PYTHONDONTWRITEBYTECODE=1 NO_PROXY="*" no_proxy="*" ./.venv/Scripts/python.exe -m pip install -U pip -i https://pypi.tuna.tsinghua.edu.cn/simple
PYTHONDONTWRITEBYTECODE=1 NO_PROXY="*" no_proxy="*" ./.venv/Scripts/python.exe -m pip install -e ".[dev]" -i https://pypi.tuna.tsinghua.edu.cn/simple

# 测试与 CLI 冒烟（M1 收尾必跑）
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -m pytest tests -v
./.venv/Scripts/sfc.exe --version && ./.venv/Scripts/sfc.exe selfcheck

# git 链前三核对（防 cwd 劫持）
pwd && git log --oneline -1 && git remote -v
```

## 6. M0 DoD 复核（逐项）

- [x] plan/00-06 齐全，00 索引与状态表回写
- [x] 骨架可运行：3.8 venv 安装成功，pytest 8 passed，CLI 三通路+退出码语义验证
- [x] CI 四矩阵 + eol=lf + extras 分层入仓（CI 实跑在 M6 push 后首验）
- [x] 决策记录 13 条（含缓议 2 条：真实赛事窗口 M6 清零、GIF 工具 M5 定）
- [x] data/ 目录骨架与台账规则就位，raw/ 版权红线 gitignore 生效
- [x] 本 HANDOFF 落盘（相对路径用法行）

---

## 7. M1 完成追加节（2026-10-07）

M1 待办 7 项全部完成：

1. ✅ 规范原文获取：37号令（mohurd 官方规章库直连，现行修正版）、31号文（mohurd 官方文件库正文 + waizi 全文含附件1/2 + 深圳gov附件2 双渠道）、JGJ130-2011/JGJ162-2008（品茗规范库全文 HTML + 99/132 张表格公式原图）；全部落盘 `data/knowledge/raw/`（gitignored），sha256 登记台账
2. ✅ 条款库 JSON：74 条款（JGJ130×44 / JGJ162×15 / 37号令×7 / 31号文×8）+ 公式表 22 + 阈值表 34；5 验算模块所需条目全部 status=已核对（唯一待核对=F-J162-sidepressure，首期模块不依赖）
3. ✅ 危大阈值清单 `data/knowledge/clauses/panorama.json`：9 条目逐条挂原文摘录，落地式 24m/50m 边界语义钉死
4. ✅ 算例真值库 13 例（≥10）：覆盖 M-1~M-6 全模块+2 条不合格路径；教材算例四渠道受限实录后按纪律降级（规范条文算例为主力，复算脚本 tools/gen_examples.py 断言）
5. ✅ 合成方案生成器 v1：src/scaffold_formwork_checker/synth/（SplitMix64 + 5 类注入 + 干净对照）+ 12 冻结 fixtures（无时间戳 docx）
6. ✅ 字节冻结守门：tests/test_synth_freeze.py（RNG 序列锁/两次构建位级一致/仓库 fixtures 位级复现/无时间戳/真值语义）+ tests/test_eol_gate.py（全树文本 CR 门）
7. ✅ 台账回填 + plan/00/05/06 回写 + 本文件标注过时 + HANDOFF-M2 落盘

测试基线：M0 8 passed → M1 收尾 **32 passed**（Python 3.8.8 venv），CLI 三通路复验通过。
