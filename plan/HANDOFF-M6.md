# HANDOFF M5 → M6（交接快照，2026-10-07）

> 续接方式：新对话输入 `/goal 读取 "<项目绝对路径>\plan\HANDOFF-M6.md" 继续完成任务`
> （路径由用户侧拼绝对路径；本文件内一律相对路径）。

## 1. 当前进度

- **M5 已完成**（2026-10-07）：桌面交付全落地（**304 passed** @3.8.8 venv，M4 基线 255 + 新增 49；版本 0.5.0）
  - `gui/` 五页签（验算/方案核查/一致性/危大分级/基准）：分层=**pipelines.py（GUI 唯一编排层，零 Qt，与 CLI 同款引擎 API）+ specs.py（动态表单规格+默认卡）+ 页签表现层**；零模态框（notify 信号）；`sfc gui` 子命令 + `sfc-gui` 入口（惰性导入，缺依赖提示 exit 2）；21 项 offscreen 测试（PySide6 缺席环境整模块声明式跳过）
  - `packaging.py` + `tools/sfc.spec` + `tools/build_exe.py`：onedir 单 spec 双 exe（sfc console / sfc-gui windowed）；datas 单一事实源白名单 46 份（checks.json + knowledge/clauses + examples + synthetic；**raw/ 绝不入包**）；hiddenimports 显式 docx/pypdf；构建后 `--check`：dist 禁区扫描 + 内嵌 sha256 对账 + 白名单外多余检测（exit 1 阻断）；spec 文本守门测试
  - `engine/loader.find_data_dir` 冻结分支：显式 > SFC_DATA > sys._MEIPASS/data > exe/_internal/data > exe/data > CWD 上溯（**冻结分支整体先于 CWD 上溯**）；10 项分支测试锁死
  - 演示物：五页签截图 docs/images/*.png（native QPA + widget.grab + QBuffer，相对路径）+ docs/技术报告.md + exe 双通路冒烟（CLI 五连 + GUI --probe）
  - exe 干净验证（DoD ②，中立目录 %LOCALAPPDATA%\Temp\sfc-clean-m5 + `env -i SYSTEMROOT=...` 剥离 PATH）：selfcheck（数据目录=内嵌副本）/calc 0/check 1（含违规降级）/grade 0/**bench 0（三套件内嵌数据全达标）**/report calc 0/report check 1（降级）/GUI 探针 0——验证完已删中立目录，复验照 HANDOFF-M5 §5 重做
  - 依赖版本通道实测：PySide6 6.6.3.1（extras `>=6.6,<6.7`）+ PyInstaller 5.13.2（extras `>=5.13,<6`）
- git 状态：M5 单次提交入 main；远程仓库**仍未创建**（M6 动作）；dist/（118MB）不入仓

## 2. 下一里程碑 M6 待办（DoD 见 plan/05 §5 M6，发布门逐项留档 plan/RELEASE-M6.md）

1. 干净环境验证：新目录 clone + 全新 venv 按 README 逐字跑通（GUI 通路须 `.[dev,gui]`）；dev 与干净环境 pytest **收集数**对账（304 = dev 全装；干净 clone 不装 gui → 283 收集 + 21 GUI 模块级 skip，`-rs` 逐项可见，逐项归因留档）
2. 脱敏四步 + 产物本体扫描（固化成入仓脚本+守门测试）：tracked/内容级/二进制样例/历史三扫全 0；**系列表述公开性先核实**（`gh api users/<owner>/repos` 查前作可见性，未公开 → 掩码后再过扫描）；HANDOFF 用法行已是相对路径（M0 纪律生效，无需重写历史）
3. 提交元数据邮箱检查（`git log --format="%ae %ce" --all | sort -u`）→ 必要时 env-filter 改写 GitHub noreply
4. 建仓：token 无 workflow scope 时 `gh repo create <u>/<r> --public --source . --remote origin`（**不带 --push**）→ 切 SSH push（先 `ssh -T git@github.com` 验证）
5. CI 首跑四矩阵绿（ubuntu/windows × 3.8/3.12；CI 只装 `.[dev]`——GUI 测试声明式 skip 属预期，收集数对账见上）；`gh run list` 对账 push 数=run 数
6. Release/tag 经用户确认后打在 CI 绿的终态提交上：Release notes=评测表数值+演示命令+截图；exe 附件=dist/sfc 打 zip（sha256 留档）；缓议项清零（决策 #12 赛事确认）；README 状态行转正
7. 收尾固化：技术报告 docx 化（md 先定稿再程序化生成）如需赛题提交；台账收尾段；HANDOFF-M7（完结收官）或就地收束

## 3. 既定口径清单（动了会打挂测试/基准，改前先对照）

M4 交接口径 1-18 全部存续（见 HANDOFF-M5 §3，含 CLI 退出码/包名版本/3.8 底线/EOL/版权红线/条文纪律/零 LLM/限值不写死/真值对账/两张皮/分级判定序/门控语义/置信度/bench 门限/报告确定性/测试基线/GUI 只消费引擎 API/extras 覆盖），M5 新增：

19. **数据内嵌冻结分支**（决策 #29）：find_data_dir 优先级=显式 > SFC_DATA > sys._MEIPASS/data > exe/_internal/data > exe/data > CWD 上溯 > 包相对上溯；冻结分支先于 CWD；10 项测试锁死，改序=口径变更
20. **打包白名单单一事实源**（决策 #28）：datas 只准 packaging.build_datas 产生（46 份）；禁区段 FORBIDDEN_SEGMENTS=("raw",) 在白名单构建器内抛错；spec 文本无手写数据路径与禁区字面（守门测试）；构建后 --check 三断言（禁区/对账/多余）exit 1
21. **hiddenimports 显式覆盖**：HIDDENIMPORTS=["docx","pypdf"]（惰性依赖对静态分析不可见——漏一个=冻结 exe 缺能力而源码态全绿）
22. **GUI 分层**（决策 #30）：pipelines.py 唯一编排层零 Qt；页签零模态框（notify 信号）；默认卡=算例转录且"逐模块直接跑通引擎"测试锁定；offscreen 三坑实录（QT_QPA_PLATFORM 首导入前设置/模态挂死测试批/offscreen 无字体——截图走 native QPA+grab+QBuffer）
23. **重依赖版本 pin**（决策 #27）：PySide6>=6.6,<6.7、pyinstaller>=5.13,<6（上限必写——只写下限等于没 pin）
24. **版本 0.5.0**：`__init__.py` 与 pyproject 一致（test_version 守门）；首个正式 Release 1.0.0 留 M6
25. **sfc gui 子命令**：惰性导入（AST 静态守门：cli 模块级不得 import gui/PySide6）；缺依赖打印安装提示 exit 2
26. **GUI 基准页/核查页等同步执行**（秒级，忙态光标）；演示截图相对路径（防个人路径入公开仓）

## 4. 本机环境坑（只记实测，新增 4 条）

M5 交接坑 1-11 存续（见 HANDOFF-M5 §4），M5 新增：

- **pytest 收集期导入污染**：测试模块级 `sys.modules` 断言在"收集即导入全部测试模块"下假失败（test_gui 先于 test_cli 被收集）——模块级导入纪律用 AST 静态守门，不用 sys.modules
- **PyInstaller 5.x onedir 布局**：数据平铺 exe 目录（dist/sfc/data），sys._MEIPASS=exe 目录——6.x 的 _internal 布局兜底分支照写（分支测试用 mock，不依赖实装版本）
- **PyInstaller 构建告警 qwindows.dll 缺 api-ms-win-shcore**：API set 由 OS loader 解析，win10+ 实跑正常（exe 五连+GUI 探针全过），非故障
- **QPixmap.save(BytesIO) 6.6 不可用**：存图走 QBuffer（tools/make_demo_shots.py 现成做法）
- **GUI 测试禁 sys.modules 断言**（同上第一条）；**模态 QMessageBox 挂死 offscreen 批**——页签零模态、对话框只准按钮槽内
- pip 装 PySide6/PyInstaller 已在 venv（6.6.3.1/5.13.2）；重建 venv 后按 pyproject extras 重装即可（版本 pin 已写死）

## 5. 关键命令速查（M5 增补）

```bash
# —— M4 速查全部存续（见 HANDOFF-M5 §5）——

# GUI 冒烟（offscreen 探针）
QT_QPA_PLATFORM=offscreen ./.venv/Scripts/sfc-gui.exe --probe    # GUI_PROBE_OK tabs=5

# 打包（构建+构建后断言一条命令；--check 只跑断言）
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -X utf8 tools/build_exe.py
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -X utf8 tools/build_exe.py --check   # BUILD_CHECKS_OK

# exe 冒烟（在 dist/sfc 内；内嵌数据冻结分支优先，仓库树内跑也吃内嵌）
cd dist/sfc && ./sfc.exe selfcheck && ./sfc.exe bench --indent 0
./sfc.exe check data/synthetic/SY-two-sheets-01.docx    # exit 1=含违规（降级完成）
./sfc-gui.exe --probe                                    # exit 0

# 干净环境复验（中立目录 + 剥离 PATH；不在仓库树内跑）
CLEAN="$(cygpath -u "$LOCALAPPDATA")/Temp/sfc-clean-m6"
cp -r dist/sfc "$CLEAN/" && cd "$CLEAN/sfc"
env -i SYSTEMROOT="$SYSTEMROOT" ./sfc.exe selfcheck      # 数据目录=内嵌副本
env -i SYSTEMROOT="$SYSTEMROOT" ./sfc.exe bench > b.json # exit 0=三套件全达标
env -i SYSTEMROOT="$SYSTEMROOT" ./sfc-gui.exe --probe    # exit 0

# 五页签截图（仓库根运行；native QPA，无窗闪）
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -X utf8 tools/make_demo_shots.py

# sfc gui 子命令冒烟（惰性导入）
./.venv/Scripts/sfc.exe gui --help

# git 链前三核对（防 cwd 劫持）
pwd && git log --oneline -1 && git remote -v
```

## 6. M5 DoD 复核（逐项，详证见 plan/05 M5 节）

- [x] ①GUI offscreen 测试绿：21 项（QT_QPA_PLATFORM 首导入前设置；模态全屏蔽 notify 可注入；`sfc gui` AST 静态守门 + ImportError 路径 exit 2）
- [x] ②exe 干净验证：中立目录 + env -i 剥离 PATH，CLI 五连（calc 0/check 1/grade 0/bench 0/report×2）+ GUI 探针 0，selfcheck 数据目录=内嵌副本
- [x] ③数据内嵌分支测试锁死：10 项（优先级/双布局/回退/显式与环境变量压制）
- [x] ④dist 无禁区成分扫描 + 内嵌数据对账断言：BUILD_CHECKS_OK（全树禁区扫描 + 46 份 sha256 对账 + 白名单外多余检测；fake dist 正反用例）
- [x] ⑤spec 白名单守门：datas 只准 build_datas、spec 文本无手写数据路径与禁区字面、hiddenimports 覆盖、`!tools/*.spec` 入仓
- [x] 附加：304 passed 全绿（M4 基线 255 不回退）；bench 全达标；gen_* --check 位级一致；截图五张 + 技术报告落盘；版本 0.5.0
