# -*- mode: python ; coding: utf-8 -*-
"""sfc onedir 双 exe spec（M5，plan/05 M5 DoD ②⑤）。

红线纪律：
- datas 一律取 scaffold_formwork_checker.packaging.build_datas(ROOT) 白名单
  （规范原文全文目录绝不入包，禁区段定义见 packaging.FORBIDDEN_SEGMENTS，
  决策 #25）——本文件不手写任何数据路径；
- hiddenimports 显式覆盖惰性导入的外部依赖（packaging.HIDDENIMPORTS）；
- 构建后必须执行 tools/build_exe.py --check（禁区扫描 + 内嵌数据对账）。

退出码：exit 1=断言失败；构建由 tools/build_exe.py 驱动（清理/日志/断言）。
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))  # spec 相对路径解析到 SPECPATH，不解析 CWD（实录坑）
sys.path.insert(0, os.path.join(ROOT, "src"))

from scaffold_formwork_checker.packaging import HIDDENIMPORTS, build_datas  # noqa: E402

datas = build_datas(ROOT)
PATH = [os.path.join(ROOT, "src")]

a_cli = Analysis(
    [os.path.join(ROOT, "tools", "_entry_sfc.py")],
    pathex=PATH,
    binaries=[],
    datas=datas,
    hiddenimports=HIDDENIMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
a_gui = Analysis(
    [os.path.join(ROOT, "tools", "_entry_gui.py")],
    pathex=PATH,
    binaries=[],
    datas=datas,
    hiddenimports=HIDDENIMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz_cli = PYZ(a_cli.pure, a_cli.zipped_data, cipher=None)
pyz_gui = PYZ(a_gui.pure, a_gui.zipped_data, cipher=None)

exe_cli = EXE(
    pyz_cli,
    a_cli.scripts,
    [],
    exclude_binaries=True,
    name="sfc",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
)
exe_gui = EXE(
    pyz_gui,
    a_gui.scripts,
    [],
    exclude_binaries=True,
    name="sfc-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe_cli,
    exe_gui,
    a_cli.binaries,
    a_cli.zipfiles,
    a_cli.datas,
    a_gui.binaries,
    a_gui.zipfiles,
    a_gui.datas,
    strip=False,
    upx=False,
    name="sfc",
)
