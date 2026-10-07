# -*- coding: utf-8 -*-
"""M5 打包构建 + 构建后断言（plan/05 M5 DoD ②④⑤）。

用法（仓库根执行）：
  python tools/build_exe.py            # PyInstaller onedir 构建 + 构建后断言
  python tools/build_exe.py --check    # 仅对既有 dist/sfc 跑禁区扫描+内嵌数据对账

退出码：0=通过（打印 BUILD_CHECKS_OK）；1=断言失败（禁区成分/内嵌数据
缺失漂移/白名单外多余）；2=构建失败或环境不可用。

注意：验证产物不要在仓库树内直接跑 exe（CWD 上溯语义已被冻结分支压制，
但仍应在干净环境复验，见 plan/05 M5 DoD ②）。
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DIST = os.path.join(ROOT, "dist")
BUILD = os.path.join(ROOT, "build")
SPEC = os.path.join(HERE, "sfc.spec")


def run_check():
    from scaffold_formwork_checker.packaging import scan_dist

    errors = scan_dist(DIST, ROOT)
    for err in errors:
        print("FAIL %s" % err, file=sys.stderr)
    if errors:
        print("DIST_SCAN_FAILED（%d 项）" % len(errors), file=sys.stderr)
        return 1
    print("BUILD_CHECKS_OK")
    return 0


def build():
    for path in (os.path.join(DIST, "sfc"), os.path.join(BUILD, "sfc")):
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm",
           "--distpath", DIST, "--workpath", BUILD, "--log-level", "WARN", SPEC]
    print("$ %s" % " ".join(cmd))
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        print("PYINSTALLER_FAILED（exit %s）" % proc.returncode, file=sys.stderr)
        return 2
    return run_check()


def main(argv):
    if "--check" in argv:
        return run_check()
    return build()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
