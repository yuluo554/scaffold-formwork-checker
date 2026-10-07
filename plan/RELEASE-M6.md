# RELEASE-M6 发布门留档（2026-10-07）

> 依据：plan/05 §M6 DoD（发布门逐项留档）+ HANDOFF-M6 §2。本文档随 M6 推进逐项补记，命令与结论均为实跑实录。

## 1. 干净环境验证（DoD ①）

- 基线：dev venv 全量 `pytest tests -q` → **304 passed**（7.93s，2026-10-07 复跑确认）。
- 验证目录：中立目录 `%LOCALAPPDATA%\Temp\sfc-clean-m6`（仓库树外），`git clone` 本仓 → `py -m venv .venv` → 全新 venv（pip 20.2.3 起，README 前置行 `pip install -U pip` 升至 25.0.1 生效）→ 按 README 逐字执行。
- **[dev] 通路**（`pip install -e ".[dev]"`，全部依赖自公共 registry 解析，无本机缓存依赖）：
  - `sfc --version` → `sfc 0.5.0`，exit 0；
  - `sfc selfcheck` → exit 0，数据目录=clone 内 `data/`，extras gui 显示"未安装"（符合预期）；
  - `pytest tests -q -rs` → exit 0，**283 passed, 1 skipped**；
    - skip 归因：`SKIPPED [1] tests\test_gui.py:22: could not import 'PySide6'`——**test_gui.py 模块级 `pytest.importorskip("PySide6")`（docx 同理），21 个 GUI 用例在收集期被折叠为 1 条模块级 skip 条目**，非逐条展开（与 HANDOFF-M6 预测的"-rs 逐项可见"表现有出入，实测如实记录：折叠 1 条，代表的用例集=test_gui.py 全部 21 项）；
    - 收集数对账：dev 环境单独收集 `pytest tests/test_gui.py --collect-only -q` → **21 tests collected**；283 + 21 = 304 ✅（无"悄悄少跑"：差集全部归因到 test_gui.py 单文件）。
- **[dev,gui] 通路**（`pip install -e ".[gui]"` → PySide6 装入）：`pytest tests -q` → exit 0，**304 passed**（7.98s）。
- CLI 五连 + GUI 探针（干净 venv，退出码逐一单跑核实，不经管道）：

| 命令 | 退出码 | 说明 |
|---|---|---|
| `sfc calc <参数卡>.json` | 0 | 参数卡=从 `data/examples/EX-diji-001.json` 的 `input_card` 字段提取（仓库无裸参数卡文件，见下方发现②） |
| `sfc check data/synthetic/SY-two-sheets-01.docx` | 1 | 含违规（预期降级完成） |
| `sfc check data/synthetic/SY-clean-01.docx` | 0 | 干净对照无违规无待确认 |
| `sfc grade data/synthetic/SY-two-sheets-01.docx` | 0 | 判定完成 |
| `sfc bench --indent 0` | 0 | 三套件全达标 |
| `sfc report calc <参数卡>.json -o …` | 0 | docx 生成 |
| `sfc report check …SY-two-sheets-01.docx -o …` | 1 | 含违规降级（预期） |
| `QT_QPA_PLATFORM=offscreen sfc-gui --probe` | 0 | GUI 无头探针通过 |

- **验证过程实录（暴露问题与处置）**：
  1. EOL 守门抓现行：验证期误将 bench 输出重定向进 clone 内（`bench_clean.json`），Windows 控制台重定向产生 CRLF → `tests/test_eol_gate.py` 立即 FAIL（`assert not ['bench_clean.json']`）。**守门测试有效性的活证据**；草稿产物一律放仓库树外后复跑全绿。产品无缺陷，不加测试（守门本就在位）。
  2. README 发现①：`sfc calc` 直接喂 `data/examples/*.json` 退出码 2（真值库记录含 `example_id/expect` 包装，非裸参数卡）——dev 环境同命令同退出码，**非回归**，属 README 可跑通性小缺口：README 只说"参数卡形态见各例 input_card 字段"，但仓内无一份可直接喂给 calc 的裸参数卡。处置：README calc 段补一行澄清（用户从 `input_card` 字段提取），随 M6 发布准备提交入仓；不新增数据文件（避免动打包白名单 46 份对账）。
  3. MSYS 路径传参坑（工具性，非产品）：`cygpath -u` 形式路径传给 Windows 原生 Python `open()` 会 FileNotFoundError，须 `cygpath -w` 转换——复验者留意。

## 2. 系列表述公开性核实（DoD ② 前置）

- 命令：`gh api "users/yuluo554/repos?per_page=100"`（2026-10-07 实跑）→ 返回列表即匿名访客可见的公开仓库全集。
- 结论：系列前作**全部已公开**——bidding-document-checker、construction-drawing-plan-checker、food-label-compliance-checker、invoice-ledger-checker、medical-record-quality-checker、power-operation-ticket-checker、resume-talent-pool、siteguard、structural-strengthening-checker、weida-plan-review、UHPC-Mixture-Design 及 dsh 插件族，`private` 字段均为 false。
- 处置：**保留系列表述**（plan/00 "与前作同模式"、plan/01 "与 structural-strengthening-checker 同模式"、plan/06 "系列第十题"等均不掩码）；结论记入 plan/06 决策 #32。
- 审计器配合：姊妹词表以 base64 内置于 tools/desensitize_audit.py（词表明文不入仓），命中判 REVIEW 复核项而非硬门（依据本节公开性证据豁免）；若未来出现未公开的新前作，把词表条目保留、将其命中升级硬门即可。

## 3. 脱敏四步 + 产物本体扫描（DoD ②，固化入仓）

- **固化物**：`tools/desensitize_audit.py`（四步+产物扫描+selftest，任一硬命中 exit 1，全过打印 DESSENSITIZE_AUDIT_OK）+ `tools/binary_whitelist.json`（17 份 tracked 二进制 sha256：12 synthetic docx + 5 GUI 截图 png）+ 守门测试 `tests/test_desensitize_audit.py`（6 项）与 `tests/test_ci_workflow.py`（4 项，含 workflow YAML 可解析/fetch-depth:0/dev extras 覆盖断言）。词表与个人目录名在源码中一律片段拼接/base64（扫描器自扫描 0 自命中）。
- **第 1 步 tracked**：文件名扫描（\.env$|\.key$|secret|token|password|_private）0 命中；.gitignore 覆盖断言（.env/*.key/_private/build/dist/output）全过；内容级扫描 149 份 tracked 文本 0 硬命中（个人路径/内网 IP/手机号/身份证/密钥形态全 0；邮箱仅 `git@github.com` 服务地址形态，豁免域白名单覆盖）。
- **第 2 步 内容级**：并入第 1 步逐行扫描（输出形态 "文件:行号 [类别] x次数"，不回显原文）。
- **第 3 步 二进制样例**：docx 走 zipfile 全条目扫描（含 docProps/core.xml 的 creator/lastModifiedBy 元数据重灾区）0 命中；png 走字节强标记+tEXt/iTXt 文本块扫描 0 命中；sha256 白名单对账 17/17 一致；synthetic docx 与 data/synthetic/manifest.json 登记值联动对账 12/12 一致。
- **第 4 步 历史三扫**：①`git log --all -p --format=commit %H` 全文（含提交信息+全部 diff）硬模式 0 命中；②`git rev-list --all --objects` 对象路径 0 敏感形态；③逐提交树面 fixed-string 前向覆盖（姊妹词+个人目录形态）仅姊妹词 REVIEW 命中（公开性豁免，见 §2）。**旧邮箱字面值级历史验证属仓外人工步骤**（字面值不入仓铁律），执行记录见 §4。
- **产物本体扫描（第 5 步）**：`--mode dist` 全 dist 树字节级强标记（个人目录形态+姊妹词）+ 禁区段（raw）路径扫描 → **0 命中**（M5 打包红线"raw 绝不入包"在产物侧复核成立）。
- **selftest 阳性/阴性对照**：SELFTEST_OK——阳性（拼接构造的邮箱/11 位手机号/18 位证件/个人目录路径/sk 密钥/docx core.xml 元数据邮箱/字节级目录标记）全被捕获；阴性（github.com/example.com 豁免域、12 位长数字串、25 位长数字串、URL scheme、hex 串内数字段、无标记字节）全不误报。首轮 selftest 实抓夹具 bug（分隔符插进 "Users" 中间致路径阳性未命中），修正后复跑过——阳性对照有效性实证。**hex 误报校准实录**：binary_whitelist.json 入仓后，其 sha256 十六进制串内的 11 位数字段（…f81a1+8825915680+c07…）被 phone 模式命中（该文件提交前进不了 git 扫描面，提交后随 diff 进入历史扫描才暴露）→ phone/idcard 模式加 hex 边界环视（`(?<![0-9a-fA-F])…(?![0-9a-fA-F])`），selftest 补 hex 阴性对照——真实号码在文本中必以非 hex 字符定界，无漏报代价。
- **REVIEW 豁免留档**：plan/01 姊妹词 ×1 + 历史 log-p 姊妹词 ×5 + 历史树面姊妹词 ×7 个提交——全部属已公开前作（§2），豁免常驻。
- **守门测试常驻**：test_desensitize_audit.py 6 项随全量测试运行（dist 项在无产物环境声明式跳过）；审计脚本所在提交先于推送（审查作用域=被推送提交，见 M5 事故纪律）。

## 4. 提交元数据邮箱检查（DoD ③）

- 预检：`git log --format="%ae %ce" --all | sort -u` → 仅一个身份（个人 QQ 邮箱，**字面值按留档纪律不入仓**，以占位符指代：`<旧QQ邮箱>`）；HEAD 树 `git grep` 0 命中。
- **瑕疵实录（留痕不回填）**：本文件 §4 初稿把该邮箱字面值写进了预检记录——违反"留档文档用占位符指代敏感字面值"纪律，被改写后终验的字面值 grep 抓出（1 处，恰在本文件）；正应了方法论文档对该坑的预告。处置：本节占位符化 + tip 提交 amend + reflog expire + gc prune，终验复跑 0 命中。
- 改写执行（2026-10-07）：改写前 `git bundle create <仓外>/sfc-pre-rewrite.bundle --all` 备份；`git filter-branch --env-filter`（作者/提交者姓名与邮箱统一改写为 GitHub noreply `<id>+yuluo554@users.noreply.github.com`，id=282769740 取自 `gh api user --jq .id`）作用于 `-- --all` 全历史 8 提交，输出重定向文件不接管道（badRef 坑预防）；改写后 `rm -rf .git/refs/original && git reflog expire --expire=now --all && git gc --prune=now --aggressive`；本地 `git config user.email` 同步改 noreply。
- 终验（全 0 才过）：①`git log --format="%ae %ce" refs/heads/main | sort -u` → 仅 noreply 一个身份 ✅；②固定字面值 grep：`git log refs/heads/main -p | grep -c <旧QQ邮箱>`（仓外字面值人工执行）→ **0** ✅；③`git fsck --full` 0 错误 ✅；④审计器 history 模式复跑 DESSENSITIZE_AUDIT_OK ✅。
- 波及说明：改写后全部提交哈希变化（原 af9a17e→重写后哈希见 `git log`）；历史内容（blob）零变化，仅元数据与 RELEASE-M6 §4 本句树面变化。

## 5. 建仓与推送（DoD ④）

（待补）

## 6. CI 首跑（DoD ⑤）

（待补）

## 7. Release/tag（DoD ⑥，经用户确认）

（待补）

## 8. 收尾固化（DoD ⑦）

（待补）
